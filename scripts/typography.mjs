import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
// Preserve punctuation that carries numeric meaning; spoken copy is never modified.
export const cleanHeading=value=>String(value??'').replace(/\p{P}/gu,(mark,i,text)=>{const before=text[i-1]||'',after=text[i+mark.length]||'';return (/\d/.test(before)&&/\d/.test(after))||(mark==='%'&&/\d/.test(before))||((mark==='-'||mark==='−')&&/\d/.test(after))?mark:''}).trim();
const filename='SourceHanSansSC-Bold.otf';
const face=base=>`@font-face{font-family:WorkflowHeading;src:url('${base}/${filename}') format('opentype');font-weight:700;font-style:normal;font-display:block}`;
export const headingFontCSS=face('media/fonts');
export const sceneHeadingFontCSS=face('../media/fonts');
const bodyFace=base=>`@font-face{font-family:WorkflowCN;src:url('${base}/SourceHanSansSC-Regular.otf') format('opentype');font-weight:400;font-display:block}@font-face{font-family:WorkflowCN;src:url('${base}/SourceHanSansSC-Bold.otf') format('opentype');font-weight:700;font-display:block}`;
export const bodyFontCSS=bodyFace('media/fonts');
export const sceneBodyFontCSS=bodyFace('../media/fonts');
export const headingFamily='WorkflowHeading,WorkflowCN,sans-serif';
export function prepareTypography(dir){
 for(const name of ['SourceHanSansSC-Bold.otf','SourceHanSansSC-Regular.otf']){
  const source=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'../assets/fonts',name);
  const target=path.join(dir,'media/fonts',name);fs.mkdirSync(path.dirname(target),{recursive:true});
  if(!fs.existsSync(target))fs.copyFileSync(source,target);
 }
}
