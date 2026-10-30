import {styleOf,headerOf,sectionHeader} from './presentation.mjs';
import {pathToFileURL} from 'node:url';
import {browserOptions} from './browser_options.mjs';
import {cleanHeading,bodyFontCSS,sceneBodyFontCSS,headingFontCSS,sceneHeadingFontCSS,headingFamily,prepareTypography} from './typography.mjs';
import fs from 'node:fs';
import path from 'node:path';
import {chromium} from 'playwright';
const dir=path.resolve(process.argv[2]);const m=JSON.parse(fs.readFileSync(path.join(dir,'manifest.json'),'utf8'));
prepareTypography(dir);
const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const output=path.join(dir,'covers');fs.mkdirSync(output,{recursive:true});
const browser=await chromium.launch(browserOptions());
const results=[];
try{
 const theme=styleOf(m),header=headerOf(m),bg=theme.bg,fg=theme.fg,accent=theme.accent;
 const extraCSS=theme.family==='paper'?'.content{background:#fff;padding:42px 38px;box-shadow:0 20px 30px #23313d20;border-radius:18px;transform:rotate(-1deg)}h1{font-size:var(--title-size)!important}':theme.family==='editorial'?'.brand{border-bottom:3px solid currentColor}.content{border-top:2px solid currentColor;padding-top:32px}.pill{border-top:1px solid currentColor;padding-top:24px}.line{height:3px;width:100%}':theme.family==='swiss'?`.brand{border-bottom:8px solid ${accent}}.kicker b{background:${accent};color:${theme.on_accent};padding:9px 14px}.pill{padding:24px;background:${theme.card}}.line{height:8px;width:100%}.portrait{box-shadow:none}`:'';
 const variants=[['A_观点','hook','本期观点'],['B_数据','data','重点拆解'],['C_提问','question','先问一个问题']];
 for(const [name,key,kicker] of variants){for(const height of [1920,1440]){
  const title=cleanHeading(m.covers[key]||m.title);const number=m.scenes.find(s=>s.number)?.number;
  const longest=Math.max(...title.split('\n').map(line=>Array.from(line).length));
  const titleWidth=theme.family==='paper'?840:928;
  const titleSize=Math.min(title.length>20?79:99,Math.floor(titleWidth/Math.max(longest,1)));
  const page=await browser.newPage({viewport:{width:1080,height},deviceScaleFactor:1});
  const middle=height===1920?420:260;
  const art=key==='data'?`<div class="number">${esc(number||'重点')}</div><div class="pill">${esc(m.covers.data_note||m.scenes[0].cards?.[0]||'看清问题，再做选择')}</div>`:key==='question'?`<div class="question">?</div><div class="pill">${esc(m.scenes.at(-1).takeaway||'你的情况，适合哪一种？')}</div>`:`<div class="line"></div><div class="pill">${esc(m.scenes[0].takeaway||'把复杂的问题，讲清楚。')}</div>`;
  const html=`<!doctype html><html lang="zh-CN"><meta charset="utf-8"><style>${sceneHeadingFontCSS}${sceneBodyFontCSS}*{box-sizing:border-box}body{margin:0;width:1080px;height:${height}px;background:${bg};color:${fg};font-family:WorkflowCN,sans-serif;padding:76px}.brand{font-size:27px;border-bottom:2px solid ${fg};padding:15px 0 30px}.content{position:absolute;left:76px;right:76px;top:${middle}px}.kicker{color:${accent};font-size:30px;font-weight:700;margin-bottom:36px}.kicker{display:flex;gap:18px;align-items:center}.kicker b{flex-shrink:0}.brand{display:flex;justify-content:space-between;gap:18px}.brand>span{max-width:56%;overflow-wrap:anywhere;line-height:1.4}.brand .tag{max-width:40%;text-align:right;color:${theme.muted};font-size:24px}h1{font-synthesis:none;font-family:${headingFamily};font-size:${titleSize}px;line-height:1.25;letter-spacing:-2px;margin:0;font-weight:700;white-space:pre-line;word-break:break-word}.line{height:12px;width:185px;background:${accent};margin-top:60px}.number{font-size:190px;font-weight:900;line-height:1.2;color:${accent};margin-top:40px}.question{font-size:190px;font-weight:900;line-height:1.2;color:${accent};margin-top:30px}.pill{font-size:30px;line-height:1.5;margin-top:40px;max-width:850px}.footer{position:absolute;left:76px;bottom:130px;color:${accent};font-size:24px}.portrait{position:absolute;width:240px;height:240px;object-fit:cover;border-radius:50%;border:8px solid white;right:76px;bottom:110px}${extraCSS}</style><body>${header.visible?`<div class="brand" data-fit><span>${esc(header.brand)}</span><span class="tag">${esc(header.tagline)}</span></div>`:''}<main class="content" style="--title-size:${titleSize}px">${sectionHeader(m,{index:0,label:kicker})}<h1 data-fit>${esc(title)}</h1>${art}</main><div class="footer">${esc(m.demo?'模板演示 · 非本人音色':header.tagline)}</div>${(m.avatar||m.cover_portrait)?`<img class="portrait" src="${pathToFileURL(path.join(dir,'media/portrait.jpg')).href}">`:''}</body></html>`;
  const htmlFile=path.join(output,`${name}_${height}.html`);fs.writeFileSync(htmlFile,html);
  await page.goto(pathToFileURL(htmlFile).href,{waitUntil:'domcontentloaded',timeout:60000});
  await page.waitForFunction(()=>document.fonts.status==='loaded'&&[...document.images].every(img=>img.complete&&img.naturalWidth>0),null,{timeout:60000});
  if(!await page.evaluate(()=>document.fonts.check('700 30px WorkflowHeading')&&document.fonts.check('400 30px WorkflowCN')))throw Error('封面嵌入字体未加载');
  const issues=await page.evaluate(()=>{const all=[...document.querySelectorAll('h1,.pill,.brand,.content')];return all.flatMap(el=>{const r=el.getBoundingClientRect();return r.right>innerWidth-40||r.bottom>innerHeight-100||el.scrollWidth>el.clientWidth+2?[el.className||el.tagName]:[]})});
  if(issues.length)throw Error(`封面溢出 ${name}/${height}: ${issues.join(',')}`);
  await page.screenshot({path:path.join(output,`${name}_${height===1920?'9x16':'3x4'}.png`)});
  results.push({name,height,overflow:issues});await page.close();
 }}
 fs.writeFileSync(path.join(output,'check.json'),JSON.stringify(results,null,2));
}catch(error){process.exitCode=1;console.error(error)}finally{await Promise.race([browser.close(),new Promise(resolve=>setTimeout(resolve,10000))]);process.exit(process.exitCode||0)}
