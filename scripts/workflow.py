#!/usr/bin/env python3
"""Portable orchestration. Provider commands are argv arrays, never shell strings."""
import argparse
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import urllib.request
from presentation import resolve_presentation, STYLES, VIDEO_STYLES

os.environ.setdefault('PYTHONUTF8','1')
ROOT = Path(__file__).resolve().parents[1]
# Installed per-machine; never distributed with the portable package.
_runtime_file=ROOT/'.runtime/runtime.json'
if _runtime_file.is_file():
    _runtime=json.loads(_runtime_file.read_text(encoding='utf-8'))
    for _tool in ('node','ffmpeg','ffprobe'):
        if _runtime.get(_tool) and Path(_runtime[_tool]).is_file():
            os.environ['PATH']=str(Path(_runtime[_tool]).parent)+os.pathsep+os.environ.get('PATH','')
    if _runtime.get('browser') and Path(_runtime['browser']).is_file():
        os.environ.setdefault('WORKFLOW_CHROME',_runtime['browser'])
        os.environ.setdefault('HYPERFRAMES_BROWSER_PATH',_runtime['browser'])

def hyperframes(*args):
    package=ROOT/'node_modules/hyperframes/package.json'
    meta=json.loads(package.read_text(encoding='utf-8'))
    entry=meta['bin'] if isinstance(meta['bin'],str) else meta['bin']['hyperframes']
    return [shutil.which('node') or 'node',str(package.parent/entry),*[str(a) for a in args]]

def run(argv, cwd=ROOT, capture=False):
    return subprocess.run([str(x) for x in argv], cwd=cwd, check=True,
                          text=True, encoding='utf-8', capture_output=capture)

def save(p, obj):
    Path(p).write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding='utf-8')

def load(p):
    return json.loads(Path(p).read_text(encoding='utf-8'))

def path(s):
    p = Path(os.path.expandvars(s)).expanduser()
    return p if p.is_absolute() else ROOT / p

def probe(p):
    return json.loads(run(['ffprobe','-v','error','-show_format','-show_streams','-of','json',p], capture=True).stdout)

def duration(p):
    return float(probe(p)['format']['duration'])

def choose_avatar(selection='auto', library='avatars/library.json', state_file=None):
    lib=load(path(library));items=lib['avatars'];order=lib['rotation']
    state_path=path(state_file or lib.get('state_file','avatars/rotation-state.json'))
    state=load(state_path) if state_path.exists() else {'next_index':0}
    index=int(state.get('next_index',0)) % len(order)
    key=order[index] if selection.lower()=='auto' else selection.upper()
    if key not in items:raise ValueError('形象编号不存在：'+key)
    item=dict(items[key],id=key)
    item['photo']=str(path(item['photo']))
    if not Path(item['photo']).is_file():raise ValueError('形象文件不存在：'+item['photo'])
    rotation={'state_path':str(state_path),'next_index':(index+1)%len(order),'selected':key} if selection.lower()=='auto' else None
    return item,rotation

def commit_rotation(rotation):
    if not rotation:return
    target=Path(rotation['state_path']);target.parent.mkdir(parents=True,exist_ok=True)
    temp=target.with_suffix('.tmp')
    save(temp,{'next_index':rotation['next_index'],'last_avatar':rotation['selected']})
    temp.replace(target)

def command(cfg, request):
    argv = cfg.get('command')
    if not isinstance(argv, list) or not argv:
        raise ValueError('provider.command 必须是非空 argv 数组，末尾自动添加 request.json 路径')
    run([os.path.expandvars(x) for x in argv] + [str(request)], cwd=path(cfg.get('cwd', '.')))

def validate(job):
    if not isinstance(job.get('title'), str) or not job['title'].strip():
        raise ValueError('需要 title')
    scenes = job.get('scenes', [])
    if not scenes:
        raise ValueError('至少需要一幕 scenes')
    for s in scenes:
        if not s.get('text') or not s.get('headline'):
            raise ValueError('每幕需要 text 和 headline')
        if len(s['headline']) > 40 or len(s.get('cards', [])) > 3:
            raise ValueError('每幕标题最多40字、卡片最多3张；请拆幕')
        if any(len(c) > 70 for c in s.get('cards', [])):
            raise ValueError('单卡最多70字；请拆幕')
    for key in ('hook','data','question'):
        value = job.get('covers', {}).get(key)
        if value is not None and len(value) > 35:
            raise ValueError('封面标题最多35字')

