#!/usr/bin/env python3
"""VoiceStudio v0.5.7 /profiles and /generate adapter. Local HTTP, no shell."""
import argparse, json, os, pathlib, subprocess, time, urllib.request, urllib.error, uuid, hashlib, shutil
p=argparse.ArgumentParser();p.add_argument('--url',default='http://127.0.0.1:3900');p.add_argument('--profile',required=True);p.add_argument('--engine',required=True);p.add_argument('--timeout',type=int,default=1800);p.add_argument('--no-cache',action='store_true');p.add_argument('request');a=p.parse_args()
base=a.url.rstrip('/');r=json.loads(pathlib.Path(a.request).read_text(encoding='utf-8'));headers={}
if os.environ.get('VOICESTUDIO_API_KEY'):headers['Authorization']='Bearer '+os.environ['VOICESTUDIO_API_KEY']
def call(route,data=None,content_type=None):
 h=dict(headers)
 if content_type:h['Content-Type']=content_type
 req=urllib.request.Request(base+route,data=data,headers=h)
 try:return urllib.request.urlopen(req,timeout=a.timeout)
 except urllib.error.HTTPError as e:raise RuntimeError(f'VoiceStudio {route}: HTTP {e.code}: {e.read(2000).decode(errors="replace")}') from e
with call('/health') as response:health=json.load(response)
with call('/openapi.json') as response:schema=json.load(response)
if '/generate' not in schema.get('paths',{}):raise RuntimeError('Running VoiceStudio has no supported /generate contract')
with call('/profiles') as response:profiles=json.load(response)
if not any(x.get('id')==a.profile for x in profiles):raise RuntimeError('Configured VoiceStudio voice profile does not exist')
with call('/engines/tts') as response:engine_info=json.load(response)
# Native engine checks remain authoritative; catalog presence alone is not readiness.
selected_profile=next(x for x in profiles if x.get('id')==a.profile)
cache_dir=pathlib.Path(__file__).resolve().parents[1]/'input/voice-cache';cache_dir.mkdir(parents=True,exist_ok=True)
report={'backend':base,'voice_profile':a.profile,'engine':a.engine,'health':health,'scenes':[]}
for scene_index,s in enumerate(r['scenes']):
 fields={'text':s['text'],'language':'Chinese','profile_id':a.profile,'engine':a.engine,'effect_preset':'raw','denoise':'false','stream':'false'}
 # Only IndexTTS exposes graded per-scene emotion through these form fields.
 if a.engine.startswith('indextts'):
  fields.update(emo_text=s.get('emotion',''),emo_alpha='0.5')
 cache_condition={k:selected_profile.get(k) for k in ('id','ref_text','instruct','language','seed','ref_audio_path','locked_audio_path','is_locked','kind','vd_states','audio_url')}
 cache_key=hashlib.sha256(json.dumps({'fields':fields,'profile':cache_condition,'backend_version':health.get('version')},ensure_ascii=False,sort_keys=True).encode()).hexdigest()
 cached=cache_dir/(cache_key+'.wav');output=pathlib.Path(s['output'])
 if cached.is_file() and not a.no_cache:
  valid=subprocess.run(['ffprobe','-v','error','-show_entries','format=duration','-of','json',str(cached)],capture_output=True,text=True)
  if valid.returncode==0:
   shutil.copyfile(cached,output);report['scenes'].append({'text':s['text'],'output':str(output),'cached':True,'seconds_elapsed':0})
   pathlib.Path(a.request).with_name('voicestudio-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
   print(f"配音 {scene_index+1}/{len(r['scenes'])} 复用缓存",flush=True);continue
 print(f"开始配音 {scene_index+1}/{len(r['scenes'])}（{len(s['text'])}字）",flush=True)
 boundary='workflow-'+uuid.uuid4().hex
 body=b''.join((f'--{boundary}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n').encode() for k,v in fields.items())+f'--{boundary}--\r\n'.encode()
 start=time.monotonic()
 with call('/generate',body,'multipart/form-data; boundary='+boundary) as response:
  data=response.read();meta={k:v for k,v in response.headers.items() if k.lower().startswith(('x-audio','x-gen','x-omnivoice','x-engine'))}
 if not data.startswith(b'RIFF') or data[8:12]!=b'WAVE':raise RuntimeError('VoiceStudio did not return a WAV; refusing to store an error as audio')
 output=pathlib.Path(s['output']);temp=output.with_suffix('.part.wav');temp.write_bytes(data)
 subprocess.run(['ffprobe','-v','error','-show_entries','format=duration','-of','json',str(temp)],check=True,stdout=subprocess.DEVNULL)
 temp.replace(output)
 cache_temp=cache_dir/(cache_key+'.'+uuid.uuid4().hex+'.tmp');shutil.copyfile(output,cache_temp);cache_temp.replace(cached)
 print(f"配音 {scene_index+1}/{len(r['scenes'])} 完成，用时 {time.monotonic()-start:.1f} 秒",flush=True)
 report['scenes'].append({'text':s['text'],'output':str(output),'seconds_elapsed':round(time.monotonic()-start,3),'headers':meta,'emotion_control':'reference-only' if a.engine=='moss-tts-nano' else 'engine-dependent'})
 pathlib.Path(a.request).with_name('voicestudio-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
print('VoiceStudio generated',len(r['scenes']),'scenes')
