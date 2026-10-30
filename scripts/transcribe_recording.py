"""Transcribe uploaded speech locally; retain timestamps for the Agent's scene plan."""
import argparse,json,subprocess
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--audio',required=True);p.add_argument('--output',required=True);a=p.parse_args()
source=Path(a.audio).expanduser().resolve()
if not source.is_file():raise ValueError('录音不存在')
import whisper
from opencc import OpenCC
cc=OpenCC('t2s');model=whisper.load_model('small',device='cpu')
result=model.transcribe(str(source),language='zh',word_timestamps=True,fp16=False)
probe=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_format','-of','json',str(source)],text=True,encoding='utf-8'))
data={'audio':str(source),'duration':float(probe['format']['duration']),'text':cc.convert(result['text']),
      'segments':[{'start':s['start'],'end':s['end'],'text':cc.convert(s['text']),
                   'words':[dict(w,word=cc.convert(w['word'])) for w in s.get('words',[])]} for s in result['segments']],
      'needs_review':True,'note':'自动转写候选；按实际说话内容核对，不能把润色后的新稿当原录音。'}
target=Path(a.output);target.parent.mkdir(parents=True,exist_ok=True);target.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
print('TRANSCRIPT: '+str(target))
