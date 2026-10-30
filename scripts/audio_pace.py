"""Bounded, pitch-preserving scene-average pace calibration before alignment."""
import copy,json,re,shutil,subprocess
from pathlib import Path

def duration(file):
 return float(subprocess.check_output(['ffprobe','-v','error','-show_entries','format=duration','-of','csv=p=0',str(file)]))

def calibrate(scenes,entries,settings,report_path):
 target=float(settings['target_chars_per_second']);low=float(settings.get('min_tempo',.8));high=float(settings.get('max_tempo',1.2))
 if not (target>0 and .5<=low<=1<=high<=2):raise ValueError('Invalid bounded pace settings')
 report=[]
 for i,(scene,entry) in enumerate(zip(scenes,entries)):
  audio=Path(entry['output']);old=duration(audio);n=len(re.sub(r'\W','',scene['text']))
  if not n:continue
  requested=old*target/n;tempo=max(low,min(high,requested));temp=audio.with_name(audio.stem+'-paced.wav')
  subprocess.run(['ffmpeg','-v','error','-y','-i',str(audio),'-af',f'atempo={tempo:.9f}','-ar','48000','-ac','2',str(temp)],check=True)
  new=duration(temp);scaled=copy.deepcopy(scene.get('caption_cues',[]));previous=0
  for c in scaled:
   c['start']=max(previous,float(c['start'])/tempo);c['end']=min(new,float(c['end'])/tempo)
   if c['end']<=c['start']:raise ValueError('Pace calibration invalidated caption timing')
   previous=c['end']
  raw=audio.with_name(audio.stem+'-raw.wav');shutil.copy2(audio,raw);temp.replace(audio)
  if scaled:scene['caption_cues']=scaled
  report.append({'scene':i+1,'characters':n,'source_seconds':old,'output_seconds':new,'requested_tempo':requested,'applied_tempo':tempo,'limited':tempo!=requested,'source_chars_per_second':n/old,'output_chars_per_second':n/new,'raw_audio':str(raw)})
 Path(report_path).write_text(json.dumps(report,ensure_ascii=False,indent=2))
 return report
