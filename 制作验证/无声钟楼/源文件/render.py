"""Restrained tactical film: geometric stage, occluded light, motivated camera and sound."""
from PIL import Image,ImageDraw,ImageFont,ImageFilter
import numpy as np
import pathlib,json,math,random,subprocess,wave,sys
ROOT=pathlib.Path(__file__).resolve().parent.parent
W,H,BW,BH=1080,1920,920,1040
FPS,DURATION=30,58
V=(40,265,1040,1525)
C={'bg':'#090e14','panel':'#101922','line':'#34434d','muted':'#7d919d','text':'#d8e3e7','gold':'#edba59','cyan':'#77c9c8','red':'#f0787a','blue':'#9bacd2'}
F={}
def font(n,b=False,mono=False):
 k=(n,b,mono)
 if k not in F:F[k]=ImageFont.truetype('C:/Windows/Fonts/'+('consola.ttf' if mono else 'msyhbd.ttc' if b else 'msyh.ttc'),n)
 return F[k]
def text(d,p,s,n=22,c=None,b=False,a=None,mono=False):d.text(p,s,font=font(n,b,mono),fill=c or C['text'],anchor=a)
def ln(d,p,c,w=2):d.line(p,fill=c,width=w,joint='curve')
def box(d,r,c=None,o=None,rad=4,w=1):d.rounded_rectangle(r,rad,fill=c,outline=o,width=w)
def clamp(t):return max(0,min(1,t))
def ease(t):t=clamp(t);return t*t*(3-2*t)
def mix(a,b,t):return a+(b-a)*t
def route(t,k):
 if t<=k[0][0]:return k[0][1]
 for (s,p),(e,q) in zip(k,k[1:]):
  if t<=e:
   v=ease((t-s)/(e-s));return (mix(p[0],q[0],v),mix(p[1],q[1],v))
 return k[-1][1]
ROOMS=[(270,140,650,750),(65,330,270,590),(650,235,850,505),(410,750,510,1040)]
SEGS=[((270,140),(650,140)),((270,140),(270,416)),((270,500),(270,750)),((650,140),(650,335)),((650,419),(650,750)),((270,750),(410,750)),((510,750),(650,750)),((65,330),(270,330)),((65,330),(65,590)),((65,590),(270,590)),((270,330),(270,416)),((270,500),(270,590)),((650,235),(850,235)),((850,235),(850,505)),((650,505),(850,505)),((650,235),(650,335)),((650,419),(650,505)),((410,750),(410,1040)),((510,750),(510,1040))]
PILLARS=[(x,y) for x in (315,605) for y in (230,355,590,690)]
for x,y in PILLARS:
 pts=[(x+16*math.cos(j*math.pi/4),y+16*math.sin(j*math.pi/4)) for j in range(8)]
 SEGS.extend(zip(pts,pts[1:]+pts[:1]))
SEG=np.array(SEGS,float)

