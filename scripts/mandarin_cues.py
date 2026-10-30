"""Approximate Mandarin visemes from Whisper word times + pinyin, not forced alignment."""
import json, re, sys
from pathlib import Path
from pypinyin import lazy_pinyin, Style
# On M1 base inference on CPU avoids MPS sparse-tensor decoder incompatibilities.
audio,output=sys.argv[1:3]
if len(sys.argv)>4 and sys.argv[3]=='--words':
 words=json.loads(Path(sys.argv[4]).read_text());r={'text':''.join(w['word'] for w in words),'segments':[{'words':words}]}
else:
 import whisper, torch
 torch.set_num_threads(4)
 model=whisper.load_model('small',device='cpu')
 r=model.transcribe(audio,language='zh',word_timestamps=True,fp16=False,verbose=False)
cues=[]
for seg in r['segments']:
 for w in seg.get('words',[]):
  chars=[c for c in w['word'] if re.match(r'[\u3400-\u9fffA-Za-z0-9]',c)]
  if not chars:continue
  span=(w['end']-w['start'])/len(chars)
  for i,c in enumerate(chars):
   start=w['start']+i*span;end=start+span
   if end-start<.02:continue
   syllable=lazy_pinyin(c,style=Style.NORMAL)[0].lower()
   if syllable.startswith(('b','p','m')):initial='A'
   elif syllable.startswith(('f','v')):initial='G'
   else:initial='B'
   if 'a' in syllable:vowel='D'
   elif 'o' in syllable:vowel='E'
   elif 'u' in syllable or 'v' in syllable:vowel='F'
   elif 'i' in syllable or 'e' in syllable:vowel='C'
   else:vowel='B'
   cues.extend([{'start':round(start,4),'end':round(start+span*.22,4),'value':initial},
                {'start':round(start+span*.22,4),'end':round(end,4),'value':vowel}])
Path(output).write_text(json.dumps({'mouthCues':cues,'transcript':r['text'],'segments':r['segments'],'method':'Whisper base word timestamps + pinyin viseme approximation'},ensure_ascii=False,indent=2))
