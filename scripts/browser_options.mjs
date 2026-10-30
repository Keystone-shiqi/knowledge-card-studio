import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
export function browserOptions(){
 const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
 const runtime=path.join(root,'.runtime/runtime.json');
 const stored=fs.existsSync(runtime)?JSON.parse(fs.readFileSync(runtime,'utf8')).browser:null;
 const candidate=process.env.WORKFLOW_CHROME || (stored&&fs.existsSync(stored)?stored:null);
 if(candidate){if(!fs.existsSync(candidate))throw Error('Browser not found: '+candidate);return {executablePath:candidate};}
 const mac='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';
 return process.platform==='darwin'&&fs.existsSync(mac)?{executablePath:mac}:{};
}