def make_captions(scene, start, length):
    # Honest approximation fallback. For precise sync provide per-scene caption_cues.
    if scene.get('caption_cues'):
        result=[]
        previous=0
        for c in scene['caption_cues']:
            a,b=float(c['start']),float(c['end'])
            if not (previous <= a < b <= length+0.02):
                raise ValueError('caption_cues 必须顺序、非重叠且位于音频内')
            result.append(dict(text=c['text'],start=round(start+a,3),end=round(start+b,3)))
            previous=b
        if ''.join(re.sub(r'\W','',c['text']) for c in result) != re.sub(r'\W','',scene['text']):
            raise ValueError('caption_cues 文字必须与终审稿一致')
        return result, 'provided'
    chunks=[]
    for phrase in re.findall(r'[^，。！？；、：,.!?;:]+[，。！？；、：,.!?;:]?',scene['text']):
        chunks.extend(phrase[i:i+16] for i in range(0,len(phrase),16))
    chunks=chunks or [scene['text']]
    n=sum(len(c) for c in chunks); t=start; result=[]
    for c in chunks:
        end=t+length*len(c)/n
        result.append(dict(text=c,start=round(t,3),end=round(end,3)));t=end
    return result, 'estimated'

def doctor(profile=None,recorded=False):
    checks={x: bool(shutil.which(x)) for x in ['node','npm','ffmpeg','ffprobe']}
    checks['hyperframes']=(ROOT/'node_modules/hyperframes/bin/hyperframes.mjs').exists()
    if profile:
        p=load(profile);v={} if recorded else p.get('voice',{});a=p.get('avatar',{})
        if v.get('mode')=='indextts2':
            checks['IndexTTS Python']=path(v.get('python','missing')).exists()
            checks['IndexTTS repo']=path(v.get('repo','missing')).is_dir()
            checks['声音参考']=path(v.get('reference','missing')).is_file()
        if v.get('engine')=='voicestudio':
            if v.get('reference'):checks['声音参考']=path(v['reference']).is_file()
            try:
                argv=v.get('command',[]);base=argv[argv.index('--url')+1].rstrip('/') if '--url' in argv else 'http://127.0.0.1:3900'
                headers={'Authorization':'Bearer '+os.environ['VOICESTUDIO_API_KEY']} if os.environ.get('VOICESTUDIO_API_KEY') else {}
                with urllib.request.urlopen(urllib.request.Request(base+'/health',headers=headers),timeout=5) as response:health=json.load(response)
                checks['VoiceStudio后端']=bool(health)
                argv=v.get('command',[]);voice_id=argv[argv.index('--profile')+1] if '--profile' in argv else ''
                with urllib.request.urlopen(urllib.request.Request(base+'/profiles',headers=headers),timeout=5) as response:voices=json.load(response)
                checks['VoiceStudio本人声音档案']=any(x.get('id')==voice_id for x in voices)
            except Exception:checks['VoiceStudio后端与声音档案']=False
        if v.get('engine')=='mlx-indextts2':
            checks['MLX Python']=path(v['command'][0]).is_file()
            checks['声音参考']=path(v.get('reference','missing')).is_file()
            checks['MLX权重']=(path(v.get('model_dir','missing'))/'gpt.safetensors').is_file()
            checks['本地语气模型']=(path(v.get('qwen_model','missing'))/'config.json').is_file()
        if a.get('library'):
            item,_=choose_avatar('auto',a['library']);checks['人物素材']=Path(item['photo']).is_file()
        elif a.get('mode')=='photo-command':checks['人物照片']=path(a.get('photo','missing')).is_file()
        if a.get('mode')=='photo-command':checks['人物视频提供方已配置']=bool(a.get('command'))
        if a.get('mode')=='video':checks['本条人物视频']=path(a.get('video','missing')).is_file()
        if a.get('engine')=='libtv-omnihuman':
            checks['LibTV CLI']=bool(shutil.which('libtv'))
            try:
                result=subprocess.run(['libtv','account','info'],capture_output=True,text=True,timeout=15)
                checks['LibTV已登录']=result.returncode==0
            except Exception:checks['LibTV已登录']=False
    print(json.dumps(checks, ensure_ascii=False, indent=2))
    return 0 if all(checks.values()) else 2

