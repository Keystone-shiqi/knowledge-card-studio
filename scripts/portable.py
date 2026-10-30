#!/usr/bin/env python3
"""Local Windows/macOS bootstrap, configuration and non-speech render smoke test."""
import argparse,hashlib,json,os,platform,shutil,subprocess,sys,zipfile,wave,math,struct,zlib
from pathlib import Path
from urllib.request import urlopen
ROOT=Path(__file__).resolve().parents[1]
os.environ.setdefault('PYTHONUTF8','1')
RUNTIME=ROOT/'.runtime'
if (RUNTIME/'runtime.json').is_file():
 try:_tools=json.loads((RUNTIME/'runtime.json').read_text(encoding='utf-8'))
 except (OSError,json.JSONDecodeError):_tools={}
 for _tool in ('node','ffmpeg','ffprobe'):
  if _tools.get(_tool) and Path(_tools[_tool]).is_file():os.environ['PATH']=str(Path(_tools[_tool]).parent)+os.pathsep+os.environ.get('PATH','')
def read(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def write(p,data):
 p=Path(p);p.parent.mkdir(parents=True,exist_ok=True);temp=p.with_name(p.name+'.new');temp.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8');temp.replace(p)
def call(argv):
 write(RUNTIME/'setup-state.json',{'state':'running','step':str(argv[0]),'arguments':[str(x) for x in argv[1:]]})
 print('>', ' '.join(str(a) for a in argv),flush=True)
 subprocess.run([str(a) for a in argv],cwd=ROOT,check=True,env=dict(os.environ,PYTHONUTF8='1',HYPERFRAMES_SKIP_SKILLS='1'))
def runtime_python():return RUNTIME/'asr'/('Scripts/python.exe' if os.name=='nt' else 'bin/python')
def npm_cli():
 npm=shutil.which('npm');node=shutil.which('node');candidates=[]
 if npm:
  p=Path(npm).resolve()
  if p.suffix in ('.js','.mjs'):candidates.append(p)
  candidates.extend([Path(npm).parent/'node_modules/npm/bin/npm-cli.js',p.parent/'node_modules/npm/bin/npm-cli.js'])
 if node:candidates.append(Path(node).resolve().parent/'node_modules/npm/bin/npm-cli.js')
 return next((p for p in candidates if p.is_file()),None)
def system_check(mode=None):
 result={}
 result['platform']={'ok':sys.platform in ('win32','darwin'),'detail':platform.platform()}
 for name in (('node',) if (mode or output_mode())=='notes' else ('node','ffmpeg','ffprobe')):
  p=shutil.which(name);ok=bool(p);detail=p or 'not on PATH'
  if p and name=='node':
   ver=subprocess.check_output([p,'--version'],text=True,encoding='utf-8').strip();ok=int(ver.lstrip('v').split('.')[0])>=22;detail=ver+' '+p
  result[name]={'ok':ok,'detail':detail}
 result['npm']={'ok':npm_cli() is not None,'detail':str(npm_cli() or 'npm-cli.js not found; use the official Node installer')}
 result['render_dependencies']={'ok':(ROOT/'node_modules/hyperframes/bin/hyperframes.mjs').is_file(),'detail':'run install if missing'}
 if (mode or output_mode())=='notes':
  result['browser']={'ok':bool(find_browser()) or ((RUNTIME/'runtime.json').is_file() and Path(read(RUNTIME/'runtime.json').get('browser','missing')).is_file()),'detail':'图文无需VoiceStudio、FFmpeg与字幕模型'}
  return result
 result['asr_environment']={'ok':runtime_python().is_file(),'detail':str(runtime_python())}
 if (RUNTIME/'runtime.json').is_file():
  r=read(RUNTIME/'runtime.json');result['browser']={'ok':Path(r.get('browser','missing')).is_file(),'detail':r.get('browser')}
 result['personal_profile']={'ok':(ROOT/'profiles/personal.json').is_file(),'detail':'run configure after starting VoiceStudio'}
 if result['personal_profile']['ok']:
  try:
   config=read(ROOT/'profiles/personal.json');v=config.get('voice',{});argv=v.get('command',[])
   if v.get('engine')=='voicestudio':
    base=argv[argv.index('--url')+1] if '--url' in argv else 'http://127.0.0.1:3900';voice=argv[argv.index('--profile')+1]
    voices=profiles(base);result['voice_backend']={'ok':any(x.get('id')==voice for x in voices),'detail':'MOSS profile on '+base}
  except Exception as e:result['voice_backend']={'ok':False,'detail':str(e)}
 return result

def find_browser():
 candidates=[os.environ.get('WORKFLOW_CHROME'),'/Applications/Google Chrome.app/Contents/MacOS/Google Chrome']
 for env in ('PROGRAMFILES','PROGRAMFILES(X86)','LOCALAPPDATA'):
  if os.environ.get(env):candidates.append(str(Path(os.environ[env])/'Google/Chrome/Application/chrome.exe'))
 return next((str(Path(x)) for x in candidates if x and Path(x).is_file()),None)

def voicestudio(args=None):
 from voicestudio_setup import ensure_voicestudio
 return ensure_voicestudio(ROOT)

def audio_mode(args=None):
 selected=getattr(args,'audio_mode',None)
 if selected:return selected
 appearance=ROOT/'profiles/appearance.json'
 if appearance.is_file() and read(appearance).get('audio_source') in ('recorded','clone'):return read(appearance)['audio_source']
 profile=ROOT/'profiles/personal.json'
 if profile.is_file() and read(profile).get('voice',{}).get('mode') in ('command','indextts2'):return 'clone'
 return 'recorded'

def output_mode(args=None):
 mode=getattr(args,'output_mode',None)
 if mode:return mode
 p=ROOT/'profiles/appearance.json'
 return read(p).get('output_mode','video') if p.is_file() else 'video'

def install_notes(args):
 checks=system_check('notes');missing=[k for k in ('platform','node','npm') if not checks[k]['ok']]
 if missing:raise RuntimeError('纯图文需要 '+', '.join(missing)+'；不需要安装配音或视频模型。')
 call([shutil.which('node'),npm_cli(),'ci','--no-audit','--no-fund'])
 browser=find_browser()
 if not browser:
  call([shutil.which('node'),ROOT/'node_modules/playwright/cli.js','install','chromium'])
  browser=subprocess.check_output([shutil.which('node'),'--input-type=module','-e',"import {chromium} from 'playwright'; console.log(chromium.executablePath())"],cwd=ROOT,text=True,encoding='utf-8').strip()
 if not Path(browser).is_file():raise RuntimeError('浏览器未安装')
 runtime=read(RUNTIME/'runtime.json') if (RUNTIME/'runtime.json').is_file() else {}
 py=runtime.get('python') if runtime.get('python') and Path(runtime['python']).is_file() else sys.executable
 runtime.update(python=py,browser=browser,node=shutil.which('node'),platform=sys.platform,machine=platform.machine())
 write(RUNTIME/'runtime.json',runtime);write(RUNTIME/'setup-state.json',{'state':'installed','output_mode':'notes','voice_required':False})
 print('纯图文环境已安装：跳过VoiceStudio、Whisper/PyTorch和FFmpeg安装，不进行配音或视频渲染。')

def _install(args):
 if output_mode(args)=='notes':return install_notes(args)
 if audio_mode(args)=='clone':voicestudio()
 else:print('上传配音模式：跳过VoiceStudio，仅安装字幕和渲染环境。')
 checks=system_check('video');missing=[k for k in ('platform','node','npm','ffmpeg','ffprobe') if not checks[k]['ok']]
 if missing:raise RuntimeError('先安装/修复 '+', '.join(missing)+'。请阅读 安装与迁移.md，安装后重启WorkBuddy以刷新PATH。')
 uv=shutil.which('uv')
 if not uv:
  for p in (Path.home()/'.local/bin/uv',Path.home()/'.local/bin/uv.exe',RUNTIME/'bootstrap'/('Scripts/uv.exe' if os.name=='nt' else 'bin/uv')):
   if p.is_file():uv=str(p);break
 if not uv:
  boot=RUNTIME/'bootstrap';call([sys.executable,'-m','venv',boot]);bp=boot/('Scripts/python.exe' if os.name=='nt' else 'bin/python');call([bp,'-m','pip','install','uv==0.11.17']);uv=str(boot/('Scripts/uv.exe' if os.name=='nt' else 'bin/uv'))
 call([uv,'python','install','3.11'])
 if not runtime_python().is_file():call([uv,'venv','--python','3.11',RUNTIME/'asr'])
 # CPU-only torch on Windows avoids downloading a CUDA runtime for ASR.
 if os.name=='nt':call([uv,'pip','install','--python',runtime_python(),'torch==2.10.0','--index-url','https://download.pytorch.org/whl/cpu'])
 elif sys.platform=='darwin' and platform.machine()=='x86_64':call([uv,'pip','install','--python',runtime_python(),'torch==2.2.2'])
 else:call([uv,'pip','install','--python',runtime_python(),'torch==2.10.0'])
 call([uv,'pip','install','--python',runtime_python(),'-r',ROOT/'requirements-asr.txt'])
 call([shutil.which('node'),npm_cli(),'ci','--no-audit','--no-fund'])
 browser=find_browser()
 if not browser:
  if not args.skip_browser:call([shutil.which('node'),ROOT/'node_modules/playwright/cli.js','install','chromium'])
  browser=subprocess.check_output([shutil.which('node'),'--input-type=module','-e',"import {chromium} from 'playwright'; console.log(chromium.executablePath())"],cwd=ROOT,text=True,encoding='utf-8').strip()
 if not Path(browser).is_file():raise RuntimeError('Chromium未安装；去掉--skip-browser后重试。')
 write(RUNTIME/'runtime.json',{'python':str(runtime_python()),'browser':browser,'platform':sys.platform,'machine':platform.machine(),'node':shutil.which('node'),'ffmpeg':shutil.which('ffmpeg'),'ffprobe':shutil.which('ffprobe')})
 if not args.skip_model:call([runtime_python(),'-X','utf8','-c',"import whisper; whisper.load_model('small',device='cpu'); print('Whisper small ready')"])
 write(RUNTIME/'setup-state.json',{'state':'installed','voice_configured':(ROOT/'profiles/personal.json').is_file()})
 print('运行环境已安装。下一步：配置头像；克隆模式还需在VoiceStudio准备MOSS与声音档案。')

def install(args):
 try:_install(args)
 except Exception as e:
  write(RUNTIME/'setup-state.json',{'state':'failed','action':'install','error':str(e)})
  raise

def profiles(base):
 from urllib.request import Request
 headers={}
 if os.environ.get('VOICESTUDIO_API_KEY'):headers['Authorization']='Bearer '+os.environ['VOICESTUDIO_API_KEY']
 with urlopen(Request(base.rstrip('/')+'/profiles',headers=headers),timeout=10) as r:data=json.load(r)
 if not isinstance(data,list):raise RuntimeError('VoiceStudio /profiles返回格式与已验证版本不一致')
 return data

def init(args=None):
 from onboarding import serve
 serve(ROOT,not getattr(args,'no_browser',False))

def configure(args):
 if not (ROOT/'profiles/appearance.json').is_file() or read(ROOT/'profiles/appearance.json').get('initialized') is not True:init()
 if output_mode(args)=='notes':
  appearance=read(ROOT/'profiles/appearance.json');path=ROOT/'profiles/personal.json'
  config=read(path) if path.exists() else {'fps':30,'voice':{'mode':'none'},'avatar':{'mode':'none'}}
  config.update(output_mode='notes',theme=appearance['theme'],header=appearance['header'])
  write(path,config);print('图文默认配置已保存；原有声音和头像配置保留，不需要新建声音档案。');return
 if not runtime_python().is_file():raise RuntimeError('请先运行 install')
 py=str(runtime_python())
 if audio_mode(args)=='recorded':voice={'mode':'recorded'}
 else:
  voices=profiles(args.url)
  if not voices:raise RuntimeError('请先在VoiceStudio创建声音档案，导入你的录音并保存，然后重试。')
  for i,v in enumerate(voices):print(f"{i+1}. {v.get('name') or v.get('id')}")
  selected=next((v for v in voices if v.get('id')==args.voice_id),None) if args.voice_id else None
  if args.voice_id and not selected:raise RuntimeError('该声音ID不在当前VoiceStudio中')
  if selected is None:
   n=int(input('选择本机声音档案编号：'))-1
   if not 0<=n<len(voices):raise RuntimeError('编号超出范围')
   selected=voices[n]
  voice={'mode':'command','engine':'voicestudio','command':[py,'-X','utf8',str(ROOT/'scripts/voicestudio_worker.py'),'--url',args.url,'--profile',selected['id'],'--engine','moss-tts-nano'],'pace':{'target_chars_per_second':4.15,'min_tempo':.8,'max_tempo':1.2}}
 ref=ROOT/'input/voice/reference.wav'
 if voice['mode']=='command' and ref.exists():voice['reference']='input/voice/reference.wav'
 if (ROOT/'avatars/library.json').exists() and (ROOT/'avatars/A.png').exists():avatar={'mode':'static','library':'avatars/library.json'}
 elif args.photo:
  source=Path(args.photo).expanduser().resolve()
  if not source.is_file():raise RuntimeError('照片不存在')
  dest=ROOT/'avatars'/('custom'+source.suffix.lower());dest.parent.mkdir(exist_ok=True);shutil.copy2(source,dest);avatar={'mode':'static','photo':str(dest.relative_to(ROOT.resolve()))}
 else:raise RuntimeError('请先导入个人素材包，或用 configure --photo 照片路径')
 config={'brand':args.brand,'theme':'studio-paper','fps':30,'voice':voice,'avatar':avatar,'alignment':{'command':[py,'-X','utf8',str(ROOT/'scripts/whisper_align.py')]},'avatar_options':{'static':{},'poses':{'pose_library':'avatars/poses/{id}/library.json'},'video':{},'mouth':{'command':[py,'-X','utf8',str(ROOT/'scripts/cartoon_worker.py'),'--timing-python',py]}}}
 appearance=read(ROOT/'profiles/appearance.json');config.update(theme=appearance['theme'],header=appearance['header'])
 path=ROOT/'profiles/personal.json'
 if path.exists() and not args.replace:raise RuntimeError('已有配置；要重新配置请加--replace，原配置会备份。')
 if path.exists():shutil.copy2(path,path.with_suffix('.previous.json'))
 write(path,config);write(RUNTIME/'setup-state.json',{'state':'configured','voice_configured':voice['mode']=='command','audio_mode':audio_mode(args)});print('已生成本机配置；音频来源：'+('上传配音，无需VoiceStudio' if voice['mode']=='recorded' else 'MOSS本人克隆'))

def materials(args):
 with zipfile.ZipFile(args.archive) as z:
  accepted=[]
  for name in z.namelist():
   parts=Path(name.replace('\\','/')).parts
   if parts and parts[0]=='personal-materials':parts=parts[1:]
   if not parts or name.endswith('/'):continue
   if any(p in ('..','.') or ':' in p for p in parts) or parts[0] not in ('avatars','input','material-manifest.json'):raise RuntimeError('素材包包含不支持的文件路径')
   relative=Path(*parts);dest=(ROOT/relative).resolve()
   if not dest.is_relative_to(ROOT.resolve()):raise RuntimeError('不安全的素材路径')
   data=z.read(name)
   if dest.exists() and dest.read_bytes()!=data and not args.replace:raise RuntimeError('已有不同素材：'+str(relative)+'；加--replace才允许替换。')
   accepted.append((dest,data))
  manifests=[data for dest,data in accepted if dest.name=='material-manifest.json']
  if manifests:
   expected=json.loads(manifests[0].decode('utf-8'))['files'];actual={dest.relative_to(ROOT.resolve()).as_posix():hashlib.sha256(data).hexdigest() for dest,data in accepted if dest.name!='material-manifest.json'}
   if actual!=expected:raise RuntimeError('素材文件与manifest哈希不符，未写入任何文件')
  # Validate the full archive before writing anything.
  for dest,data in accepted:
   if dest.exists() and dest.read_bytes()!=data:
    backup=ROOT/'private/material-backup'/dest.relative_to(ROOT.resolve());backup.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(dest,backup)
   dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(data)
 print('素材已导入。录音仍需在VoiceStudio创建本机声音档案；旧电脑ID不会迁移。')

def smoke(args):
 py=runtime_python()
 if not py.exists() and (ROOT/'profiles/personal.json').is_file():
  legacy=read(ROOT/'profiles/personal.json').get('alignment',{}).get('command',[])
  if legacy:py=Path(legacy[0])
 if not py.is_file():raise RuntimeError('先安装运行环境')
 work=ROOT/'work/environment-smoke';work.mkdir(parents=True,exist_ok=True)
 wav=work/'测试音_不是配音.wav';sr=48000
 with wave.open(str(wav),'wb') as w:
  w.setparams((1,2,sr,0,'NONE','not compressed'));w.writeframes(b''.join(struct.pack('<h',int(1800*math.sin(2*math.pi*440*i/sr))) if i<sr//5 else b'\0\0' for i in range(sr*3)))
 job={'id':'environment-smoke','title':'环境自测 不含克隆配音','covers':{'hook':'环境自测\n不含克隆配音','data':'本地画面\n与音轨测试','question':'先跑通环境\n再配置声音'},'scenes':[{'text':'这是环境自测，不含克隆配音。','headline':'本地环境自测\n不含克隆配音','cards':['画面与字体','音轨编码'],'layout':'comparison','audio':str(wav),'caption_cues':[{'text':'这是环境自测，不含克隆配音。','start':0,'end':3}]}]}
 config={'brand':'环境自测','theme':'studio-paper','fps':30,'voice':{'mode':'recorded'},'avatar':{'mode':'static','photo':'assets/environment-avatar.png'}}
 write(work/'job.json',job);write(work/'profile.json',config)
 call([py,'-X','utf8',ROOT/'scripts/workflow.py','run','--job',work/'job.json','--profile',work/'profile.json'])
 print('环境自测完成；测试音不能证明声音克隆、语气或口型质量。')

def menu():
 if not (ROOT/'profiles/appearance.json').is_file() or read(ROOT/'profiles/appearance.json').get('initialized') is not True:init()
 while True:
  print('\n竖版口播工作流 v1.3\n1 安装运行环境\n2 导入个人素材ZIP\n3 配置本机声音和头像\n4 环境检查\n5 生成3秒环境自测片\n6 重新选择卡片风格和页眉\n7 检查并下载VoiceStudio（视频克隆可选）\n8 安装纯图文环境\n0 退出')
  choice=input('选择：').strip()
  try:
   if choice=='0':return
   if choice=='1':install(argparse.Namespace(skip_browser=False,skip_model=False))
   elif choice=='2':materials(argparse.Namespace(archive=input('素材ZIP路径：').strip().strip('"'),replace=False))
   elif choice=='3':
    photo=None if (ROOT/'avatars/A.png').exists() else input('你的照片路径：').strip().strip('"')
    configure(argparse.Namespace(url='http://127.0.0.1:3900',voice_id=None,photo=photo,brand=input('视频署名（回车用默认）：').strip() or '运营知识讲解',replace=False))
   elif choice=='4':print(json.dumps(system_check(),ensure_ascii=False,indent=2))
   elif choice=='5':smoke(None)
   elif choice=='6':init()
   elif choice=='7':voicestudio()
   elif choice=='8':install_notes(argparse.Namespace(skip_browser=False))
  except Exception as e:print('未完成：',e)

def main():
 p=argparse.ArgumentParser();sub=p.add_subparsers(dest='action',required=True)
 sub.add_parser('menu');c=sub.add_parser('check');c.add_argument('--output-mode',choices=['video','notes']);sub.add_parser('voicestudio')
 a=sub.add_parser('init');a.add_argument('--no-browser',action='store_true')
 a=sub.add_parser('install');a.add_argument('--output-mode',choices=['video','notes']);a.add_argument('--audio-mode',choices=['recorded','clone']);a.add_argument('--skip-browser',action='store_true');a.add_argument('--skip-model',action='store_true')
 a=sub.add_parser('configure');a.add_argument('--output-mode',choices=['video','notes']);a.add_argument('--audio-mode',choices=['recorded','clone']);a.add_argument('--url',default='http://127.0.0.1:3900');a.add_argument('--voice-id');a.add_argument('--photo');a.add_argument('--brand',default='运营知识讲解');a.add_argument('--replace',action='store_true')
 a=sub.add_parser('materials');a.add_argument('archive');a.add_argument('--replace',action='store_true')
 sub.add_parser('smoke');a=p.parse_args()
 if a.action=='menu':menu()
 elif a.action=='check':
  checks=system_check(a.output_mode);print(json.dumps(checks,ensure_ascii=False,indent=2));return 0 if all(v['ok'] for v in checks.values()) else 2
 else:globals()[a.action](a)
 return 0
if __name__=='__main__':
 try:sys.exit(main())
 except Exception as e:print('ERROR:',e,file=sys.stderr);sys.exit(2)
