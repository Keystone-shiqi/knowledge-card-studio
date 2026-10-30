"""Resolve scene-relative card reveals from speech anchors or checked offsets."""
import math,re,unicodedata

def norm(text):
    return ''.join(c.lower() for c in unicodedata.normalize('NFKC',str(text)) if c.isalnum())

def resolve(scene):
    cards=scene.get('cards',[]);duration=float(scene['duration'])
    if not cards:return []
    cues=scene.get('card_cues');at=scene.get('card_at');method='estimated' if scene.get('card_timing')=='estimated' else 'manual'
    if cues is not None:
        if not isinstance(cues,list) or len(cues)!=len(cards) or any(not isinstance(c,str) or not norm(c) for c in cues):
            raise ValueError('card_cues需与cards等长，每项为原口播中的连续短语')
        words=scene.get('_word_timing',[])
        if not words:raise ValueError('card_cues需要已有逐词时间，不可用均分时间冒充音频对齐')
        text='';times=[]
        for w in words:
            token=norm(w.get('word',''));text+=token;times.extend([float(w['start'])]*len(token))
        at=[];cursor=0
        for cue in cues:
            term=norm(cue);pos=text.find(term,cursor)
            if pos<0:raise ValueError('口播锚点未匹配，请对照逐词转写修正：'+cue)
            at.append(times[pos]);cursor=pos+len(term)
        method='speech-anchor'
    elif at is None:
        # Legacy compatibility only. Skill asks for anchors for new narration jobs.
        count=len(cards);at=[round(.3+i*max(0,duration-1.2)/count,3) for i in range(count)];method='estimated'
    if not isinstance(at,list) or len(at)!=len(cards):raise ValueError('card_at需与cards等长')
    if any(type(x) not in (int,float) or not math.isfinite(x) for x in at):raise ValueError('card_at需为有限秒数')
    if any(t<0 or t>duration-.4 for t in at) or any(b<=a for a,b in zip(at,at[1:])):
        raise ValueError('card_at需递增且位于本幕音频内，并留至少0.4秒展示')
    scene['card_at']=[round(x,3) for x in at];scene['card_timing']=method
    return scene['card_at']

def prepare(manifest):
    result=[]
    for scene in manifest['scenes']:
        at=resolve(scene);result.append({'scene':scene['index'],'start':scene['start'],'card_at':at,'method':scene.get('card_timing','none'),'card_cues':scene.get('card_cues')})
    return {'scene_relative_seconds':True,'scenes':result,'estimated_scenes':[x['scene'] for x in result if x['method']=='estimated']}
