import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {spawnSync} from 'node:child_process';
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const runtimeFile=path.join(root,'.runtime/runtime.json');const runtime=fs.existsSync(runtimeFile)?JSON.parse(fs.readFileSync(runtimeFile,'utf8')):{};
const env={...process.env,PYTHONUTF8:'1'};
for(const name of ['node','ffmpeg','ffprobe'])if(runtime[name]&&fs.existsSync(runtime[name]))env.PATH=path.dirname(runtime[name])+path.delimiter+(env.PATH||'');
if(runtime.browser&&fs.existsSync(runtime.browser)){env.WORKFLOW_CHROME=runtime.browser;env.HYPERFRAMES_BROWSER_PATH=runtime.browser;}
const [action,...extra]=process.argv.slice(2);let command,args;
if(['check','render'].includes(action)){
 const dir=path.join(root,'node_modules/hyperframes');const meta=JSON.parse(fs.readFileSync(path.join(dir,'package.json'),'utf8'));
 command=process.execPath;args=[path.join(dir,typeof meta.bin==='string'?meta.bin:meta.bin.hyperframes),action,...extra];
}else if(['doctor','smoke'].includes(action)){
 const config=path.join(root,'.runtime/runtime.json');let py;
 if(fs.existsSync(config))py=JSON.parse(fs.readFileSync(config,'utf8')).python;
 else {const p=path.join(root,'profiles/personal.json');if(fs.existsSync(p))py=JSON.parse(fs.readFileSync(p,'utf8')).alignment?.command?.[0];}
 if(!py)throw Error('Run the platform setup launcher first.');
 command=py;args=['-X','utf8',path.join(root,'scripts',action==='smoke'?'portable.py':'workflow.py'),action,...(action==='doctor'&&fs.existsSync(path.join(root,'profiles/personal.json'))?['--profile',path.join(root,'profiles/personal.json')]:[]),...extra];
}else throw Error('Choose doctor, smoke, check or render');
const result=spawnSync(command,args,{cwd:root,stdio:'inherit',env});
if(result.error)throw result.error;process.exitCode=result.status??2;
