"""Read-only reference preparation; no creative replica code is modified."""
from PIL import Image,ImageDraw,ImageFont
from pathlib import Path
import json,subprocess,math
P=Path(__file__).resolve().parent
A=json.loads((P/'来源与覆盖.json').read_text(encoding='utf8'))
font=ImageFont.truetype('C:/Windows/Fonts/consola.ttf',19)
for n,v in enumerate(A,1):
 vid=v['bvid'];f=P/(vid+'.mp4');out=P/vid;out.mkdir(exist_ok=True)
 subprocess.run(['ffmpeg','-v','error','-i',str(f),'-vf','fps=1','-q:v','3',str(out/'%04d.jpg'),'-y'],check=True)
 files=sorted(out.glob('[0-9][0-9][0-9][0-9].jpg'))
 # Each panel is the complete uncropped frame. Sixteen consecutive seconds per page.
 for start in range(0,len(files),16):
  sheet=Image.new('RGB',(1080,2016),'#151b23');d=ImageDraw.Draw(sheet)
  for i,fn in enumerate(files[start:start+16]):
   im=Image.open(fn).resize((270,480),Image.Resampling.LANCZOS)
   x=i%4*270;y=i//4*504;sheet.paste(im,(x,y));d.text((x+7,y+481),f'{start+i:03d}s',font=font,fill='white')
  sheet.save(out/f'review-{start:03d}.jpg',quality=94)
 subprocess.run(['ffmpeg','-v','error','-ss',str(max(0,v['duration']-.12)),'-i',str(f),'-frames:v','1','-update','1',str(out/'end.jpg'),'-y'],check=True)
 print(n,vid,'seconds',len(files),'pages',math.ceil(len(files)/16),flush=True)