def make_map():
 im=Image.new('RGB',(BW,BH),'#0b1119');d=ImageDraw.Draw(im);rng=random.Random(32)
 for x in range(0,BW,40):ln(d,[(x,0),(x,BH)],'#101923',1)
 for y in range(0,BH,40):ln(d,[(0,y),(BW,y)],'#101923',1)
 for x0,y0,x1,y1 in ROOMS:
  d.rectangle((x0,y0,x1,y1),fill='#26313c')
  for y in range(y0,y1,46):
   for x in range(x0,x1,49):
    v=rng.randrange(29,37);d.rectangle((x+1,y+1,min(x+48,x1),min(y+45,y1)),fill=(v,v+10,v+20))
  for _ in range(12):
   x=rng.randrange(x0+9,x1-9);y=rng.randrange(y0+9,y1-9)
   ln(d,[(x,y),(x+7,y+3),(x+13,y+1)],'#3b4650',1)
 for p,q in SEGS[:19]:ln(d,[p,q],'#111922',12);ln(d,[p,q],'#8996a0',3)
 for x,y in PILLARS:
  d.ellipse((x-17,y-17,x+17,y+17),fill='#14202a',outline='#73828c',width=2)
  d.ellipse((x-11,y-11,x+11,y+11),outline='#43535f',width=1)
 d.rectangle((440,555,480,738),fill='#3b3037')
 for y in (620,665,705):ln(d,[(441,y),(477,y+3)],'#51404a')
 for x in (360,525):
  for y in (220,270,675):box(d,(x,y,x+40,y+12),'#403d37','#636055',1)
 d.ellipse((420,160,500,240),fill='#252b2e',outline='#7a725a',width=2)
 d.ellipse((435,175,485,225),outline='#a69564',width=2)
 for a in np.arange(0,2*math.pi,math.pi/4):ln(d,[(460+25*math.cos(a),200+25*math.sin(a)),(460+40*math.cos(a),200+40*math.sin(a))],'#77705c',2)
 for r in [(83,350,112,390),(83,545,161,570),(802,260,829,320)]:box(d,r,'#353532','#65614f',2)
 text(d,(460,110),'主钟厅',20,C['muted'],a='mm')
 text(d,(167,307),'储物间',17,C['muted'],a='mm')
 text(d,(750,213),'巡灯室',17,C['muted'],a='mm')
 text(d,(460,1000),'撤离 ↓',19,C['cyan'],True,a='mm')
 return im
MAP=make_map()
MAPDARK=Image.blend(Image.new('RGB',MAP.size,'#080d13'),MAP,.39)
A=[(0,(455,535)),(2.6,(455,518)),(3,(455,490)),(5,(455,535)),(8,(455,535)),(10,(455,630)),(18,(455,630)),(23,(475,610)),(29,(475,610)),(33,(600,455)),(37,(580,560)),(41,(480,710)),(45,(455,735)),(47,(455,735)),(49,(455,825)),(51,(455,960)),(52.5,(455,1080))]
B=[(0,(390,620)),(10,(390,570)),(11,(390,550)),(17,(390,550)),(24,(390,550)),(29,(430,530)),(32,(650,380)),(34,(720,350)),(36,(720,350)),(37.5,(690,380)),(38.5,(620,400)),(41,(480,600)),(45,(480,855)),(48,(480,1050))]
U=[(0,(520,620)),(17,(520,620)),(21,(310,480)),(24,(305,480)),(27,(305,480)),(29,(310,500)),(30,(350,535)),(34,(470,700)),(38,(435,850)),(41,(435,1045))]
E=[(0,(460,475)),(8,(460,475)),(10,(460,550)),(13,(365,490)),(16,(365,490)),(20,(415,440)),(23,(415,440)),(25,(320,460)),(27,(235,460)),(28,(155,455)),(36,(155,455)),(38,(220,455)),(40,(250,455)),(44.7,(250,455)),(45.3,(300,458)),(47,(350,510)),(48.3,(350,510)),(51,(460,325)),(58,(460,325))]
CAP=[(0,(780,350)),(34,(780,350)),(36.2,(780,350)),(37.7,(740,380)),(39.8,(625,400)),(42.5,(460,640)),(46,(460,880)),(49,(460,1050))]
CAM=[(0,(460,520,1.05)),(1,(460,520,1.05)),(2.0,(455,495,1.75)),(7,(455,495,1.75)),(8.4,(460,570,1.16)),(10.8,(390,530,1.7)),(15.8,(390,530,1.7)),(17.4,(460,520,1.05)),(21,(320,480,1.5)),(28,(255,460,1.6)),(29.4,(270,460,1.8)),(30.8,(460,470,1.05)),(34.7,(720,365,1.8)),(35.7,(720,365,1.8)),(36.5,(180,450,2.0)),(39,(260,458,1.85)),(44.8,(270,458,1.85)),(45.7,(455,650,1.2)),(47,(455,650,1.2)),(48,(460,430,1.3)),(49.5,(460,600,1.03)),(52,(460,600,1.03))]
def camera(t):
 for (s,p),(e,q) in zip(CAM,CAM[1:]):
  if t<=e:
   v=ease((t-s)/(e-s));return tuple(mix(p[i],q[i],v) for i in range(3))
 return CAM[-1][1]

