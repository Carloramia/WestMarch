"""Original staged 1-v-5 short. Screen-space projection preserves fine lines on zoom."""
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import pathlib, math, random, json, subprocess, sys, wave
import numpy as np
ROOT=pathlib.Path(__file__).resolve().parent.parent
W,H,FPS,DURATION=1080,1920,24,66
VIEW=(42,260,1038,1438)
C={'bg':'#0b1012','panel':'#10191c','line':'#3a494a','ink':'#d8dfd8','muted':'#879591','gold':'#d5ac60','red':'#b64d50','enemy':'#d4b491','cyan':'#8bb8ab'}
F={}
def font(n,b=False):
 if (n,b) not in F:F[n,b]=ImageFont.truetype('C:/Windows/Fonts/'+('msyhbd.ttc' if b else 'msyh.ttc'),n)
 return F[n,b]
def txt(d,p,s,n=26,c=None,b=False,a=None):d.text(p,s,font=font(n,b),fill=c or C['ink'],anchor=a)
def line(d,p,c,w=2):d.line(p,fill=c,width=w,joint='curve')
def box(d,r,fill=None,out=None,rad=5,w=1):d.rounded_rectangle(r,rad,fill=fill,outline=out,width=w)
def cl(x):return max(0,min(1,x))
def ez(x):x=cl(x);return x*x*(3-2*x)
def ler(a,b,t):return a+(b-a)*t
def path(t,k):
 if t<=k[0][0]:return k[0][1]
 for (s,p),(e,q) in zip(k,k[1:]):
  if t<=e:
   z=ez((t-s)/(e-s));return tuple(ler(p[i],q[i],z) for i in range(len(p)))
 return k[-1][1]
