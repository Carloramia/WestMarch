import os,sys,pathlib,json,wave
import numpy as np
sys.path.insert(0,str(pathlib.Path(os.environ['TEMP'])/'waijing-review-deps'))
os.environ['HF_HUB_DISABLE_XET']='1'
from faster_whisper import WhisperModel
P=pathlib.Path(__file__).resolve().parent
M=WhisperModel('base',device='cpu',compute_type='int8',cpu_threads=8,download_root=str(pathlib.Path(os.environ['TEMP'])/'waijing-whisper-models'))
for v in json.loads((P/'来源与覆盖.json').read_text(encoding='utf8')):
 out=P/(v['bvid']+'-transcript.json')
 if out.exists():continue
 with wave.open(str(P/(v['bvid']+'.wav')),'rb') as w:audio=np.frombuffer(w.readframes(w.getnframes()),dtype='<i2').astype(np.float32)/32768
 segs,info=M.transcribe(audio,language='zh',beam_size=5,vad_filter=True,condition_on_previous_text=False)
 rows=[]
 for s in segs:rows.append({'start':s.start,'end':s.end,'text':s.text,'avg_logprob':s.avg_logprob,'no_speech_prob':s.no_speech_prob})
 out.write_text(json.dumps({'source':v['source'],'audio_duration':info.duration,'language':info.language,'method':'faster-whisper base int8; machine transcript, verify against image subtitles; not a verbatim authoritative transcript','segments':rows},ensure_ascii=False,indent=2),encoding='utf8')
 print(v['bvid'],len(rows),'segments',flush=True)
