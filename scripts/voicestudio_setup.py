"""Download a pinned official VoiceStudio installer; never accept model terms."""
import hashlib,json,os,platform,re,shutil,subprocess,sys,time
from pathlib import Path
from urllib.request import Request,urlopen
VERSION='0.5.7'
BASE=f'https://github.com/debpalash/VoiceStudio/releases/download/v{VERSION}/'
RELEASE=f'https://github.com/debpalash/VoiceStudio/releases/tag/v{VERSION}'
# Verified against the official GitHub expanded-assets metadata for v0.5.7.
OFFICIAL_SHA256={
 'VoiceStudio-0.5.7-mac-arm64.dmg':'8db7a16f35af1e4eaca25c389d376acc86b3885f30d1982f5fd6497953f888a0',
 'VoiceStudio-0.5.7-win-x64.exe':'76c6385d404ae9f11b9e47d42996432ea4cd6c065afb06718c4842b39020cd80',
}

def installed_app():
    if sys.platform=='darwin':
        return next((p for p in (Path('/Applications/VoiceStudio.app'),Path.home()/'Applications/VoiceStudio.app') if p.is_dir()),None)
    if sys.platform=='win32':
        candidates=[]
        for env in ('LOCALAPPDATA','PROGRAMFILES','PROGRAMFILES(X86)'):
            if os.environ.get(env):
                base=Path(os.environ[env]);candidates.extend([base/'Programs/VoiceStudio/VoiceStudio.exe',base/'Programs/voicestudio/VoiceStudio.exe',base/'VoiceStudio/VoiceStudio.exe',base/'voicestudio/VoiceStudio.exe'])
        if shutil.which('VoiceStudio.exe'):candidates.append(Path(shutil.which('VoiceStudio.exe')))
        # Electron installers may use a custom directory recorded by Windows.
        import winreg
        for hive in (winreg.HKEY_CURRENT_USER,winreg.HKEY_LOCAL_MACHINE):
            for branch in (r'Software\Microsoft\Windows\CurrentVersion\Uninstall',r'Software\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall'):
                try:
                    with winreg.OpenKey(hive,branch) as parent:
                        for i in range(winreg.QueryInfoKey(parent)[0]):
                            try:
                                with winreg.OpenKey(parent,winreg.EnumKey(parent,i)) as key:
                                    name=winreg.QueryValueEx(key,'DisplayName')[0]
                                    if name.lower().startswith('voicestudio'):
                                        try:candidates.append(Path(winreg.QueryValueEx(key,'InstallLocation')[0])/'VoiceStudio.exe')
                                        except OSError:pass
                            except OSError:pass
                except OSError:pass
        return next((p for p in candidates if p.is_file()),None)
    return None

def asset_name(system=None,machine=None):
    system=system or sys.platform;machine=(machine or platform.machine()).lower()
    if system=='darwin' and machine in ('arm64','aarch64'):return f'VoiceStudio-{VERSION}-mac-arm64.dmg'
    if system=='win32' and machine in ('amd64','x86_64','x64'):return f'VoiceStudio-{VERSION}-win-x64.exe'
    raise RuntimeError('自动下载当前支持Mac M系列和Windows x64。其他架构请按VoiceStudio官方平台说明处理：'+RELEASE)

def fetch(url,target):
    """Verified TLS only. curl fallback handles some system-Python TLS setups."""
    target=Path(target);target.parent.mkdir(parents=True,exist_ok=True)
    try:
        with urlopen(Request(url,headers={'User-Agent':'PortraitNarrationSetup/1.1.2'}),timeout=30) as response,target.open('wb') as output:
            total=int(response.headers.get('Content-Length') or 0);done=0;last=time.monotonic()
            while True:
                chunk=response.read(1024*1024)
                if not chunk:break
                output.write(chunk);done+=len(chunk)
                if time.monotonic()-last>=5:
                    print(f'VoiceStudio下载：{done/1048576:.1f} MB'+(f' / {total/1048576:.1f} MB' if total else ''),flush=True);last=time.monotonic()
            if total and done!=total:raise RuntimeError('下载长度不完整')
    except Exception:
        target.unlink(missing_ok=True)
        curl=shutil.which('curl.exe') if os.name=='nt' else shutil.which('curl')
        if not curl:raise
        subprocess.run([curl,'--fail','--location','--show-error','--retry','2','--connect-timeout','20','--output',str(target),url],check=True)

def expected_hash(text,name):
    for line in text.splitlines():
        match=re.match(r'^([0-9a-fA-F]{64})\s+\*?(.+?)\s*$',line)
        if match and match[2]==name:return match[1].lower()
    raise RuntimeError('官方SHA256清单中找不到安装包；停止安装：'+name)

def digest(file):
    h=hashlib.sha256()
    with Path(file).open('rb') as source:
        for data in iter(lambda:source.read(1024*1024),b''):h.update(data)
    return h.hexdigest()

def ensure_voicestudio(root,open_installer=True):
    root=Path(root);app=installed_app()
    if app:
        print('VoiceStudio已安装，复用现有软件，不重复下载。',flush=True)
        return {'state':'installed','path':str(app)}
    headers={}
    if os.environ.get('VOICESTUDIO_API_KEY'):headers['Authorization']='Bearer '+os.environ['VOICESTUDIO_API_KEY']
    try:
        with urlopen(Request('http://127.0.0.1:3900/openapi.json',headers=headers),timeout=3) as response:contract=json.load(response)
        if '/generate' in contract.get('paths',{}) and '/profiles' in contract.get('paths',{}):
            print('检测到运行中的VoiceStudio后端，复用现有服务，不安装第二套。',flush=True)
            return {'state':'running_backend'}
    except Exception:pass
    name=asset_name();folder=root/'.runtime/installers/voicestudio';folder.mkdir(parents=True,exist_ok=True)
    sums=folder/'SHA256SUMS.txt';part=folder/(name+'.part');target=folder/name
    try:
        print('未检测到VoiceStudio，开始下载官方安装包 '+name,flush=True)
        expected=OFFICIAL_SHA256[name]
        sums.write_text(expected+'  '+name+'\n',encoding='utf-8')
        if not target.is_file() or digest(target)!=expected:
            fetch(BASE+name,part)
            if digest(part)!=expected:
                part.unlink(missing_ok=True);raise RuntimeError('安装包SHA256不匹配，未打开文件。')
            part.replace(target)
        state={'state':'installer_downloaded','version':VERSION,'installer':str(target),'sha256':expected,'source':RELEASE}
        (folder/'download-state.json').write_text(json.dumps(state,ensure_ascii=False,indent=2),encoding='utf-8')
        if open_installer:
            if sys.platform=='darwin':subprocess.run(['open',str(target)],check=True)
            elif sys.platform=='win32':os.startfile(str(target))
        print('官方安装包已校验'+('并打开' if open_installer else '')+'。请完成系统安装提示；之后在VoiceStudio启用MOSS并创建声音档案。',flush=True)
        return state
    except Exception as e:
        part.unlink(missing_ok=True)
        (folder/'download-state.json').write_text(json.dumps({'state':'failed','error':str(e),'source':RELEASE},ensure_ascii=False,indent=2),encoding='utf-8')
        raise RuntimeError('VoiceStudio下载未完成，请检查网络后重试。未使用第三方镜像或绕过TLS校验。官方页面：'+RELEASE+'；原因：'+str(e)) from e
