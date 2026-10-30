#!/usr/bin/env python3
"""Image-only note export. No TTS, ASR, FFmpeg or HyperFrames invocation."""
import argparse,datetime as dt,json,os,shutil,subprocess,sys,re
from pathlib import Path
from presentation import STYLES,validate_header
ROOT=Path(__file__).resolve().parents[1]

def load(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def write(p,data):Path(p).write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
def validate(job):
    if not isinstance(job.get('title'),str) or not job['title'].strip():raise ValueError('图文需要title')
    pages=job.get('pages')
    if not isinstance(pages,list) or not 1<=len(pages)<=18:raise ValueError('pages需为1–18页，长内容请分篇')
    for p in pages:
        if not isinstance(p,dict) or not isinstance(p.get('headline'),str) or not p['headline'].strip():raise ValueError('每页需要headline')
        if len(p['headline'])>48:raise ValueError('单页标题最多48字；请缩短或拆页')
        if p.get('layout','cover') not in ('cover','comparison','flow','stat','image','takeaway'):raise ValueError('未知图文layout')
        if len(p.get('cards',[]))>4 or len(p.get('images',[]))>2 or len(p.get('rows',[]))>2:raise ValueError('每页最多4卡/2图/2条流程链，请拆页')
        for row in p.get('rows',[]):
            if not 2<=len(row.get('steps',[]))<=4:raise ValueError('每条流程需2–4步')
        for card in p.get('cards',[]):
            if not isinstance(card,dict) or not card.get('title'):raise ValueError('图文card需要title，可选body')
            if len(card['title'])>22 or len(card.get('body',''))>110:raise ValueError('卡片文字过长，请拆页')
        if len(p.get('sources',[]))>3 or any(len(str(x))>100 for x in p.get('sources',[])):raise ValueError('来源说明最多3条，每条100字')

def build(args):
    job=load(args.job);validate(job)
    profile=load(args.profile) if args.profile else {}
    appearance=load(ROOT/'profiles/appearance.json') if (ROOT/'profiles/appearance.json').is_file() else {}
    theme=args.style or job.get('theme') or appearance.get('theme') or profile.get('theme') or 'brief-light'
    if theme not in STYLES:raise ValueError('未知风格 '+str(theme))
    for page in job['pages']:
        if page.get('theme',theme) not in STYLES:raise ValueError('单页主题不存在')
    header={'brand':profile.get('brand','我的知识笔记'),'tagline':'','visible':True,'section_prefix':'','show_number':False}
    for source in [profile,appearance,job]:header.update(validate_header(source.get('header',{})))
    ratio=job.get('ratio','3:4')
    if ratio not in ('3:4','9:16'):raise ValueError('图文比例可选3:4或9:16')
    stamp=dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    slug=re.sub(r'[^\w-]','-',job.get('id','notes'))[:40]
    out=Path(args.output).expanduser().resolve() if args.output else ROOT/'jobs'/('notes-'+slug+'-'+stamp)
    if out.exists() and any(out.iterdir()):raise ValueError('输出目录非空，请使用新目录')
    out.mkdir(parents=True,exist_ok=True);(out/'media').mkdir()
    write(out/'status.json',{'state':'running','output_mode':'notes'})
    try:
        for index,page in enumerate(job['pages']):
            for j,im in enumerate(page.get('images',[])):
                source=Path(im['path']).expanduser()
                if not source.is_absolute():source=Path(args.job).resolve().parent/source
                if not source.is_file() or source.suffix.lower() not in ('.png','.jpg','.jpeg','.webp'):raise ValueError('图片需为本地PNG/JPG/WebP：'+str(source))
                name=f'image-{index}-{j}'+source.suffix.lower();shutil.copy2(source,out/'media'/name);im['src']='media/'+name;im.pop('path',None)
        manifest=dict(job,theme=theme,header=header,width=1080,height=1440 if ratio=='3:4' else 1920,output_mode='notes',workflow_version='1.3.0')
        write(out/'manifest.json',manifest)
        runtime=load(ROOT/'.runtime/runtime.json') if (ROOT/'.runtime/runtime.json').is_file() else {}
        node=runtime.get('node') or shutil.which('node')
        if not node or not Path(node).is_file():raise ValueError('未找到Node，请先安装图文运行环境')
        subprocess.run([node,str(ROOT/'scripts/notes.mjs'),str(out)],cwd=ROOT,check=True)
        lines=['# '+job['title'],'',job.get('caption',''),'']
        if job.get('tags'):lines+=[' '.join('#'+str(tag).lstrip('#') for tag in job['tags']),'']
        lines+=['## 图片顺序','']+[f"{i+1:02d} {page['headline'].replace(chr(10),' ')}" for i,page in enumerate(job['pages'])]
        (out/'发布文案.md').write_text('\n'.join(lines),encoding='utf-8')
        write(out/'status.json',{'state':'images_ready','output_mode':'notes','pages':len(job['pages']),'audio_generated':False,'video_rendered':False,'notes':['直接导出PNG/JPG，无配音和视频渲染；内容、图片与来源请按原稿核对。']})
        print('OUTPUT: '+str(out))
    except Exception as e:write(out/'status.json',{'state':'failed','error':str(e),'output_mode':'notes'});raise

def main():
    p=argparse.ArgumentParser();p.add_argument('--job',required=True);p.add_argument('--profile');p.add_argument('--style',choices=list(STYLES));p.add_argument('--output');build(p.parse_args())
if __name__=='__main__':
    try:main()
    except Exception as e:print('ERROR: '+str(e),file=sys.stderr);sys.exit(1)