def visibility(p,angle,radius=280,cone=1.5,closed=False):
 seg=SEG if not closed else np.concatenate((SEG,np.array([[(270,416),(270,500)]])))
 dirs=np.column_stack((np.cos(np.linspace(angle-cone/2,angle+cone/2,101)),np.sin(np.linspace(angle-cone/2,angle+cone/2,101))))
 s=seg[:,1]-seg[:,0];v=seg[:,0]-np.array(p)
 den=dirs[:,0,None]*s[None,:,1]-dirs[:,1,None]*s[None,:,0]
 den=np.where(abs(den)<1e-8,1e-8,den)
 tt=(v[None,:,0]*s[None,:,1]-v[None,:,1]*s[None,:,0])/den
 uu=(v[None,:,0]*dirs[:,None,1]-v[None,:,1]*dirs[:,None,0])/den
 distances=np.min(np.where((tt>0)&(uu>=0)&(uu<=1),tt,radius),axis=1).clip(0,radius)
 pts=np.array(p)+dirs*distances[:,None]
 return [tuple(p)]+[tuple(x) for x in pts]+[tuple(p)]
def heading(t,keys,default=-math.pi/2):
 p=route(t,keys);q=route(t+.2,keys);dx,dy=q[0]-p[0],q[1]-p[1]
 return math.atan2(dy,dx) if math.hypot(dx,dy)>1 else default
def ring(d,p,t,col,rad=100,n=3):
 rgb=tuple(int(col[j:j+2],16) for j in (1,3,5))
 for j in range(n):
  v=(t+j/n)%1;r=8+v*rad
  d.ellipse((p[0]-r,p[1]-r,p[0]+r,p[1]+r),outline=(*rgb,int(155*(1-v))),width=2)
def actor(d,p,label,col,ang,enemy=False,quiet=False):
 x,y=p;r=18 if not enemy else 24
 d.ellipse((x-r-4,y-r-4,x+r+4,y+r+4),outline=col,width=1)
 d.ellipse((x-r,y-r,x+r,y+r),fill='#0c1721',outline=col,width=2)
 if enemy:
  d.polygon([(x,y-14),(x+11,y-7),(x+8,y+12),(x,y+17),(x-8,y+12),(x-11,y-7)],outline=col,fill='#452c35')
  ln(d,[(x-7,y-5),(x+7,y-5)],'#ffc4c1',3)
 else:text(d,(x,y),label,17,col,True,a='mm')
 tip=(x+math.cos(ang)*(r+11),y+math.sin(ang)*(r+11))
 d.polygon([tip,(x+math.cos(ang+.25)*(r+2),y+math.sin(ang+.25)*(r+2)),(x+math.cos(ang-.25)*(r+2),y+math.sin(ang-.25)*(r+2))],fill=col)
 if quiet:ln(d,[(x-10,y+r+9),(x+10,y+r+9)],col,2)
def speech(d,p,s,col):
 x,y=p;w=d.textlength(s,font=font(18))+18
 box(d,(x-w/2,y-60,x+w/2,y-30),'#10202b',col,3)
 text(d,(x,y-45),s,18,col,a='mm')

