#!/usr/bin/env python3
"""Rhubarb phonetic cues -> deterministic Canvas puppet. No generative GPU model."""
import argparse, json, pathlib, subprocess, tempfile, hashlib
ROOT=pathlib.Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser();p.add_argument('--rhubarb');p.add_argument('--timing-python');p.add_argument('request');a=p.parse_args()
r=json.load(open(a.request));out=pathlib.Path(r['output']);out.parent.mkdir(parents=True,exist_ok=True)
# Frozen job images are matched by content, never by the generic avatar-source filename.
digest=hashlib.sha256(pathlib.Path(r['image']).read_bytes()).hexdigest()
ids=[x for x in ('A','B','C') if (ROOT/'avatars'/f'{x}.png').is_file() and hashlib.sha256((ROOT/'avatars'/f'{x}.png').read_bytes()).hexdigest()==digest]
if len(ids)!=1:raise ValueError('Image is not a registered calibrated avatar')
with tempfile.TemporaryDirectory(prefix='cartoon-') as tmp:
 wav=pathlib.Path(tmp)/'speech.wav';cues=pathlib.Path(tmp)/'cues.json'
 subprocess.run(['ffmpeg','-v','error','-y','-i',r['audio'],'-ar','16000','-ac','1',str(wav)],check=True)
 if a.timing_python:
  argv=[a.timing_python,str(ROOT/'scripts/mandarin_cues.py'),str(wav),str(cues)]
  if r.get('word_timing'):
   words=pathlib.Path(tmp)/'words.json';words.write_text(json.dumps(r['word_timing'],ensure_ascii=False));argv+=['--words',str(words)]
  subprocess.run(argv,check=True)
 elif a.rhubarb:
  subprocess.run([a.rhubarb,'-r','phonetic','-f','json','--extendedShapes','GHX','-o',str(cues),str(wav)],check=True)
 else:raise ValueError('Choose timing-python or native rhubarb')
 payload=dict(r,avatar_id=ids[0],mouth_cues=json.load(open(cues))['mouthCues'],fps=30)
 config=out.with_suffix('.puppet.json');config.write_text(json.dumps(payload,ensure_ascii=False,indent=2))
 subprocess.run(['node',str(ROOT/'scripts/cartoon_render.mjs'),str(config)],check=True,cwd=ROOT)
 out.with_suffix('.animation.json').write_text(json.dumps({'engine':('Whisper alignment + pinyin + Canvas 2D puppet' if a.timing_python else 'Rhubarb phonetic + Canvas 2D puppet'),'avatar_id':ids[0],'timing_source':('reused_alignment_words' if r.get('word_timing') else 'independent_audio_recognition'),'cues':payload['mouth_cues'],'limitations':['Visemes are approximated from recognized syllables; this is not a neural 3D lip-sync model.','Mouth and blink animation; body gesture is not generated.']},ensure_ascii=False,indent=2))