def finish_visuals(out, manifest, no_render=False, demo=False):
    from card_timing import prepare
    timing=prepare(manifest)
    save(out/'card-timing.json',timing)
    save(out/'manifest.json',manifest)
    fps=manifest['fps'];timeline=manifest['scenes'];time=manifest['speech_duration'];total=manifest['duration']
    run(['node',ROOT/'scripts/compose.mjs',out])
    run(['node',ROOT/'scripts/check_card_reveals.mjs',out])
    check=subprocess.run(hyperframes('check',out,'--json'),cwd=ROOT,text=True,encoding='utf-8',capture_output=True)
    (out/'hyperframes-check.json').write_text(check.stdout,encoding='utf-8')
    (out/'hyperframes-check.log').write_text(check.stderr,encoding='utf-8')
    check.check_returncode()
    run(['node',ROOT/'scripts/covers.mjs',out])
    if not no_render:
        target=out/('演示_非本人声音_1080x1920.mp4' if demo else '成片_1080x1920.mp4')
        raw=out/'render.mp4'
        # Parallel capture occasionally loses a frame between worker temp dirs and the
        # encode step (ENOENT on copyfile after all frames "complete"), wasting a full
        # render. Default to one worker; opt in via WORKFLOW_RENDER_WORKERS=2 on faster machines.
        run(hyperframes('render',out,'--fps',fps,'--quality','delivery','--workers',os.environ.get('WORKFLOW_RENDER_WORKERS','1'),'--output',raw))
        run(['ffmpeg','-v','error','-y','-i',raw,'-i',out/'media/narration.wav','-map','0:v:0','-map','1:a:0',
             '-c:v','copy','-af','apad=pad_dur=0.4','-t',str(total),'-c:a','aac','-ar','48000','-ac','2','-movflags','+faststart',target])
        pr=probe(target);save(out/'ffprobe.json',pr)
        v=next(s for s in pr['streams'] if s['codec_type']=='video');a=next(s for s in pr['streams'] if s['codec_type']=='audio')
        if (v['width'],v['height'])!=(1080,1920) or a['sample_rate']!='48000':raise ValueError('成片参数不符合目标')
        if abs(float(pr['format']['duration'])-total)>0.15:raise ValueError('成片时长不一致')
        for i,s in enumerate(timeline):
            run(['ffmpeg','-v','error','-y','-ss',str(s['start']+min(1,s['duration']/2)),'-i',target,'-frames:v','1',out/f'关键帧-{i+1}.png'])