def shot_world(t):
 a,b,u,e=[route(t,k) for k in (A,B,U,E)];cp=route(t,CAP)
 m=Image.new('L',(BW,BH),0);md=ImageDraw.Draw(m)
 for keys,p in [(A,a),(B,b),(U,u)]:
  if p[1]>1030:continue
  h=heading(t,keys)
  md.polygon(visibility(p,h,290,1.2,28.6<t<44.7),fill=190)
  md.polygon(visibility(p,h,65,math.tau,28.6<t<44.7),fill=225)
 if cp[1]<1030:md.polygon(visibility(cp,0,110,math.tau,28.6<t<44.7),fill=150)
 im=Image.composite(MAP,MAPDARK,m.filter(ImageFilter.GaussianBlur(.8))).convert('RGBA')
 ov=Image.new('RGBA',im.size);d=ImageDraw.Draw(ov)
 if 10.7<t<13.8:
  ring(d,(365,490),t-10.7,C['cyan'],105)
  v=ease((t-10.6)/.6);x=mix(390,365,v);y=mix(550,490,v)-math.sin(v*math.pi)*30
  d.polygon([(x-4,y-3),(x+6,y-4),(x+4,y+4),(x-4,y+3)],fill='#b3bec0')
 if 16.5<t<18.4:
  for i in range(0,110,16):ln(d,[(275-i,460),(268-i,459)],C['gold'],2)
  d.polygon([(150,450),(163,442),(162,458)],fill=C['gold']);box(d,(80,348,252,571),None,'#aa8c58',3,1)
 if 21<t<23:
  v=ease((t-21)/2);x=mix(305,145,v);y=mix(480,450,v)-math.sin(math.pi*v)*55
  ln(d,[(x-12,y+7),(x,y)],'#8c7c53',1);box(d,(x-8,y-6,x+8,y+6),'#23313b',C['gold'],2)
 if 23<=t<52:
  if t<36.3:ring(d,(145,450),t-23,C['gold'],90)
  box(d,(134,441,156,459),'#16212a',C['gold'] if t<36.3 else C['muted'],2,2)
  if 36.3<t<38.5:ln(d,[(137,444),(153,457)],C['red'],2);text(d,(145,425),'停止',16,C['red'],a='mm')
 if t<28.6:ln(d,[(270,416),(220,419)],'#7c817a',4)
 elif t<44.7:
  ln(d,[(270,418),(270,498)],'#a99c78',6);ln(d,[(260,435),(280,480)],C['gold'],5)
  if t>38:
   damage=clamp((t-38)/6.7);ln(d,[(270,427),(275,444),(266,461),(274,482)],C['red'],1+int(damage*3))
   if (t-38)%1.1<.18:ring(d,(268,458),t,C['red'],55,2)
 else:
  for j in range(8):
   v=clamp((t-44.7)/.5);an=j*2.1;x=270+math.cos(an)*(20+15*j%34)*v;y=458+math.sin(an)*55*v
   ln(d,[(x-8,y-6),(x+5,y+7)],'#b69a6c',3)
 shattered=2.9<t<6.4
 if shattered:
  v=clamp((t-2.9)/.55)
  if t>5.3:v=1-ease((t-5.3)/1.1)
  for j in range(18):
   an=j*2.399;dist=(32+j%5*9)*v;xx=e[0]+math.cos(an)*dist;yy=e[1]+math.sin(an)*dist
   d.polygon([(xx-5,yy-5),(xx+7,yy-1),(xx+2,yy+7)],fill='#b58788',outline='#e2bec0')
  if t>5.2:ring(d,e,t-5.2,C['red'],75)
 else:
  if 6.4<t<7.3:ring(d,e,t-6.4,C['red'],80)
  eh=heading(t,E,math.pi/2)
  if 10.8<t<16:eh=math.atan2(490-e[1],365-e[0])
  if 23<t<28:eh=math.atan2(450-e[1],145-e[0])
  if 48.1<t<51:eh=math.atan2(325-e[1],460-e[0])
  d.polygon(visibility(e,eh,135,.9,28.6<t<44.7),fill=(240,100,110,22));actor(d,e,'甲',C['red'],eh,True)
 for keys,p,s,c in [(A,a,'砾',C['gold']),(B,b,'线',C['cyan']),(U,u,'钉',C['blue'])]:
  if p[1]>1040:continue
  last=route(max(0,t-.35),keys)
  if math.dist(last,p)>3:ln(d,[last,p],c,2)
  actor(d,p,s,c,heading(t,keys),quiet=14<t<47)
 if cp[1]<1040:
  actor(d,cp,'灯','#d1d7d0',math.pi/2)
  if t<35.2:ln(d,[(cp[0]-13,cp[1]+25),(cp[0]+13,cp[1]+25)],'#c48b78',2)
  if 34.7<t<35.7:ring(d,cp,t-34.7,C['cyan'],40,2)
 if 2.5<t<3.25:
  v=clamp((t-2.5)/.5);x,y=e;d.arc((x-58,y-58,x+58,y+58),int(50+v*110),int(135+v*110),fill='#fff2c5',width=5)
  if 2.85<t<3.02:
   for j in range(12):
    an=j*.8;r=15+(t-2.85)*300;ln(d,[(x+math.cos(an)*r,y+math.sin(an)*r),(x+math.cos(an)*(r+15),y+math.sin(an)*(r+15))],C['gold'],2)
 if 47<t<48.1:
  v=clamp((t-47)/1.1);x=mix(455,460,v);y=mix(735,325,v)
  ln(d,[(x-7,y+30),(x+3,y-9)],C['gold'],4);ln(d,[(x,y+35),(x,y+70)],'#766a4c',2)
 if 48.1<t<52:ring(d,(460,325),t-48.1,C['gold'],105);ln(d,[(453,334),(467,315)],'#b1a182',4)
 if 1<t<2.4:speech(d,a,'我来。',C['gold'])
 if 14.8<t<17:speech(d,b,'别动。',C['cyan'])
 if 26.6<t<28.3:speech(d,u,'再走两步。',C['blue'])
 if 44.7<t<46.5:speech(d,a,'先走！',C['gold'])
 return Image.alpha_composite(im,ov).convert('RGB')

