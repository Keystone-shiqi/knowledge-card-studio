// Verify real HyperFrames runtime state before/after every card reveal, including reverse seeks.
import fs from 'node:fs';import path from 'node:path';import {pathToFileURL} from 'node:url';
import {chromium} from 'playwright';import {browserOptions} from './browser_options.mjs';
const dir=path.resolve(process.argv[2]),m=JSON.parse(fs.readFileSync(path.join(dir,'manifest.json')));
const dist=path.resolve(import.meta.dirname,'../node_modules/hyperframes/dist');
const compiler=fs.readdirSync(dist).find(n=>/^compiler-.*\.js$/.test(n));
if(!compiler)throw Error('HyperFrames compiler not found; use pinned package-lock');
const {bundleToSingleHtml}=await import(pathToFileURL(path.join(dist,compiler)));
const html=await bundleToSingleHtml(dir),file=path.join(dir,'.motion-check.html');
fs.writeFileSync(file,html.replace(/<head([^>]*)>/i,`<head$1><base href="${pathToFileURL(dir+path.sep).href}">`));
const browser=await chromium.launch(browserOptions()),samples=[],issues=[];
try{
 const page=await browser.newPage({viewport:{width:1080,height:1920}});const errors=[];
 page.on('pageerror',e=>errors.push(e.message));
 await page.goto(pathToFileURL(file).href,{waitUntil:'load',timeout:60000});
 await page.waitForFunction(()=>typeof window.__player?.seek==='function'&&Object.keys(window.__timelines||{}).length>0,null,{timeout:15000,polling:100}).catch(async e=>{console.error('Page errors:',errors,await page.evaluate(()=>({ready:window.__renderReady,keys:Object.keys(window.__timelines||{}),scripts:[...document.scripts].map(s=>s.src||s.textContent.slice(0,70))})));throw e});
 const plan=[];
 for(const s of m.scenes){
  if(!s.cards?.length)continue;
  if(!Array.isArray(s.card_at)||s.card_at.length!==s.cards.length)throw Error('Missing checked card_at for scene '+s.index);
  for(const at of s.card_at){if(at>.1)plan.push({scene:s,time:s.start+at-.08});plan.push({scene:s,time:Math.min(s.start+at+.48,s.start+s.duration-.01)})}
 }
 // Forward then reverse order catches state leakage that start/midpoint screenshots miss.
 for(const {scene:s,time} of [...plan,...plan.slice().reverse()]){
  await page.evaluate(t=>{window.__player.seek(t)},time);
  const states=await page.evaluate(index=>{
   const prefix=document.querySelector('#paper'+index+'-card0')?'paper'+index:'s'+index;
   return Array.from(document.querySelectorAll(`[id^="${prefix}-card"]`)).map(e=>{const c=getComputedStyle(e);let visible=c.visibility!=='hidden'&&c.display!=='none'&&Number(c.opacity)>.05;for(let p=e.parentElement;p;p=p.parentElement){const z=getComputedStyle(p);if(z.visibility==='hidden'||z.display==='none'||Number(z.opacity)<.01)visible=false}return {id:e.id,visible,opacity:Number(c.opacity)}})
  },s.index);
  if(states.length!==s.cards.length)issues.push({scene:s.index,time,error:'card DOM count mismatch',count:states.length});
  states.forEach((state,i)=>{const dt=time-s.start-s.card_at[i];if(dt<-.02&&state.visible||dt>.43&&!state.visible)issues.push({scene:s.index,time,card:i,expected:dt>0?'visible':'hidden',state})});
  samples.push({scene:s.index,time,visible:states.map(x=>x.visible)});
 }
 if(errors.length)issues.push({page_errors:errors});
 const report={ok:issues.length===0,checks:samples.length,samples,issues};
 fs.writeFileSync(path.join(dir,'card-reveal-check.json'),JSON.stringify(report,null,2));
 if(issues.length)throw Error('Card reveal check failed: '+JSON.stringify(issues.slice(0,3)));
 console.log('Card reveal checks passed: '+samples.length+' forward/reverse samples');
}finally{fs.rmSync(file,{force:true});await Promise.race([browser.close(),new Promise(r=>{const timer=setTimeout(r,5000);timer.unref()})]);process.exitCode=issues.length?1:process.exitCode;}
