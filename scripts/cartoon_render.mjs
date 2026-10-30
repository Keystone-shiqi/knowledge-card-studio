import {fileURLToPath} from 'node:url';
import {browserOptions} from './browser_options.mjs';
import fs from 'node:fs';
import path from 'node:path';
import {spawn} from 'node:child_process';
import {once} from 'node:events';
import {chromium} from 'playwright';
const req=JSON.parse(fs.readFileSync(process.argv[2]));
const root=path.dirname(path.dirname(fileURLToPath(import.meta.url)));
const rigs=JSON.parse(fs.readFileSync(path.join(root,'avatars/rigs/landmarks.json')));
const config={...req,rig:rigs[req.avatar_id],image:'data:image/png;base64,'+fs.readFileSync(req.image).toString('base64')};
const browser=await chromium.launch(browserOptions());
let encoder;
try{
 const page=await browser.newPage({viewport:{width:512,height:512}});
 await page.setContent('<body style="margin:0"><canvas width="512" height="512"></canvas></body>');
 await page.evaluate(async cfg=>{
  const img=new Image();img.src=cfg.image;await img.decode();
  const canvas=document.querySelector('canvas'),ctx=canvas.getContext('2d');
  const shapes={A:[.82,.035],B:[1,.12],C:[.94,.3],D:[.84,.5],E:[.49,.42],F:[.4,.28],G:[.88,.13],H:[.92,.22],X:[1,0]};
  const [mx,my,mw]=cfg.rig.mouth;
  function values(t){let c=cfg.mouth_cues.find(c=>c.start<=t&&c.end>t);return shapes[c?.value||'X'];}
  function mouth(t){
   // Smooth within 24ms at transitions without adding cyclic motion unrelated to speech.
   const cur=values(t),prev=values(Math.max(0,t-.024));const w=(cur[0]*.8+prev[0]*.2)*mw,h=(cur[1]*.8+prev[1]*.2)*mw;
   if(h<3)return;
   ctx.save();ctx.translate(mx,my+1);
   ctx.beginPath();ctx.moveTo(-w/2,0);ctx.bezierCurveTo(-w*.24,-h*.25,w*.24,-h*.25,w/2,0);ctx.bezierCurveTo(w*.34,h*.83,-w*.34,h*.83,-w/2,0);ctx.closePath();
   const inner=ctx.createLinearGradient(0,-h*.2,0,h*.65);inner.addColorStop(0,'#432725');inner.addColorStop(.7,'#672e2e');inner.addColorStop(1,'#a45a57');ctx.fillStyle=inner;ctx.fill();
   ctx.lineWidth=3;ctx.strokeStyle='#b77060';ctx.stroke();ctx.clip();
   if(h>9){const teeth=ctx.createLinearGradient(0,0,0,9);teeth.addColorStop(0,'#d1b9a5');teeth.addColorStop(1,'#f7ead5');ctx.fillStyle=teeth;ctx.beginPath();ctx.ellipse(0,-1,w*.43,Math.min(9,h*.23),0,0,Math.PI);ctx.fill();}
   if(h>22){ctx.fillStyle='#b96d70';ctx.beginPath();ctx.ellipse(1,h*.64,w*.22,h*.2,0,0,Math.PI*2);ctx.fill();}
   ctx.restore();
  }
  function blink(t){
   // Stable irregular intervals, about one blink every 3–5 seconds.
   let closeness=0;for(let n=0;n<Math.ceil(cfg.duration/3)+2;n++){const bt=1.9+n*3.75+Math.sin(n*7)*.55;const d=Math.abs(t-bt);if(d<.11)closeness=Math.max(closeness,1-d/.11);}
   if(closeness<.05)return;
   for(const [x,y,rx,ry] of cfg.rig.eyes){
    ctx.save();ctx.beginPath();ctx.ellipse(x,y,rx+2,ry+2,0,0,2*Math.PI);ctx.clip();
    const skin=ctx.createLinearGradient(x,y-ry,x,y+ry);skin.addColorStop(0,'#d99870');skin.addColorStop(.7,'#efb58a');skin.addColorStop(1,'#e8a77d');
    ctx.fillStyle=skin;ctx.fillRect(x-rx-3,y-ry-3,2*rx+6,2*ry+6);
    const open=Math.max(.02,1-closeness);ctx.save();ctx.translate(x,y);ctx.scale(1,open);ctx.drawImage(img,x-rx-2,y-ry-2,2*rx+4,2*ry+4,-rx-2,-ry-2,2*rx+4,2*ry+4);ctx.restore();
    ctx.strokeStyle='#7e4a35';ctx.lineWidth=2;ctx.beginPath();ctx.moveTo(x-rx,y);ctx.quadraticCurveTo(x,y+4*closeness,x+rx,y);ctx.stroke();ctx.restore();
   }
  }
  window.draw=(t)=>{
   ctx.clearRect(0,0,512,512);ctx.save();ctx.scale(512/1254,512/1254);
   // Entire portrait stays in the accepted medium shot, with restrained breathing movement.
   ctx.translate(627,627);ctx.rotate(Math.sin(t*.92)*.0025);ctx.translate(-627,-627+Math.sin(t*1.6)*1.4);
   ctx.drawImage(img,0,0,1254,1254);mouth(t);blink(t);ctx.restore();
  };
 },config);
 encoder=spawn('ffmpeg',['-v','error','-y','-f','image2pipe','-vcodec','png','-framerate',String(req.fps),'-i','pipe:0','-an','-c:v','libx264','-preset','fast','-crf','18','-pix_fmt','yuv420p','-movflags','+faststart',req.output],{stdio:['pipe','ignore','inherit']});
 let pipeError;encoder.stdin.on('error',e=>{pipeError=e});const completion=once(encoder,'close');
 const frames=Math.ceil(req.duration*req.fps);
 for(let f=0;f<frames;f++){
  const png=await page.evaluate(t=>{window.draw(t);return document.querySelector('canvas').toDataURL('image/png').split(',')[1]},f/req.fps);
  const buffer=Buffer.from(png,'base64');
  if(pipeError)throw pipeError;
  if(!encoder.stdin.write(buffer))await once(encoder.stdin,'drain');
 }
 encoder.stdin.end();const [code]=await completion;if(code)throw Error('Avatar ffmpeg failed '+code);
 console.log('Animated avatar:',req.output);
}finally{if(encoder&&!encoder.stdin.destroyed)encoder.stdin.destroy();await browser.close();}