def phase(t):
 for end,s in [(7,'正面交战'),(11,'撤步'),(18,'声音线索'),(23,'换个办法'),(28.6,'诱敌'),(35.7,'营救'),(38.2,'声源中断'),(44.7,'门闩受损'),(48.1,'掩护撤离'),(53,'第二声源'),(99,'全员撤离')]:
  if t<end:return s
def render(t):
 world=shot_world(t);cx,cy,zoom=camera(t);vw,vh=V[2]-V[0],V[3]-V[1];scale=1.10*zoom
 vx=cx-vw/(2*scale);vy=cy-vh/(2*scale);shake=0
 if 2.86<t<3.08 or (38<t<44.7 and (t-38)%1.1<.11) or 44.7<t<45.02:shake=3*math.sin(t*110)
 view=world.transform((vw,vh),Image.Transform.AFFINE,(1/scale,0,vx+shake,0,1/scale,vy),Image.Resampling.BICUBIC,fillcolor='#0b1119')
 im=Image.new('RGB',(W,H),C['bg']);im.paste(view,(V[0],V[1]));d=ImageDraw.Draw(im)
 text(d,(42,45),'外 境',35,C['gold'],True);text(d,(1038,57),'探索记录 / 001',21,C['muted'],a='ra')
 text(d,(42,108),'无声钟楼',51,C['text'],True);text(d,(42,187),'目标  带回巡灯人',25,C['gold'])
 text(d,(1036,193),phase(t),24,C['red'] if 35.7<t<46 else C['muted'],a='ra');ln(d,[(40,238),(1040,238)],C['line'])
 for x,y,sx,sy in [(40,265,1,1),(1040,265,-1,1),(40,1525,1,-1),(1040,1525,-1,-1)]:ln(d,[(x,y+sy*20),(x,y),(x+sx*20,y)],'#8b7957',2)
 text(d,(58,282),'N ↑',19,C['muted'],mono=True);d.ellipse((929,287,937,295),fill=C['red']);text(d,(1020,282),f'{int(t)//60:02}:{int(t)%60:02}',18,C['muted'],a='ra',mono=True)
 if zoom>1.25:
  mini=MAP.resize((184,208),Image.Resampling.BILINEAR);mini=Image.blend(Image.new('RGB',mini.size,'#080e14'),mini,.7)
  im.paste(mini,(838,1295));d=ImageDraw.Draw(im);d.rectangle((838,1295,1022,1503),outline=C['line'],width=1)
  for keys,c in [(A,C['gold']),(B,C['cyan']),(U,C['blue']),(E,C['red'])]:
   p=route(t,keys);x=838+p[0]*.2;y=1295+p[1]*.2;d.ellipse((x-3,y-3,x+3,y+3),fill=c)
  x0=max(838,838+vx*.2);y0=max(1295,1295+vy*.2);x1=min(1022,838+(vx+vw/scale)*.2);y1=min(1503,1295+(vy+vh/scale)*.2)
  if x1>x0 and y1>y0:d.rectangle((x0,y0,x1,y1),outline=C['gold'],width=1)
 for i,(s,role,c,keys) in enumerate([('砾','前卫',C['gold'],A),('线','斥候',C['cyan'],B),('钉','匠人',C['blue'],U)]):
  x=42+i*340;p=route(t,keys);state='已撤离' if p[1]>1040 else '静步' if t>14 else '行动中'
  d.ellipse((x,1563,x+39,1602),outline=c,width=2);text(d,(x+20,1583),s,21,c,True,a='mm')
  text(d,(x+54,1567),role,23,C['text'],True);text(d,(x+54,1602),state,19,C['muted'])
 ln(d,[(42,1645),(1038,1645)],C['line'])
 for start,end,s in NARRATION:
  if start<=t<end:
   for i,ss in enumerate(wrap(s)):text(d,(540,1700+i*47),ss,34,C['text'],True,a='mm')
 if 5.4<t<7.2:box(d,(305,400,775,454),'#201c24',C['red'],3);text(d,(540,428),'异常：受击后重新聚合',26,C['red'],True,a='mm')
 if 39<t<44.7:
  remain=max(0,44.7-t);box(d,(270,392,810,477),'#201821','#8c525a',3)
  text(d,(298,407),'门闩',22,C['red']);text(d,(785,407),f'{remain:04.1f}s',24,C['red'],True,a='ra',mono=True)
  d.rectangle((300,453,780,459),fill='#4d3038');d.rectangle((300,453,300+480*remain/5.7,459),fill=C['red'])
 if 18.2<t<20.8:
  card=Image.new('RGBA',(W,H));cd=ImageDraw.Draw(card);cd.rectangle((40,265,1040,1525),fill=(5,10,15,145))
  box(cd,(165,690,915,1080),'#111d28',C['gold'],6,2);text(cd,(205,723),'携行工具 / 03',21,C['muted'])
  box(cd,(395,790,685,875),'#28343a',C['gold'],8,3)
  for x in (450,540,630):cd.ellipse((x-23,810,x+23,856),outline='#9b9d8b',width=2);ln(cd,[(x,816),(x,849)],'#9b9d8b',2)
  ln(cd,[(540,790),(540,768),(565,768)],C['gold'],3);text(cd,(540,936),'发条响器',41,C['gold'],True,a='mm');text(cd,(540,1006),'延时启动 · 持续敲击',25,C['text'],a='mm')
  im=Image.alpha_composite(im.convert('RGBA'),card).convert('RGB');d=ImageDraw.Draw(im)
 if t>=52.7:
  end=Image.new('RGBA',(W,H),(5,10,15,205));ed=ImageDraw.Draw(end);text(ed,(540,635),'任务完成',68,C['cyan'],True,a='mm');ln(ed,[(240,725),(840,725)],C['line'],2)
  for x,big,small in [(335,'4 / 4','全员撤离'),(745,'0','永久击杀')]:text(ed,(x,835),big,74,C['text'],True,a='mm',mono=True);text(ed,(x,925),small,27,C['muted'],a='mm')
  text(ed,(540,1080),'活着回来，也是答案。',37,C['gold'],True,a='mm');text(ed,(540,1180),'无声钟楼 / 探索记录 001',23,C['muted'],a='mm')
  im=Image.alpha_composite(im.convert('RGBA'),end).convert('RGB');d=ImageDraw.Draw(im)
 ln(d,[(42,1828),(1038,1828)],C['line'],3);ln(d,[(42,1828),(42+996*t/DURATION,1828)],C['gold'],3)
 text(d,(42,1855),'独立虚构样例 · 非正式设定',19,C['muted']);text(d,(1038,1855),f'{int(t):02} / 58',19,C['muted'],a='ra',mono=True)
 if t<.25:im=Image.blend(Image.new('RGB',im.size,C['bg']),im,ease(t/.25))
 if t>57:im=Image.blend(im,Image.new('RGB',im.size,C['bg']),ease(t-57))
 return im