def build(args):
    job=load(args.job);profile=load(args.profile);validate(job)
    appearance_file=ROOT/'profiles/appearance.json'
    appearance_ready=appearance_file.is_file() and load(appearance_file).get('initialized') is True
    if not appearance_ready and not args.demo and job.get('id')!='environment-smoke':
        raise ValueError('首次使用请先运行 scripts/portable.py init，在八种风格中选择并保存，再生成视频。')
    if appearance_ready and job.get('id')!='environment-smoke':
        appearance=load(appearance_file)
        profile=dict(profile,theme=appearance['theme'],header=dict(profile.get('header',{}),**appearance['header']))
    theme,header=resolve_presentation(job,profile,getattr(args,'style',None))
    fps=int(profile.get('fps',30))
    if fps not in (24,25,30,50,60):raise ValueError('fps 需要为24/25/30/50/60')
    voice=profile.get('voice',{});avatar=profile.get('avatar',{'mode':'none'})
    requested=getattr(args,'avatar_mode',None) or job.get('avatar_mode') or avatar.get('mode')
    avatar=dict(avatar,**profile.get('avatar_options',{}).get(requested,{}),mode=requested)
    if getattr(args,'avatar_video',None):avatar=dict(avatar,mode='video',video=args.avatar_video)
    if job.get('avatar_photo'):avatar=dict(avatar,photo=job['avatar_photo']);avatar.pop('library',None)
    if avatar.get('mode')=='video':avatar.pop('library',None)
    selection=None;rotation=None
    if args.avatar or avatar.get('library'):
        if avatar.get('mode') not in ('static','mouth','poses','photo-command'):raise ValueError('该模式不能使用静态形象库')
        selection,rotation=choose_avatar(args.avatar or job.get('avatar_id','auto'),avatar.get('library','avatars/library.json'))
        avatar=dict(avatar,photo=selection['photo'])
    if avatar.get('mode') in ('mouth','photo-command') and not avatar.get('command'):
        raise ValueError('所选人物模式缺少command配置，不自动切换其他模式。')
    if avatar.get('mode')=='video' and not avatar.get('video'):raise ValueError('口播视频模式需要 --avatar-video 或配置avatar.video')
    if avatar.get('mode') in ('static','mouth') and (not avatar.get('photo') or not path(avatar['photo']).is_file()):raise ValueError('所选模式需要存在的图片文件')
    uploaded_audio=getattr(args,'audio',None) or job.get('audio_source')
    if uploaded_audio:
        if avatar.get('mode')=='video' and avatar.get('use_video_audio',True):
            raise ValueError('视频原音轨与上传录音不能同时启用；请先明确音频来源。')
        source=path(uploaded_audio)
        if not source.is_file():raise ValueError('上传配音文件不存在')
        length=duration(source);previous=0.0
        for audio_index,scene in enumerate(job['scenes']):
            if len(job['scenes'])==1:scene.setdefault('audio_start',0.0);scene.setdefault('audio_end',length)
            if 'audio_start' not in scene or 'audio_end' not in scene:
                raise ValueError('整段配音多幕需先转写，按真实时间填写audio_start/audio_end')
            start,end=float(scene['audio_start']),float(scene['audio_end'])
            if abs(start-previous)>.025 or not 0<=start<end<=length+.025:
                raise ValueError('配音分镜必须从0起连续覆盖，不能猜时间或漏掉音频')
            if audio_index==len(job['scenes'])-1 and abs(end-length)<=.025:end=length
            scene.update(audio=str(source),audio_start=previous,audio_end=end);previous=end
        if abs(previous-length)>.025:raise ValueError('配音分镜没有覆盖到音频末尾')
        voice=dict(voice,mode='recorded')
    if avatar.get('mode')=='video' and avatar.get('use_video_audio',True):
        vp=probe(path(avatar['video']))
        if not any(x['codec_type']=='audio' for x in vp['streams']):raise ValueError('上传视频没有音轨；请提供对应录音，或显式关闭use_video_audio并配置配音。')
        voice=dict(voice,mode='video-native')
        previous=0.0
        for i,scene in enumerate(job['scenes']):
            if len(job['scenes'])==1:scene.setdefault('video_start',0.0);scene.setdefault('video_end',float(vp['format']['duration']))
            if 'video_start' not in scene or 'video_end' not in scene:raise ValueError('视频多分镜需要按实际视频时间填写video_start/video_end；请先转写，不自动猜时长。')
            start,end=float(scene['video_start']),float(scene['video_end'])
            if abs(start-previous)>.025 or not start<end<=float(vp['format']['duration'])+.025:raise ValueError('视频分镜需从0开始连续覆盖，避免音画错位。')
            previous=end

    pose_library=None
    if avatar.get('mode')=='poses':
        pose_path=avatar.get('pose_library','avatars/poses/{id}/library.json').replace('{id}',selection['id'] if selection else avatar.get('id',''))
        if not path(pose_path).is_file():raise ValueError('所选形象还没有姿势图库：'+pose_path+'。不自动更换衣服或调用付费模型。')
        pose_library=load(path(pose_path))['poses']
        if not pose_library:raise ValueError('姿势图库为空')
        pose_ids={p['id'] for p in pose_library}
        for scene in job['scenes']:
            if scene.get('pose_id') and scene['pose_id'] not in pose_ids:raise ValueError('姿势编号不存在：'+scene['pose_id'])
        for item in pose_library:
            if not path(item['photo']).is_file():raise ValueError('姿势图不存在：'+item['photo'])

    if voice.get('mode')=='demo-system' and not args.demo:
        raise ValueError('系统演示音色仅能带 --demo 使用；正式生成必须配置你的声音或录音')
    if avatar.get('mode')=='none' and not args.demo:
        raise ValueError('请选择 static/mouth/video/poses 人物模式')
    stamp=dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    slug=re.sub(r'[^\w\-]','-',job.get('id','video'))[:50]
    out=ROOT/'jobs'/f'{slug}-{stamp}';out.mkdir(parents=True)
    (out/'media').mkdir();shutil.copy(ROOT/'assets/gsap.min.js',out/'media/gsap.min.js')
    if selection:
        frozen=out/'media/avatar-source.png';shutil.copy(avatar['photo'],frozen)
        avatar['photo']=str(frozen);save(out/'avatar-selection.json',selection)
    save(out/'job.json',job)
    # Keep only non-secret provenance; profiles/commands may reference credentials.
    save(out/'status.json',{'state':'running','demo':args.demo,'voice':voice.get('mode'),'avatar':avatar.get('mode')})
    try:
        entries=[]
        for i,s in enumerate(job['scenes']):
            entries.append({'text':s['text'],'emotion':s.get('emotion','自然解释，亲切、克制'),
                            'output':str(out/'media'/f'voice-{i}.wav')})
        mode=voice.get('mode')
        if mode in ('indextts2','command'):
            req=out/'voice-request.json';save(req,{'scenes':entries,'reference':str(path(voice['reference'])) if voice.get('reference') else None,
                'repo':str(path(voice['repo'])) if voice.get('repo') else None,
                'model_dir':voice.get('model_dir','checkpoints'),'emotion_strength':voice.get('emotion_strength',0.5),
                'qwen_model':str(path(voice['qwen_model'])) if voice.get('qwen_model') else None,
                'emotion_mode':voice.get('emotion_mode','text'),'emotion_reference':str(path(voice['emotion_reference'])) if voice.get('emotion_reference') else None})
            if mode=='indextts2':
                run([path(voice['python']),ROOT/'scripts/indextts_worker.py',req],cwd=path(voice['repo']))
            else:command(voice,req)
        elif mode=='video-native':
            for scene,e in zip(job['scenes'],entries):
                run(['ffmpeg','-v','error','-y','-ss',str(scene['video_start']),'-i',path(avatar['video']),'-t',str(float(scene['video_end'])-float(scene['video_start'])),'-vn','-ar','48000','-ac','2',e['output']])
        elif mode=='recorded':
            for s,e in zip(job['scenes'],entries):
                if not s.get('audio'):raise ValueError('recorded 模式每幕都需要 audio 路径')
                trim=['-ss',str(s['audio_start']),'-t',str(float(s['audio_end'])-float(s['audio_start']))] if uploaded_audio else []
                run(['ffmpeg','-v','error','-y','-i',path(s['audio']),*trim,'-vn','-ar','48000','-ac','2',e['output']])
        elif mode=='demo-system':
            for i,e in enumerate(entries):
                raw=out/'media'/f'demo-{i}.aiff';txt=out/'media'/f'demo-{i}.txt';txt.write_text(e['text'],encoding='utf-8')
                run(['say','-v',voice.get('name','Tingting'),'-r','205','-f',txt,'-o',raw])
                run(['ffmpeg','-v','error','-y','-i',raw,'-ar','48000','-ac','2',e['output']])
        else:raise ValueError('voice.mode 未配置：indextts2 / command / recorded')
        if voice.get('pace') and mode in ('command','indextts2'):
            from audio_pace import calibrate
            calibrate(job['scenes'],entries,voice['pace'],out/'pace-report.json')
        alignment=profile.get('alignment')
        if alignment:
            alignment_entries=[{'text':s['text'],'audio':e['output'],'duration':duration(e['output']),
                                'output':str(out/'media'/f'cues-{i}.json')}
                               for i,(s,e) in enumerate(zip(job['scenes'],entries))]
            req=out/'alignment-request.json';save(req,{'scenes':alignment_entries})
            command(alignment,req)
            for s,e in zip(job['scenes'],alignment_entries):
                s['caption_cues']=load(e['output'])
                words=Path(e['output']).with_suffix('.words.json')
                if words.is_file():s['_word_timing']=load(words)

        timeline=[];captions=[];time=0;timing_modes=[]
        for i,(s,e) in enumerate(zip(job['scenes'],entries)):
            p=Path(e['output'])
            if not p.is_file() or p.stat().st_size==0:raise ValueError('配音提供方没有写出有效音频')
            # Normalize format only; never alter speech speed or trim ends.
            normalized=out/'media'/f'norm-{i}.wav'
            run(['ffmpeg','-v','error','-y','-i',p,'-ar','48000','-ac','2',normalized])
            d=duration(normalized)
            if d<0.2:raise ValueError('配音过短')
            c,tm=make_captions(s,time,d);captions.extend(c);timing_modes.append(tm)
            timeline.append(dict(s,index=i,start=round(time,6),duration=d,audio=f'media/norm-{i}.wav'))
            time+=d
        # Filter concat avoids quoting arbitrary user paths in a concat-list file.
        merge=['ffmpeg','-v','error','-y']
        for i in range(len(entries)):merge+=['-i',str(out/'media'/f'norm-{i}.wav')]
        merge+=['-filter_complex',''.join(f'[{i}:a]' for i in range(len(entries)))+f'concat=n={len(entries)}:v=0:a=1[a]',
                '-map','[a]','-ar','48000','-ac','2',str(out/'media/narration.wav')];run(merge)
        avmode=avatar.get('mode');avfile=None;avatar_kind='none';avatar_cues=[]
        if avmode=='video':avfile=path(avatar['video'])
        elif avmode in ('photo-command','mouth'):
            photo=path(avatar['photo'])
            if not photo.is_file():raise ValueError('缺少你的形象照片')
            req=out/'avatar-request.json';avfile=out/'media/avatar-generated.mp4'
            save(req,{'image':str(photo),'audio':str(out/'media/narration.wav'),'output':str(avfile),'duration':time,'scenes':[{'start':s['start'],'duration':s['duration']} for s in timeline],
                'word_timing':[dict(w,start=w['start']+s['start'],end=w['end']+s['start']) for s in timeline for w in s.get('_word_timing',[])]})
            command(avatar,req)
        elif avmode in ('static','poses'):
            avatar_kind=avmode
            x=float(avatar.get('focus_x',.5));y=float(avatar.get('focus_y',.5))
            if not (0<=x<=1 and 0<=y<=1):raise ValueError('focus_x/y必须位于0到1')
            def freeze_image(source,name):
                target=out/'media'/name
                run(['ffmpeg','-v','error','-y','-i',path(source),'-vf',fr'crop=min(iw\,ih):min(iw\,ih):(iw-ow)*{x}:(ih-oh)*{y},scale=360:360','-frames:v','1',target])
                return 'media/'+name
            if avmode=='static':
                if not avatar.get('photo') or not path(avatar['photo']).is_file():raise ValueError('静态头像需要一张图片')
                source=freeze_image(avatar['photo'],'avatar-static.png')
                avatar_cues=[{'start':0,'duration':round(time+.4,6),'image':source}]
            else:
                pose_map={p['id']:p for p in pose_library}
                for i,scene in enumerate(timeline):
                    pose_id=scene.get('pose_id') or pose_library[i%len(pose_library)]['id']
                    if pose_id not in pose_map:raise ValueError('姿势编号不存在：'+pose_id)
                    source=freeze_image(pose_map[pose_id]['photo'],f'avatar-pose-{i}.png')
                    avatar_cues.append({'start':scene['start'],'duration':scene['duration']+(.4 if i==len(timeline)-1 else 0),'image':source,'pose_id':pose_id})
            run(['ffmpeg','-v','error','-y','-i',out/avatar_cues[0]['image'],'-frames:v','1',out/'media/portrait.jpg'])
        elif avmode!='none':raise ValueError('avatar.mode 未配置')

        if avfile:
            avatar_kind='video'
            pr=probe(avfile)
            if not any(s['codec_type']=='video' for s in pr['streams']):raise ValueError('人物文件没有视频轨道')
            if float(pr['format']['duration'])<time-0.1:raise ValueError('人物视频短于配音；禁止自动循环冒充对口型')
            x=float(avatar.get('focus_x',0.5));y=float(avatar.get('focus_y',0.5))
            if not (0<=x<=1 and 0<=y<=1):raise ValueError('focus_x/y 必须位于0到1')
            run(['ffmpeg','-v','error','-y','-i',avfile,'-t',str(time+0.4),'-an','-vf',
                 fr'crop=min(iw\,ih):min(iw\,ih):(iw-ow)*{x}:(ih-oh)*{y},scale=360:360,trim=duration={time},setpts=PTS-STARTPTS,tpad=stop_mode=clone:stop_duration=0.4',
                 '-c:v','libx264','-pix_fmt','yuv420p','-r',str(fps),str(out/'media/avatar.mp4')])
            # Crop is deterministic; circle masking is authored in the HTML layer.
            run(['ffmpeg','-v','error','-y','-ss','0.2','-i',out/'media/avatar.mp4','-frames:v','1',out/'media/portrait.jpg'])
        total=round(time+0.4,6)
        manifest={'title':job['title'],'brand':header['brand'],'theme':theme,'header':header,'workflow_version':'1.3.2',
                  'scenes':timeline,'captions':captions,'duration':total,'speech_duration':time,'fps':fps,
                  'avatar':bool(avfile or avatar_cues),'avatar_kind':avatar_kind,'avatar_cues':avatar_cues,'avatar_mode':avmode,'demo':args.demo,'covers':job.get('covers',{}),
                  'audio_mode':mode,'audio_reused':mode in ('recorded','video-native'),
                  'avatar_id':selection['id'] if selection else None,
                  'caption_timing':'provided' if all(x=='provided' for x in timing_modes) else 'estimated'}
        save(out/'manifest.json',manifest)
        finish_visuals(out,manifest,args.no_render,args.demo)
        notes=['字幕目前按句长估算时间，需要对齐或人工确认。'] if manifest['caption_timing']=='estimated' else []
        if args.demo:notes+=['演示使用系统音色，未克隆本人声音；人物未配置。'] if not avfile else ['演示使用系统音色，未克隆本人声音。']
        if avmode in ('static','poses'):notes+=['人物使用静态图片，不提供嘴型或连续动作。']
        elif avmode=='mouth':notes+=['嘴型为本地近似动画，没有真实身体手势；不是神经口型同步。']
        notes+=['上传原声未调用配音模型；读音与事实仍需确认。'] if mode=='recorded' else ['音色相似度、语气、读音与事实仍需人工确认。']
        if avmode in ('video','photo-command'):notes+=['口型和人物动作仍需人工确认。']

        save(out/'status.json',{'state':'rendered_candidate' if not args.no_render else 'prepared','demo':args.demo,'notes':notes})
        (out/'验收说明.md').write_text('# 已生成候选文件\n\n'+ '\n'.join('- '+s for s in notes)+'\n\n已自动检查：HyperFrames、封面溢出、成片分辨率/音轨/时长。参数检查不能证明内容准确或嘴型自然。\n',encoding='utf-8')
        if not args.no_render:commit_rotation(rotation)
        print('OUTPUT: '+str(out))
    except Exception as e:
        save(out/'status.json',{'state':'failed','error':str(e)})
        raise