# All paths are deliberate choreography, not an autonomous combat model.
K=[(0,(500,740)),(6,(500,740)),(12,(456,690)),(17,(456,690)),(18,(456,665)),(21,(456,665)),(23,(465,686)),(26,(465,686)),(28,(474,700)),(29,(488,680)),(31,(500,676)),(33,(490,700)),(36,(575,650)),(39,(620,610)),(41,(620,590)),(43,(620,590)),(44,(665,565)),(45,(650,490)),(46,(555,455)),(48,(540,460)),(50,(540,490)),(52,(540,525)),(54,(540,510)),(58,(540,510)),(66,(540,510))]
P=[
 [(0,(430,460)),(10,(430,460)),(16,(456,615)),(18,(456,625)),(20,(450,602)),(22,(425,610))],
 [(0,(535,425)),(19,(535,425)),(24,(490,620)),(26,(490,643)),(27,(480,655)),(29,(510,635))],
 [(0,(665,450)),(14,(665,450)),(25,(665,660)),(31,(550,700)),(33,(535,700)),(36,(625,700)),(39,(620,665)),(41,(620,638)),(43,(642,655))],
 [(0,(545,250)),(44,(545,250)),(46,(540,400)),(48,(540,415)),(49,(525,415))],
 [(0,(665,300)),(40,(665,300)),(48,(620,435)),(49,(680,490)),(50,(665,590)),(51,(580,620)),(52,(540,585)),(53,(540,575)),(55,(555,590)),(66,(555,590))]
]
DOWN=[20.5,28.0,42,48.5,54]
NAMES=['短刀','手斧','木棍','轻弩','头目']
CAM=[(0,(535,520,.9)),(6,(535,520,.9)),(12,(500,620,1.05)),(14,(495,625,1.3)),(23,(495,625,1.3)),(25,(500,640,1.25)),(30,(570,660,1.05)),(34,(570,660,1.05)),(37,(585,625,1.1)),(44,(585,625,1.1)),(46,(540,450,1.4)),(49,(540,450,1.4)),(51,(545,530,1.35)),(55,(545,530,1.35)),(58,(535,520,.9))]
NARR=json.loads((ROOT/'源文件'/'旁白.json').read_text(encoding='utf8'))
WALLS=[((240,70),(240,1020)),((800,70),(800,1020)),((240,100),(445,100)),((635,100),(800,100))]
PILLARS=[(590,550),(315,250)]
ATTACKS=[(17.3,0,'knife'),(19.8,-1,'shield'),(20.45,-1,'pommel'),(26.5,1,'axe'),(27.7,-1,'sword'),(32,2,'club'),(41.5,-1,'shield'),(42,-1,'trip'),(48,-1,'shield'),(48.5,-1,'pommel'),(52,4,'knife'),(53.6,-1,'sword')]
PHASE=[(0,'遭遇','五名暴徒 · 一条出口'),(6,'选位','靠近车架，护住侧面'),(14,'接敌','盾面承箭，抢先破坏重心'),(24,'补位','避开斧锋，攻击收招空隙'),(30,'遇险','右翼绕后 · 左臂受击'),(35,'转位','脱离追击，利用石柱遮挡'),(40,'反击','盾推绊步，阻止重新包围'),(45,'贴近','趁装填接近弩手'),(50,'收束','控制刀手，迫使投降'),(58,'战后','四人失能 · 一人投降 · 骑士轻伤')]
RNG=random.Random(51)
STONES=[(x,y,RNG.randint(-3,3)) for y in range(120,1020,46) for x in range(250,800,55)]
def frame(t):
 im=Image.new('RGB',(W,H),C['bg']);d=ImageDraw.Draw(im)
 box(d,(16,18,1064,1900),'#0d1416','#354043',28,2)
 for x in (32,1048):
  for y in (246,1452):d.ellipse((x-4,y-4,x+4,y+4),outline='#75807b',width=1)
 txt(d,(48,66),'外 境  /  战 场 记 录',24,C['muted'])
 txt(d,(48,110),'街口 · 一对五',49,C['ink'],True)
 txt(d,(1034,80),'演示 002',20,C['gold'],a='ra')
 txt(d,(1034,125),'低阶红骑士',23,C['gold'],a='ra')
 phase=next((s for at,*s in reversed(PHASE) if t>=at),PHASE[0][1:])
 txt(d,(50,201),phase[0],24,C['gold'],True);txt(d,(170,201),phase[1],23,C['muted'])
 cx,cy,z=path(t,CAM);scale=z*1.37
 def p(q):return (540+(q[0]-cx)*scale,850+(q[1]-cy)*scale)
 def rect(r,fill,out=None,w=1):d.rectangle((*p(r[:2]),*p(r[2:])),fill=fill,outline=out,width=w)
 def li(a,b,c,w=2):line(d,[p(a),p(b)],c,w)
 def ellipse(q,r,fill=None,out=None,w=1):
  x,y=p(q);rr=r*scale;d.ellipse((x-rr,y-rr,x+rr,y+rr),fill=fill,outline=out,width=w)
 rect((0,0,1100,1200),'#111b1e')
 # Stable projected geometry: no bitmap map resizing.
 rect((240,100,800,1040),'#273033')
 for x,y,v in STONES:
  x0,y0=p((x,y));x1,y1=p((min(x+53,798),y+44))
  if y1>260 and y0<1438:d.rectangle((x0,y0,x1,y1),fill=(37+v,45+v,47+v))
 for a,b in WALLS:li(a,b,'#11191b',16);li(a,b,'#73817d',3);li((a[0]+5,a[1]),(b[0]+5,b[1]),'#344540',2)
 for y in range(170,1020,110):
  li((240,y),(260,y),'#8e9690',2);li((780,y),(800,y),'#8e9690',2)
 # Door at top; damaged cart occupies left lane and narrows simultaneous approach.
 li((445,100),(445,200),'#796b50',6);li((635,100),(635,200),'#796b50',6)
 rect((260,610,396,790),'#181d1d','#9b8c6b',2)
 for x in (280,310,340,370):li((x,620),(x,780),'#665d4a',2)
 for y in (638,758):li((248,y),(409,y),'#a18a62',4)
 for q in [(255,638),(402,638),(255,758),(402,758)]:ellipse(q,13,'#111719','#7f795f',2)
 for q in PILLARS:
  ellipse((q[0]+7,q[1]+8),34,'#151d1f');ellipse(q,31,'#313d3d','#98a29a',2);ellipse(q,23,None,'#61716a',1)
 for q in [(750,825),(745,875),(290,910)]:
  ellipse(q,24,'#292b25','#75735c',2);li((q[0]-20,q[1]),(q[0]+20,q[1]),'#575b49',2)
 for q,s in [((325,835),'废弃车架'),((645,520),'石柱'),((540,155),'封闭院门')]:txt(d,p(q),s,19,C['muted'],a='mm')
 if 7<t<13:
  for x in (415,510):li((x,595),(x,765),C['gold'],2)
  txt(d,p((475,805)),'护住侧面',24,C['gold'],True,a='mm')
 if 29<t<35:
  pts=[(665,470),(665,705),(555,705)];line(d,[p(q) for q in pts],C['enemy'],3)
  txt(d,p((660,775)),'右翼绕后',23,C['enemy'],True,a='mm')
 if 35<t<40:
  pts=[(525,720),(582,670),(620,610)];line(d,[p(q) for q in pts],C['gold'],2)
 # Bolt is physically stopped at shield, then remains on floor.
 if 13.6<t<14.2:
  v=cl((t-13.6)/.6);q=(ler(545,458,v),ler(250,665,v));li((q[0],q[1]-24),q,'#e3d7aa',3)
 if t>=14.2:li((443,672),(432,704),'#c3b992',2)
 if 35.3<t<35.9:
  v=cl((t-35.3)/.6);q=(ler(545,570,v),ler(250,522,v));li((q[0]-1,q[1]-24),q,'#e3d7aa',3)
 if t>=35.9:li((570,522),(573,501),'#c3b992',2)
 if 35.9<t<36.4:ellipse((570,522),9+25*cl((t-35.9)/.5),None,C['gold'],2)
 kp=path(t,K);ep=[path(t,k) for k in P]
 # Foot marks and movement trails are restrained.
 for keys,col in [(K,'#6f6654')]+[(k,'#555c55') for k in P]:
  a=path(max(0,t-.5),keys);b=path(t,keys)
  if math.dist(a,b)>5:li(a,b,col,2)
 def weapon(q,ang,kind,col):
  ux,uy=math.cos(ang),math.sin(ang);vx,vy=-uy,ux
  a=(q[0]+ux*15,q[1]+uy*15);b=(q[0]+ux*49,q[1]+uy*49)
  li(a,b,col,4 if kind=='club' else 2)
  if kind=='axe':li((b[0]+vx*12,b[1]+vy*12),(b[0]-vx*12,b[1]-vy*12),col,7)
  elif kind=='bow':li((a[0]+vx*21,a[1]+vy*21),(a[0]-vx*21,a[1]-vy*21),col,3)
  elif kind=='sword':li((a[0]+ux*8+vx*8,a[1]+uy*8+vy*8),(a[0]+ux*8-vx*8,a[1]+uy*8-vy*8),col,2)
 def actor(q,ang,idx,down=False):
  x,y=p(q)
  if down:
   col='#867b69';ellipse(q,22,'#23292a',col,1)
   li((q[0]-11,q[1]-11),(q[0]+11,q[1]+11),col,2);li((q[0]-11,q[1]+11),(q[0]+11,q[1]-11),col,2)
   weapon((q[0]+29,q[1]+14),.6,['knife','axe','club','bow','knife'][idx], '#827862')
   txt(d,(x,y-40*scale),f'{idx+1} · 失能',20,C['muted'],a='mm');return
  knight=idx==-1;col=C['gold'] if knight else C['enemy']
  ellipse((q[0]+3,q[1]+6),24,'#151c1e')
  if knight:
   ca=ang+math.pi
   d.polygon([p((q[0]+math.cos(ca)*30,q[1]+math.sin(ca)*30)),p((q[0]+math.cos(ca+.8)*17,q[1]+math.sin(ca+.8)*17)),p((q[0]+math.cos(ca-.8)*17,q[1]+math.sin(ca-.8)*17))],fill='#8c3d41')
  ellipse(q,19,'#283436' if knight else '#393733',col,2)
  tip=(q[0]+math.cos(ang)*27,q[1]+math.sin(ang)*27)
  d.polygon([p(tip),p((q[0]+math.cos(ang+.45)*18,q[1]+math.sin(ang+.45)*18)),p((q[0]+math.cos(ang-.45)*18,q[1]+math.sin(ang-.45)*18))],fill=col)
  if knight:
   # Shield and sword remain spatially readable; red cloak is friendly identity.
   sq=(q[0]+math.cos(ang-.65)*26,q[1]+math.sin(ang-.65)*26)
   sx,sy=p(sq);rr=12*scale
   d.polygon([(sx-rr,sy-rr),(sx+rr,sy-rr),(sx+rr*.8,sy+rr*.5),(sx,sy+rr*1.3),(sx-rr*.8,sy+rr*.5)],fill='#684047',outline=col,width=2)
   weapon(q,ang+.48,'sword','#e0ded0')
   # Helmet visor gives the knight an individual silhouette.
   li((q[0]-9,q[1]-5),(q[0]+9,q[1]-5),'#e2c17e',3)
   li((q[0],q[1]-13),(q[0],q[1]+8),'#e2c17e',2)
   if t>32:ellipse((q[0]-20,q[1]+9),4,'#cf8c75')
  elif idx==4 and t>=54:
   for dx in (-23,23):ellipse((q[0]+dx,q[1]-12),4,'#ded0b7')
  else:weapon(q,ang,['knife','axe','club','bow','knife'][idx],col)
  label='红骑士' if knight else f'{idx+1} {NAMES[idx]}'
  txt(d,(x,y+(43 if knight else -39)*scale),label,23 if knight else 20,col,knight,a='mm')
  if idx==4 and t>=54:txt(d,(x,y+39*scale),'投降',22,C['cyan'],True,a='mm')
 # Face nearest live threat, turn visibly before engagement.
 live=[i for i in range(5) if t<DOWN[i]]
 target=min(live,key=lambda i:math.dist(kp,ep[i])) if live else 4
 ka=math.atan2(ep[target][1]-kp[1],ep[target][0]-kp[0])
 for i,q in enumerate(ep):actor(q,math.atan2(kp[1]-q[1],kp[0]-q[0]),i,t>=DOWN[i] and i<4)
 actor(kp,ka,-1)
 # Animated sweeps, shield shove, push feedback. Timing is shared with effects audio.
 for at,who,kind in ATTACKS:
  dt=t-at
  if -.28<dt<.42:
   q=kp if who==-1 else ep[who];a=ka if who==-1 else math.atan2(kp[1]-q[1],kp[0]-q[0])
   v=cl((dt+.28)/.55);col=C['gold'] if who==-1 else '#dfbaa0'
   if kind in ('shield','pommel','trip'):
    pp=(q[0]+math.cos(a)*31,q[1]+math.sin(a)*31);ellipse(pp,8+16*v,None,col,3)
   else:
    pts=[p((q[0]+math.cos(a-1+j*.12+v*.5)*53,q[1]+math.sin(a-1+j*.12+v*.5)*53)) for j in range(15)]
    line(d,pts,col,4)
   if -.04<dt<.15:
    iq=(q[0]+math.cos(a)*37,q[1]+math.sin(a)*37)
    for j in range(7):
     aa=j*2.399;li((iq[0]+math.cos(aa)*7,iq[1]+math.sin(aa)*7),(iq[0]+math.cos(aa)*23,iq[1]+math.sin(aa)*23),'#f4dca4',2)
 if 14.1<t<14.6:
  ellipse((456,668),23+cl((t-14.1)/.5)*30,None,C['gold'],2)
 if 32<t<34.5:txt(d,p((520,760)),'左臂受击',25,'#df9c82',True,a='mm')
 if t>=54:weapon((580,580),1.4,'knife','#aaa18a')
 # Hide projected geometry outside the map viewport and draw instrument framing.
 d.rectangle((0,0,W,259),fill=C['bg']);d.rectangle((0,1439,W,H),fill=C['bg'])
 # Header redraw after crop.
 txt(d,(48,55),'外 境  /  战 场 记 录',24,C['muted']);txt(d,(48,100),'街口 · 一对五',49,C['ink'],True)
 txt(d,(1034,62),'演示 002',20,C['gold'],a='ra');txt(d,(1034,111),'低阶红骑士',23,C['gold'],a='ra')
 txt(d,(50,201),phase[0],24,C['gold'],True);txt(d,(170,201),phase[1],23,C['muted'])
 d.rectangle(VIEW,outline='#69756c',width=2)
 for x in (52,1028):
  for y,sgn in [(270,1),(1428,-1)]:line(d,[(x+18*(1 if x<100 else -1),y),(x,y),(x,y+18*sgn)],C['gold'],2)
 # Sidebar masks keep near-camera geometry inside frame.
 d.rectangle((0,260,41,1438),fill=C['bg']);d.rectangle((1039,260,1080,1438),fill=C['bg'])
 txt(d,(60,280),f'REC  {int(t)//60:02}:{int(t)%60:02}',18,C['muted'])
 count=sum(t>=v for v in DOWN)
 box(d,(42,1466,1038,1545),C['panel'],C['line'],5)
 txt(d,(66,1487),'接敌状态',22,C['muted'])
 for i in range(5):
  x=265+i*143;col=C['muted'] if t>=DOWN[i] else C['enemy']
  d.ellipse((x,1490,x+16,1506),fill=col)
  txt(d,(x+25,1486),str(i+1)+(' 退' if i==4 and t>=54 else ' 失能' if t>=DOWN[i] else ' 接敌'),19,col)
 box(d,(42,1570,1038,1754),'#10191b',None,7)
 for s,e,words in NARR:
  if s<=t<e:
   parts=wrap(words)
   for j,ss in enumerate(parts):txt(d,(540,1610+j*49),ss,31,C['ink'],True,a='mt')
 txt(d,(48,1790),'一人 / 剑与盾',23,C['gold']);txt(d,(1035,1790),'左臂受击' if t>32 else '已接敌' if t>14 else '尚未接触',23,'#d09277' if t>32 else C['muted'],a='ra')
 line(d,[(45,1845),(1035,1845)],C['line'],2);line(d,[(45,1845),(45+990*t/DURATION,1845)],C['gold'],3)
 txt(d,(45,1870),'原创演示剧情 · 预编排动画 · 非数值模拟',19,C['muted'])
 if 0<t<5.8:
  box(d,(150,1190,930,1370),'#0e171a','#706549',4,2)
  txt(d,(540,1220),'他们有五个人。',42,C['ink'],True,a='mt');txt(d,(540,1286),'但不能让他们一起出手。',29,C['gold'],True,a='mt')
 if t>=58:
  ov=Image.new('RGBA',(W,H));od=ImageDraw.Draw(ov)
  box(od,(135,555,945,1175),(10,18,21,241),'#a48c5b',8,2)
  txt(od,(540,602),'交 战 结 束',48,C['gold'],True,a='mt')
  for yy,l,r in [(728,'暴徒 01—04','失去战斗能力'),(815,'暴徒 05','弃械投降'),(902,'红骑士','左臂受伤 · 存活')]:
   txt(od,(190,yy),l,28,C['muted']);txt(od,(880,yy),r,28,C['ink'],True,a='ra')
  line(od,[(190,1000),(890,1000)],C['line'],2)
  txt(od,(540,1043),'控制接敌面，逐个破坏协同。',31,C['gold'],True,a='mt')
  im=Image.alpha_composite(im.convert('RGBA'),ov).convert('RGB')
 if t>65:im=Image.blend(im,Image.new('RGB',im.size,C['bg']),ez(t-65))
 return im