def wrap(s):
 if len(s)<=19:return [s]
 k=min([i+1 for i,c in enumerate(s) if c in '，。' and 5<i<len(s)-5] or [len(s)//2],key=lambda x:abs(x-len(s)/2))
 return [s[:k],s[k:]]
NARRATION=json.loads((ROOT/'源文件'/'旁白.json').read_text(encoding='utf8'))

def audio():
 sr=48000;t=np.arange(sr*DURATION)/sr;rng=np.random.default_rng(22);sig=np.zeros((len(t),2),np.float32)
 drone=(np.sin(2*np.pi*55*t)*.008+np.sin(2*np.pi*82.41*t)*.003)*(1+.2*np.sin(t*.6));sig[:,0]=drone;sig[:,1]=drone*.96
 def add(at,s,pan=0,reverb=0):
  i=int(at*sr);n=min(len(s),len(sig)-i)
  if n<=0:return
  for ch,g in enumerate((math.sqrt((1-pan)/2),math.sqrt((1+pan)/2))):sig[i:i+n,ch]+=s[:n]*g
  if reverb:
   for delay,g in [(.065,.23),(.13,.12),(.24,.065)]:add(at+delay,s*g,-pan,0)
 def thud(at,vol=.1,pan=0,hard=True):
  tt=np.arange(int(sr*.38))/sr;s=(rng.normal(0,.42 if hard else .12,len(tt))+np.sin(2*np.pi*(65 if hard else 110)*tt))*np.exp(-tt*(24 if hard else 38))*vol;add(at,s,pan,1)
 def metal(at,f=700,dur=.7,vol=.08,pan=0):
  tt=np.arange(int(sr*dur))/sr;s=np.zeros(len(tt))
  for ratio,amp in [(1,1),(2.71,.4),(4.07,.15)]:s+=np.sin(2*np.pi*f*ratio*tt)*amp
  add(at,s*np.exp(-tt*8/dur)*vol,pan,1)
 def scrape(at,dur=.4,vol=.04,pan=0):
  tt=np.arange(int(sr*dur))/sr;s=rng.normal(0,1,len(tt));s=np.convolve(s,np.ones(7)/7,'same');s*=np.sin(math.pi*tt/dur)**2*vol;add(at,s,pan,1)
 for at in np.arange(37,50,.55):
  tt=np.arange(int(sr*.18))/sr;add(at,np.sin(2*np.pi*62*tt)*np.exp(-tt*35)*.045)
 for at in [0.8,1.3,1.8,8.4,8.8,9.2,9.6,10.0]:thud(at,.025,hard=False)
 scrape(2.48,.35,.06);thud(2.9,.18);metal(2.92,410,1.1,.08)
 for at in [3.05,3.19,3.4,3.58]:metal(at,940+at*90,.2,.025)
 scrape(5.4,.7,.06);metal(6.2,190,1.2,.06)
 for at in [10.85,11.02,11.25]:thud(at,.055,-.3)
 for at in np.arange(23.1,36.1,.32):metal(at,1300,.07,.018,-.7)
 metal(36.15,630,.08,.04,-.7);scrape(36.25,.18,.06,-.7);thud(28.65,.15,-.6);scrape(28.8,.4,.06,-.6);thud(29,.065,-.6)
 for at in np.arange(38,44.7,1.1):thud(at,.12,-.6);scrape(at+.05,.22,.04,-.6)
 thud(44.7,.21,-.5)
 for at in [44.75,44.88,45.1]:scrape(at,.3,.08,-.5)
 scrape(47.1,.25,.07);metal(48.1,850,.8,.10,.25)
 for at in np.arange(45,52,.38):thud(at,.025,hard=False)
 for at,f in [(52.8,220),(53.1,277.18),(53.4,329.63)]:metal(at,f,1.6,.035)
 log=[]
 for i,(s,e,words) in enumerate(NARRATION):
  src=ROOT/'音频'/f'neural_{i:02d}.mp3'
  if not src.exists():raise FileNotFoundError('Regenerate narration: '+str(src))
  pr=json.loads(subprocess.check_output(['ffprobe','-v','quiet','-show_format','-of','json',str(src)]));dur=float(pr['format']['duration']);tempo=max(1,dur/(e-s-.08));log.append({'line':i,'duration':dur,'tempo':tempo})
  raw=subprocess.check_output(['ffmpeg','-v','error','-i',str(src),'-af',f'atempo={tempo:.5f},highpass=f=85,loudnorm=I=-17:TP=-2:LRA=7','-f','f32le','-ar',str(sr),'-ac','1','pipe:1'])
  add(s,np.frombuffer(raw,dtype='<f4')*1.22)
 sig*=np.minimum(1,t/.2)[:,None]*np.minimum(1,(DURATION-t)/.8)[:,None];sig=np.tanh(sig*1.15)/1.15
 with wave.open(str(ROOT/'音频'/'完整混音.wav'),'wb') as w:w.setnchannels(2);w.setsampwidth(2);w.setframerate(sr);w.writeframes((np.clip(sig,-1,1)*32767).astype('<i2').tobytes())
 (ROOT/'音频'/'旁白适配.json').write_text(json.dumps(log,indent=2),encoding='utf8')
def main():
 if '--stills' in sys.argv:
  for t in [1,3,6,12,16,19.5,25,29,34,37,41,45,48.5,51,54]:render(t).save(ROOT/f'预览_{t:04.1f}.jpg',quality=95)
  return
 audio();cmd=['ffmpeg','-y','-v','warning','-f','rawvideo','-pixel_format','rgb24','-video_size',f'{W}x{H}','-framerate',str(FPS),'-i','pipe:0','-i',str(ROOT/'音频'/'完整混音.wav'),'-c:v','libx264','-preset','fast','-crf','18','-pix_fmt','yuv420p','-c:a','aac','-b:a','192k','-movflags','+faststart','-shortest',str(ROOT/'外境_无声钟楼_简约修订.mp4')]
 p=subprocess.Popen(cmd,stdin=subprocess.PIPE)
 for i in range(int(DURATION*FPS)):
  p.stdin.write(render(i/FPS).tobytes())
  if i%(FPS*5)==0:print(f'Render {i//FPS:02d}/{DURATION}s',flush=True)
 p.stdin.close()
 if p.wait():raise RuntimeError('Encode failed')
 render(12).save(ROOT/'封面.jpg',quality=95);print('DONE',flush=True)
if __name__=='__main__':main()
