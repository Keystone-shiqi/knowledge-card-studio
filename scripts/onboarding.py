"""Loopback-only first-use style picker. No voice credentials served to the page."""
import argparse,json,secrets,time,webbrowser
from http.server import BaseHTTPRequestHandler,HTTPServer
from pathlib import Path
from urllib.parse import urlparse
from presentation import STYLES,validate_header
ROOT=Path(__file__).resolve().parents[1]

def save_choice(root,data):
    if not isinstance(data,dict) or data.get('theme') not in STYLES:
        raise ValueError('请选择一种卡片风格')
    output=data.get('output_mode','video')
    if output not in ('video','notes'):raise ValueError('请选择视频或图文')
    if output not in STYLES[data['theme']].get('modes',['notes','video']):raise ValueError('该风格仅支持图文，请重新选择视频风格')
    mode=data.get('audio_source','recorded')
    if mode not in ('recorded','clone'):raise ValueError('请选择上传配音或文字克隆')
    h=data.get('header',{})
    if set(h)-{'brand','tagline'}:raise ValueError('初始化仅设置品牌与栏目')
    validate_header(h)
    value={'theme':data['theme'],'header':dict(h,section_prefix='',show_number=False),'initialized':True,'version':'1.3.1','audio_source':mode,'output_mode':output}
    dest=root/'profiles/appearance.json';dest.parent.mkdir(parents=True,exist_ok=True)
    tmp=dest.with_suffix('.new');tmp.write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf-8');tmp.replace(dest)
    return value

def serve(root=ROOT,open_browser=True,timeout=600,ready_file=None):
    token=secrets.token_urlsafe(24);state={'saved':False};base=root/'assets/onboarding'
    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*args):pass
        def response(self,code,body,kind='application/json'):
            if not isinstance(body,bytes):body=json.dumps(body,ensure_ascii=False).encode('utf-8')
            self.send_response(code);self.send_header('Content-Type',kind+'; charset=utf-8');self.send_header('Content-Length',str(len(body)));self.send_header('Cache-Control','no-store');self.send_header('X-Content-Type-Options','nosniff');self.end_headers();self.wfile.write(body)
        def do_GET(self):
            route=urlparse(self.path).path
            if not route.startswith('/'+token+'/'):return self.response(404,{'error':'not found'})
            name=route[len(token)+2:]
            if name=='state':
                p=root/'profiles/appearance.json';return self.response(200,json.loads(p.read_text(encoding='utf-8')) if p.exists() else {})
            if name=='styles':return self.response(200,STYLES)
            if name=='':file=base/'index.html';kind='text/html'
            elif name.startswith('previews/') and name[9:] in [k+'.jpg' for k in STYLES]:file=base/name;kind='image/jpeg'
            elif name in ('comparison.jpg','notes-comparison.jpg'):file=base/name;kind='image/jpeg'
            else:return self.response(404,{'error':'not found'})
            if not file.is_file():return self.response(404,{'error':'asset missing'})
            return self.response(200,file.read_bytes(),kind)
        def do_POST(self):
            if urlparse(self.path).path!='/'+token+'/save':return self.response(404,{'error':'not found'})
            origin=self.headers.get('Origin')
            if origin and origin!=f'http://127.0.0.1:{self.server.server_port}':return self.response(403,{'error':'origin mismatch'})
            try:
                length=int(self.headers.get('Content-Length','0'))
                if not 0<length<=16384:raise ValueError('请求长度无效')
                value=save_choice(root,json.loads(self.rfile.read(length)))
                self.response(200,{'ok':True,'appearance':value});state['saved']=True
            except (ValueError,TypeError) as e:self.response(400,{'error':str(e)})
    with HTTPServer(('127.0.0.1',0),Handler) as server:
        server.timeout=.5;url=f'http://127.0.0.1:{server.server_port}/{token}/'
        print('首次初始化：请选择输出形式与卡片风格并保存。\n'+url,flush=True)
        if ready_file:Path(ready_file).write_text(url,encoding='utf-8')
        if open_browser:webbrowser.open(url)
        until=time.monotonic()+timeout
        while not state['saved'] and time.monotonic()<until:server.handle_request()
    if not state['saved']:raise RuntimeError('未保存风格选择；没有替用户选择默认风格。可重新运行 init。')
    print('已保存风格；后续生成自动使用，随时可重新选择。',flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,default=ROOT);p.add_argument('--no-browser',action='store_true');p.add_argument('--ready-file');p.add_argument('--timeout',type=int,default=600);a=p.parse_args()
    serve(a.root,not a.no_browser,a.timeout,a.ready_file)
