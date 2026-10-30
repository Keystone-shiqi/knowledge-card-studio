"""Optional openai-whisper adapter. Keeps script text; rejects low-confidence alignment."""
import difflib
import json
import os
from pathlib import Path
import re
import sys
import whisper
import torch
from opencc import OpenCC
from pypinyin import lazy_pinyin
torch.set_num_threads(4)
cc=OpenCC("t2s")

req=json.loads(Path(sys.argv[1]).read_text(encoding='utf-8'))
model_name=os.environ.get('WORKFLOW_WHISPER_MODEL','small')
model=whisper.load_model(model_name)
for s in req['scenes']:
    result=model.transcribe(s['audio'],language='zh',word_timestamps=True,fp16=False)
    recognized_words=[dict(word=cc.convert(w['word']),start=w['start'],end=w['end']) for seg in result['segments'] for w in seg.get('words',[])]
    Path(s['output']).with_suffix('.words.json').write_text(json.dumps(recognized_words,ensure_ascii=False,indent=2),encoding='utf-8')
    chars=[];times=[]
    for segment in result['segments']:
        for w in segment.get('words',[]):
            text=re.sub(r'\W','',cc.convert(w['word']))
            for i,c in enumerate(text):
                chars.append(c);times.append((w['start']+(w['end']-w['start'])*i/max(len(text),1),
                                              w['start']+(w['end']-w['start'])*(i+1)/max(len(text),1)))
    clean=re.sub(r'\W','',cc.convert(s['text']));matching=difflib.SequenceMatcher(None,clean,''.join(chars),autojunk=False)
    mapping={i+k:j+k for i,j,n in matching.get_matching_blocks() for k in range(n)}
    literal_ratio=len(mapping)/max(len(clean),1)
    # Chinese homophones often differ in Whisper spelling; align phonetic tokens
    # while retaining the exact approved script. This does not verify pronunciation.
    phonetic=difflib.SequenceMatcher(None,lazy_pinyin(clean),lazy_pinyin(''.join(chars)),autojunk=False)
    phonetic_mapping={i+k:j+k for i,j,n in phonetic.get_matching_blocks() for k in range(n)}
    phonetic_ratio=len(phonetic_mapping)/max(len(clean),1)
    if phonetic_ratio>literal_ratio:mapping=phonetic_mapping
    Path(s['output']).with_suffix('.alignment.json').write_text(json.dumps({'model':model_name,'literal_ratio':literal_ratio,'phonetic_ratio':phonetic_ratio,'recognized':''.join(chars),'script':s['text']},ensure_ascii=False,indent=2),encoding='utf-8')
    if len(mapping)/max(len(clean),1)<0.9:raise RuntimeError('识别与原稿匹配低于90%，请复听和人工对齐；未静默使用识别错字')
    phrases=[]
    for phrase in re.findall(r'[^，。！？；、：,.!?;:]+[，。！？；、：,.!?;:]?',s['text']):
        phrases.extend(phrase[i:i+16] for i in range(0,len(phrase),16))
    cues=[];offset=0;prev=0
    for phrase in phrases:
        n=len(re.sub(r'\W','',phrase));indices=[mapping[i] for i in range(offset,offset+n) if i in mapping]
        if not n:
            if cues:cues[-1]['text']+=phrase
            continue
        if not indices:raise RuntimeError('某字幕句无法匹配，请人工对齐')
        start=max(prev,times[indices[0]][0]);end=min(s['duration'],times[indices[-1]][1])
        if end<=start:raise RuntimeError('字幕时间发生重叠或越界')
        cues.append({'start':start,'end':end,'text':phrase});prev=end;offset+=n
    Path(s['output']).write_text(json.dumps(cues,ensure_ascii=False,indent=2),encoding='utf-8')