def wrap(s):
 if len(s)<=24:return [s]
 cuts=[i+1 for i,c in enumerate(s) if c in '，。' and 7<i<len(s)-7]
 k=min(cuts or [len(s)//2],key=lambda x:abs(x-len(s)/2));return [s[:k],s[k:]]
def audio():
 sr=48000;sig=np.zeros((DURATION*sr,2),np.float32);rng=np.random.default_rng(8)
 def add(at,a,pan=0):
  i=int(at*sr);n=min(len(a),len(sig)-i)
  if n>0:
   sig[i:i+n,0]+=a[:n]*math.sqrt((1-pan)/2);sig[i:i+n,1]+=a[:n]*math.sqrt((1+pan)/2)
 tt=np.arange(sr*DURATION)/sr
 bed=(np.sin(tt*math.tau*55)*.004+np.sin(tt*math.tau*82.4)*.003)*(1+.15*np.sin(tt*.8))
 sig[:,0]=bed;sig[:,1]=bed
 def hit(at,metal=False,vol=.12):
  tt=np.arange(int(sr*.45))/sr
  a=(rng.normal(0,.3,len(tt))+np.sin(tt*math.tau*85))*np.exp(-tt*25)*vol
  if metal:a+=(np.sin(tt*math.tau*690)+.3*np.sin(tt*math.tau*1810))*np.exp(-tt*14)*vol*.5
  add(at,a)
 for at,who,kind in ATTACKS:hit(at,kind in ('knife','sword','axe'),.12 if who==-1 else .085)
 hit(14.15,True,.15)
 hit(35.9,False,.08)
 for at in np.arange(6,12,.6):hit(at,False,.015)
 for at in np.arange(35,39,.45):hit(at,False,.02)
 for at in np.arange(45,48,.38):hit(at,False,.025)
 log=[]
 for i,(s,e,words) in enumerate(NARR):
  src=ROOT/'音频'/f'neural_{i:02d}.mp3'
  dur=float(json.loads(subprocess.check_output(['ffprobe','-v','quiet','-show_format','-of','json',str(src)]))['format']['duration'])
  tempo=max(1,dur/(e-s-.12));log.append({'line':i,'source_duration':dur,'tempo':tempo})
  raw=subprocess.check_output(['ffmpeg','-v','error','-i',str(src),'-af',f'atempo={tempo:.6f},highpass=f=85,loudnorm=I=-17:TP=-2:LRA=7','-f','f32le','-ar',str(sr),'-ac','1','pipe:1'])
  add(s,np.frombuffer(raw,dtype='<f4')*1.13)
 sig*=np.minimum(1,tt/.25)[:,None]*np.minimum(1,(DURATION-tt)/1)[:,None]
 with wave.open(str(ROOT/'音频'/'完整混音.wav'),'wb') as w:
  w.setnchannels(2);w.setsampwidth(2);w.setframerate(sr);w.writeframes((np.clip(sig,-1,1)*32767).astype('<i2').tobytes())
 (ROOT/'音频'/'旁白适配.json').write_text(json.dumps(log,indent=2),encoding='utf8')
def main():
 if '--stills' in sys.argv:
  for t in [3,11,18,21,27,32.2,38,42,48.2,53.6,60]:frame(t).save(ROOT/f'预览_{t:04.1f}.jpg',quality=94)
  return
 audio()
 p=subprocess.Popen(['ffmpeg','-y','-v','warning','-f','rawvideo','-pixel_format','rgb24','-video_size',f'{W}x{H}','-framerate',str(FPS),'-i','pipe:0','-i',str(ROOT/'音频'/'完整混音.wav'),'-c:v','libx264','-preset','fast','-crf','18','-pix_fmt','yuv420p','-c:a','aac','-b:a','192k','-movflags','+faststart','-shortest',str(ROOT/'外境_红骑士街口_测试.mp4')],stdin=subprocess.PIPE)
 for i in range(FPS*DURATION):
  p.stdin.write(frame(i/FPS).tobytes())
  if i%(FPS*5)==0:print(f'render {i//FPS}/{DURATION}',flush=True)
 p.stdin.close()
 if p.wait():raise RuntimeError('Encoding failed')
 frame(18).save(ROOT/'封面.jpg',quality=95)
 print('DONE',flush=True)
if __name__=='__main__':main()