def restyle(args):
    source=path(args.source).resolve()
    if not (source/'manifest.json').is_file() or not (source/'media/narration.wav').is_file():
        raise ValueError('source 需要已生成的任务目录，含manifest.json与media/narration.wav')
    manifest=load(source/'manifest.json')
    if args.header_json:
        patch=load(args.header_json)
        manifest['header']=dict(manifest.get('header',{}),**patch)
    theme,header=resolve_presentation(manifest,{},args.style)
    manifest.update(theme=theme,header=header,brand=header['brand'],workflow_version='1.3.0')
    out=ROOT/'jobs'/('restyle-'+theme+'-'+dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'))
    out.mkdir(parents=True)
    try:
        shutil.copytree(source/'media',out/'media')
        save(out/'manifest.json',manifest)
        save(out/'restyle-source.json',{'source':str(source),'audio_reused':True,'synthesized':False})
        finish_visuals(out,manifest,args.no_render,manifest.get('demo',False))
        save(out/'status.json',{'state':'prepared' if args.no_render else 'rendered_candidate',
                              'notes':['仅更换视觉；沿用原音频与字幕时间，未重新配音。']})
        print('OUTPUT: '+str(out))
    except Exception as e:
        save(out/'status.json',{'state':'failed','error':str(e)})
        raise

def main():
    parser=argparse.ArgumentParser();sub=parser.add_subparsers(dest='cmd',required=True)
    sub.add_parser('styles',help='列出卡片风格')
    nt=sub.add_parser('notes',help='直接导出图文PNG/JPG，不生成配音和视频')
    nt.add_argument('--job',required=True);nt.add_argument('--profile');nt.add_argument('--style',choices=list(STYLES));nt.add_argument('--output')
    rs=sub.add_parser('restyle',help='复用现有音频更换风格与页眉')
    rs.add_argument('--source',required=True);rs.add_argument('--style',choices=list(VIDEO_STYLES))
    rs.add_argument('--header-json',help='仅包含header字段的JSON文件');rs.add_argument('--no-render',action='store_true')
    d=sub.add_parser('doctor');d.add_argument('--profile');d.add_argument('--recorded',action='store_true',help='上传录音路线，不检查TTS服务')
    av=sub.add_parser('avatars');av.add_argument('--select',default='auto')
    ref=sub.add_parser('prepare-reference');ref.add_argument('--source',required=True)
    ref.add_argument('--start',type=float,required=True);ref.add_argument('--seconds',type=float,default=10)
    ref.add_argument('--output',default='input/my-voice-reference.wav')
    r=sub.add_parser('run');r.add_argument('--job',required=True);r.add_argument('--profile',required=True)
    r.add_argument('--demo',action='store_true');r.add_argument('--no-render',action='store_true')
    r.add_argument('--style',choices=list(VIDEO_STYLES),help='卡片与封面风格，覆盖job和profile')
    r.add_argument('--audio',help='整段已录制配音，跳过TTS；多幕需真实音频时间')
    r.add_argument('--avatar-mode',choices=['static','mouth','video','poses'],help='人物呈现方式；不自动调用云端模型')
    r.add_argument('--avatar-video',help='本条文案对应的口播视频文件')
    r.add_argument('--avatar',help='A/B/C指定形象，auto按成功成片轮换')
    a=parser.parse_args()
    if a.cmd=='styles':print(json.dumps(STYLES,ensure_ascii=False,indent=2));return 0
    if a.cmd=='notes':
        from notes import build as build_notes
        build_notes(a);return 0
    if a.cmd=='restyle':restyle(a);return 0
    if a.cmd=='doctor':return doctor(a.profile,a.recorded)
    if a.cmd=='avatars':
        item,rotation=choose_avatar(a.select)
        print(json.dumps({'library':load(ROOT/'avatars/library.json'),'selected':item,'rotation_preview':rotation,'advances_state':False},ensure_ascii=False,indent=2));return 0
    if a.cmd=='prepare-reference':
        if not 3<=a.seconds<=12 or a.start<0:raise ValueError('参考片段应为3–12秒，start不能为负数')
        if a.start+a.seconds>duration(path(a.source))+0.01:raise ValueError('参考片段超出源录音')
        target=path(a.output)
        if target.exists():raise ValueError('参考音频已经存在；请指定新文件名，避免覆盖已校准音色')
        target.parent.mkdir(parents=True,exist_ok=True)
        run(['ffmpeg','-v','error','-i',path(a.source),'-ss',str(a.start),'-t',str(a.seconds),'-vn','-ar','22050','-ac','1',target])
        print(target);return 0
    build(a);return 0

if __name__=='__main__':
    try:sys.exit(main())
    except Exception as e:print('ERROR: '+str(e),file=sys.stderr);sys.exit(1)
