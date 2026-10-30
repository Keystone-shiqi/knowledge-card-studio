import {styleOf,headerOf,sectionHeader,topbar} from './presentation.mjs';
import {cleanHeading,bodyFontCSS,sceneBodyFontCSS,headingFontCSS,sceneHeadingFontCSS,headingFamily,prepareTypography} from './typography.mjs';
import {avatarMarkup} from './avatar_markup.mjs';
import fs from 'node:fs';
import path from 'node:path';
const dir=path.resolve(process.argv[2]);
prepareTypography(dir);
const m=JSON.parse(fs.readFileSync(path.join(dir,'manifest.json'),'utf8'));
const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
if(styleOf(m).family!=='classic'){await import('./compose-paper.mjs');process.exit(0)}
const dark=m.theme==='navy';
const colors=dark?{bg:'#08192B',fg:'#F5F2E9',red:'#FFD067',card:'#143150',muted:'#BBCCDC'}:{bg:'#EEF1F3',fg:'#182129',red:'#B52F17',card:'#FFFFFF',muted:'#4A5862'};
let scenes='',anim='';
for(const s of m.scenes){
 const id=`s${s.index}`,cards=s.cards?.length?s.cards:[s.text];
 const headlineSize=s.headline.length>22?65:82;
 scenes+=`<section id="${id}" class="clip scene" data-start="${s.start}" data-duration="${s.duration+(s.index===m.scenes.length-1?0.4:0)}" data-track-index="1">
 <div class="scene-inner" id="${id}-inner">${sectionHeader(m,s)}
 <h1 style="font-size:${headlineSize}px">${esc(cleanHeading(s.headline))}</h1>
 ${s.number?`<div class="stat"><strong>${esc(s.number)}</strong><span>${esc(s.unit||'')}</span></div>`:''}
 <div class="cards ${s.number?'with-stat':''}">${cards.map((c,i)=>`<div class="card" id="${id}-card${i}"><span class="card-index">0${i+1}</span><p>${esc(c)}</p></div>`).join('')}</div>
 <div class="scene-foot">${esc(s.takeaway||'把复杂的问题，讲清楚。')}</div></div></section>`;
 anim+=`tl.fromTo('#${id}-inner',{opacity:0,y:35},{opacity:1,y:0,duration:.42,ease:'power3.out'},${s.start});\n`;
 cards.forEach((_,i)=>{anim+=`tl.fromTo('#${id}-card${i}',{opacity:0,y:45,rotation:${i%2?1.3:-1.3}},{opacity:1,y:0,rotation:0,duration:.5,ease:'power3.out'},${s.start+0.3+i*0.25});\n`;});
}
const caps=m.captions.map((c,i)=>`<div id="cap${i}" class="clip caption" data-start="${c.start}" data-duration="${(c.end-c.start).toFixed(3)}" data-track-index="4" data-track-kind="captions" data-layout-allow-caption-zone="true"><span>${esc(c.text)}</span></div>`).join('');
const avatar=avatarMarkup(m);
const html=`<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=1080,height=1920"><script src="media/gsap.min.js"></script><style>
${bodyFontCSS}${headingFontCSS}
*{box-sizing:border-box;margin:0}html,body{width:1080px;height:1920px;overflow:hidden;background:${colors.bg};font-family:WorkflowCN,sans-serif;color:${colors.fg}}
#root{position:relative;width:1080px;height:1920px}.backdrop{position:absolute;inset:0;background:radial-gradient(ellipse at 80% 5%,${dark?'#183451':'#FFFFFF'} 0%,${colors.bg} 70%)}
.topbar{position:absolute;left:76px;top:145px;width:928px;display:flex;align-items:center;gap:18px;font-size:28px;font-weight:700;letter-spacing:2px;border-bottom:2px solid ${colors.muted};padding-bottom:25px}.dot{width:13px;height:13px;border-radius:50%;background:${colors.red}}.series{margin-left:auto;color:${colors.muted};font-size:28px}
.scene{position:absolute;inset:0}.scene-inner{position:absolute;left:76px;top:280px;width:928px}.eyebrow{color:${colors.red};font-size:28px;font-weight:650;margin-bottom:32px;letter-spacing:3px}.eyebrow span{float:right;color:${colors.muted};font-size:28px}h1{font-synthesis:none;font-family:${headingFamily};font-weight:700;line-height:1.26;letter-spacing:-1px;padding-bottom:14px;white-space:pre-line;word-break:break-word}
.stat{height:235px;display:flex;align-items:baseline;gap:24px;padding-top:18px}.stat strong{font-size:174px;letter-spacing:-8px;line-height:1.2;color:${colors.red}}.stat span{font-size:30px}
.cards{display:flex;flex-direction:column;gap:26px;margin-top:58px}.cards.with-stat{margin-top:25px}.card{display:flex;align-items:center;gap:26px;background:${colors.card};border:1px solid ${dark?'#365673':'#DEE3E7'};border-radius:23px;box-shadow:0 13px 20px #0000000D;padding:32px;min-height:132px}.card-index{flex-shrink:0;background:${colors.fg};color:${colors.bg};border-radius:10px;padding:9px;font-size:28px;font-weight:800}.card p{font-size:36px;font-weight:650;line-height:1.46;word-break:break-word}.scene-foot{margin-top:40px;padding-left:22px;border-left:6px solid ${colors.red};font-size:28px;line-height:1.6;color:${colors.muted};max-width:850px}
.avatar{position:absolute;left:708px;top:1330px;width:278px;height:278px;object-fit:cover;border-radius:50%;border:9px solid white;box-shadow:0 12px 32px #00000025;z-index:8}.caption{position:absolute;left:76px;top:1640px;width:928px;text-align:center;z-index:10;font-size:40px;font-weight:650;line-height:1.5}.caption span{display:inline-block;padding:14px 28px;border-radius:10px;color:#FFFFFF;background:#182129;max-width:100%}.demo-note{position:absolute;left:76px;top:1480px;font-size:28px;color:${colors.muted}}.progress{position:absolute;left:76px;top:1790px;width:928px;height:5px;background:${dark?'#28405A':'#CED6DD'}}.progress-fill{width:100%;height:100%;background:${colors.red};transform-origin:left center}.tail{position:absolute;left:76px;top:750px;width:928px;font-size:70px;line-height:1.4;font-weight:800}.tail small{display:block;font-size:30px;color:${colors.red};margin-bottom:28px}
.kicker{display:flex;gap:20px;color:${colors.muted};font-size:28px;margin-bottom:32px}.kicker b{color:${colors.red};flex-shrink:0}.brand-name{max-width:550px;overflow-wrap:anywhere;line-height:1.4}.tag{max-width:330px;text-align:right;overflow-wrap:anywhere;line-height:1.4;margin-left:auto;color:${colors.muted};font-size:28px;font-weight:400}</style></head><body><div id="root" data-composition-id="main" data-start="0" data-duration="${m.duration}" data-width="1080" data-height="1920" data-fps="${m.fps}"><div class="backdrop"></div>${topbar(m)}${scenes}${avatar}${caps}<audio id="narration" src="media/narration.wav" data-start="0" data-duration="${m.speech_duration}" data-track-index="5"></audio><div class="progress"><div id="progress-fill" class="progress-fill"></div></div></div><script>window.__timelines=window.__timelines||{};const tl=gsap.timeline({paused:true});${anim}tl.fromTo('#progress-fill',{scaleX:0},{scaleX:1,duration:${m.duration},ease:'none'},0);window.__timelines.main=tl;</script></body></html>`;
fs.writeFileSync(path.join(dir,'index.html'),html);
fs.writeFileSync(path.join(dir,'meta.json'),JSON.stringify({id:'portrait-workflow',name:m.title}));
fs.writeFileSync(path.join(dir,'hyperframes.json'),JSON.stringify({media:{autoProxy:true}}));
