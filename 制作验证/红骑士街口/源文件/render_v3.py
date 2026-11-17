"""Original staged 1-v-5 short. Screen-space projection preserves fine lines on zoom."""
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageChops
import pathlib, math, random, json, subprocess, sys, wave, bisect
from navigation import interpolate
import numpy as np
ROOT=pathlib.Path(__file__).resolve().parent.parent
W,H,FPS,DURATION=1080,1920,24,96
VIEW=(42,260,1038,1438)
C={'bg':'#0b1012','panel':'#10191c','line':'#3a494a','ink':'#d8dfd8','muted':'#879591','gold':'#d5ac60','red':'#b64d50','enemy':'#d4b491','cyan':'#8bb8ab'}
F={}
_yy,_xx=np.mgrid[0:H,0:W]
_v=.68+.32*np.exp(-(((_xx-540)/650)**2+((_yy-850)/900)**2))
VIGNETTE=Image.fromarray(np.uint8(_v*255)).convert('RGB')
del _yy,_xx,_v
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
 times=globals().get('NAV_TIMES',{}).get(id(k))
 if times is not None:
  j=max(0,min(len(k)-2,bisect.bisect_right(times,t)-1));st,a=k[j];en,b=k[j+1]
  v=cl((t-st)/max(en-st,1e-8));return(ler(a[0],b[0],v),ler(a[1],b[1],v))
 if t<=k[0][0]:return k[0][1]
 for (s,p),(e,q) in zip(k,k[1:]):
  if t<=e:
   z=ez((t-s)/(e-s));return tuple(ler(p[i],q[i],z) for i in range(len(p)))
 return k[-1][1]
# All paths are deliberate choreography, not an autonomous combat model.
DOWN=[24.6,48,54.5,84,73.5]
NAMES=['暴徒1','暴徒2','暴徒3','暴徒4','头目']

CAM=[(0,(530,650,.86)),(6,(530,650,.86)),(8,(540,490,.91)),(12,(540,490,.91)),(14,(665,400,1.2)),(17,(500,740,1.25)),(19,(500,740,1.25)),(21,(480,650,1.35)),(26,(480,650,1.35)),(28,(555,660,.98)),(33,(555,700,1.05)),(35,(500,740,1.6)),(38,(500,740,1.6)),(40,(495,690,1.02)),(44,(495,690,1.02)),(46,(555,660,1.4)),(50,(555,660,1.4)),(52,(600,750,1.3)),(56,(600,750,1.3)),(58,(650,850,.98)),(62,(650,850,.98)),(65,(600,935,1.25)),(69,(600,935,1.25)),(71,(635,930,1.5)),(75,(635,930,1.5)),(77,(655,750,1.1)),(85,(655,750,1.1)),(88,(535,650,.86))]
NARR=json.loads((ROOT/'源文件'/'旁白_v2.json').read_text(encoding='utf8'))
WALLS=[((240,70),(240,1020)),((800,70),(800,1020)),((240,100),(445,100)),((635,100),(800,100))]
PILLARS=[(590,550),(315,250)]
ATTACKS=[(22.2,0,'knife'),(23.5,-1,'shield'),(24.55,-1,'pommel'),(31.2,1,'axe'),(34.8,2,'club'),(46.8,1,'axe'),(47.9,-1,'sword'),(52.4,2,'club'),(54.4,-1,'pommel'),(71.4,4,'knife'),(73.4,-1,'sword')]
PHASE=[(0,'护送','受伤信使 · 街口遭遇'),(7,'追兵','远端弩手 · 两侧展开'),(17,'选位','先保护信使，再争取主动'),(21,'破局','盾挡弩箭 · 短刀手先到'),(28,'合围','斧手正压，棍手绕后'),(35,'失盾','左臂受伤 · 盾带断裂'),(40,'变招','推动车架 · 遮挡弩手'),(46,'反击','车轮限制退路'),(52,'贴身','截断棍手的补刀'),(58,'截人','头目转向信使'),(64,'回援','放弃追击，抢占截击位置'),(70,'护住','控制持刀手，信使继续撤离'),(77,'对峙','四人失能，弩手孤立'),(84,'撤离','最后一人弃械 · 信使脱离'),(88,'战后','四人失能 · 一人投降 · 失盾受伤')]
NAV=json.loads((ROOT/'源文件'/'navigation_tracks.json').read_text(encoding='utf8'))
K=NAV['tracks']['knight'];P=[NAV['tracks'][f'enemy{i}'] for i in range(5)];COURIER=NAV['tracks']['courier']
NAV_TIMES={id(k):[row[0] for row in k] for k in [K,*P,COURIER]}
def state(t,name):return NAV['snapshots'][min(960,max(0,int(t*10)))]['units'][name]
RNG=random.Random(51)
STONES=[(x,y,RNG.randint(-1,1)) for y in range(120,1020,46) for x in range(250,800,55)]
def frame(t):
 im=Image.new('RGB',(W,H),C['bg']);d=ImageDraw.Draw(im)
 box(d,(16,18,1064,1900),'#0d1416','#354043',28,2)
 for x in (32,1048):
  for y in (246,1452):d.ellipse((x-4,y-4,x+4,y+4),outline='#75807b',width=1)
 txt(d,(48,66),'外 境  /  战 场 记 录',24,C['muted'])
 txt(d,(48,110),'街口 · 护送未完',49,C['ink'],True)
 txt(d,(1034,80),'演示 002',20,C['gold'],a='ra')
 txt(d,(1034,125),'低阶红骑士',23,C['gold'],a='ra')
 phase=next((s for at,*s in reversed(PHASE) if t>=at),PHASE[0][1:])
 txt(d,(50,201),phase[0],24,C['gold'],True);txt(d,(170,201),phase[1],23,C['muted'])
 cx,cy,z=path(t,CAM);scale=z*1.37
 for at,who,kind in ATTACKS:
  dt=t-at
  if 0<=dt<.24:
   amp=2.5*(1-dt/.24);cx+=math.sin(dt*100)*amp;cy+=math.cos(dt*82)*amp*.6
 cartshift=ez((t-39)/3.0)
 def cart(q):return(q[0]+140*cartshift,q[1]-80*cartshift)
 def cli(a,b,c,w=2):line(d,[p(cart(a)),p(cart(b))],c,w)
 def crect(r,fill,out=None,w=1):d.rectangle((*p(cart(r[:2])),*p(cart(r[2:]))),fill=fill,outline=out,width=w)
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
 crect((260,610,396,790),'#181d1d','#9b8c6b',2)
 for x in (280,310,340,370):cli((x,620),(x,780),'#665d4a',2)
 for y in (638,758):cli((248,y),(409,y),'#a18a62',4)
 for q in [(255,638),(402,638),(255,758),(402,758)]:ellipse(cart(q),13,'#111719','#7f795f',2)
 for q in PILLARS:
  ellipse((q[0]+7,q[1]+8),34,'#151d1f');ellipse(q,31,'#313d3d','#98a29a',2);ellipse(q,23,None,'#61716a',1)
 for q in [(750,825),(745,875),(290,910)]:
  ellipse(q,24,'#292b25','#75735c',2);li((q[0]-20,q[1]),(q[0]+20,q[1]),'#575b49',2)
 for q,s in [(cart((325,835)),'车架'),((645,520),'石柱'),((540,155),'封闭院门')]:txt(d,p(q),s,19,C['muted'],a='mm')
 if 8<t<12:
  for i,qs in enumerate([[(430,460),(430,615)],[(665,450),(665,700)],[(535,250),(520,650)]]):
   line(d,[p(q) for q in qs],'#a37561',2)
  txt(d,p((600,370)),'弩手压制',21,C['enemy'],True,a='mm')
 if 29<t<34:
  pts=[(665,470),(665,705),(555,745)];line(d,[p(q) for q in pts],C['enemy'],3)
  txt(d,p((670,790)),'侧后包夹',23,C['enemy'],True,a='mm')
 if 58<t<63:
  pts=[(740,770),(740,920),(580,940)];line(d,[p(q) for q in pts],'#ce8d79',3)
  txt(d,p((690,855)),'截住信使',23,'#ce8d79',True,a='mm')
 for at,start,end in [(21.8,(535,250),(458,648)),(42.5,(535,250),(532,530))]:
  if at-.6<t<at:
   v=cl((t-(at-.6))/.6);q=(ler(start[0],end[0],v),ler(start[1],end[1],v))
   a=math.atan2(end[1]-start[1],end[0]-start[0]);li((q[0]-math.cos(a)*24,q[1]-math.sin(a)*24),q,'#e3d7aa',3)
  if at<t<at+.4:ellipse(end,10+25*cl((t-at)/.4),None,C['gold'],2)
 if t>=21.8:li((440,657),(429,685),'#c3b992',2)
 if t>=42.5:li((532,530),(537,510),'#c3b992',2)
 kp=path(t,K);ep=[path(t,k) for k in P]
 # Foot marks and movement trails are restrained.
 for keys,col in [(K,'#6f6654')]+[(k,'#555c55') for k in P]:
  a=path(max(0,t-.5),keys);b=path(t,keys)
  if math.dist(a,b)>5:li(a,b,col,2)
 def actor(q,ang,idx,down=False):
  # The entire character grammar: circle + heading + label + state.
  knight=idx==-1;col=C['gold'] if knight else C['enemy'];x,y=p(q)
  surrendered=idx==3 and t>=84
  if down:col=C['muted']
  ellipse(q,15,'#61363b' if knight else '#182326',col,2)
  if down:
   li((q[0]-6,q[1]-6),(q[0]+6,q[1]+6),col,2)
   li((q[0]-6,q[1]+6),(q[0]+6,q[1]-6),col,2)
  elif not surrendered:
   points=[(q[0]+math.cos(ang)*10,q[1]+math.sin(ang)*10),
           (q[0]+math.cos(ang+2.5)*7,q[1]+math.sin(ang+2.5)*7),
           (q[0]+math.cos(ang-2.5)*7,q[1]+math.sin(ang-2.5)*7)]
   d.polygon([p(a) for a in points],fill=col)
  else:ellipse(q,5,None,C['cyan'],2)
  label='红骑士' if knight else '头目' if idx==4 else f'暴徒{idx+1}'
  suffix=' · 失能' if down else ' · 投降' if surrendered else ''
  txt(d,(x,y-31*scale),label+suffix,22 if knight else 19,col,knight,a='mm')
  if knight and t>=35:ellipse((q[0]+15,q[1]+14),3,'#d99b7f')
 # Face nearest live threat, turn visibly before engagement.
 live=[i for i in range(5) if t<DOWN[i]]
 target=min(live,key=lambda i:math.dist(kp,ep[i])) if live else 4
 ka=math.atan2(ep[target][1]-kp[1],ep[target][0]-kp[0])
 for i,q in enumerate(ep):actor(q,state(t,f'enemy{i}')['heading'],i,t>=DOWN[i] and i!=3)
 actor(kp,state(t,'knight')['heading'],-1)
 # Combat is an event pulse between logical centers, never a held weapon/skeleton.
 for at,who,kind in ATTACKS:
  dt=t-at
  if -.2<dt<.5:
   if who==-1:
    target=min((i for i in range(5) if at<=DOWN[i]+.1),key=lambda i:math.dist(kp,ep[i]))
    a,b=kp,ep[target]
   else:a,b=ep[who],kp
   middle=((a[0]+b[0])/2,(a[1]+b[1])/2)
   col=C['gold'] if who==-1 else '#ce9a84'
   if dt<0:ellipse(a,18,None,col,1)
   else:
    line(d,[p(a),p(b)],col,2)
    ellipse(middle,3+16*cl(dt/.45),None,col,2)
 if 35.1<t<96:
  sx,sy=p((470,790));rr=14*scale
  d.polygon([(sx-rr,sy-rr),(sx+rr,sy-rr),(sx+rr*.8,sy+rr*.5),(sx,sy+rr*1.3),(sx-rr*.8,sy+rr*.5)],fill='#684047',outline='#b29360',width=2)
  li((460,792),(481,784),'#bca585',2)
  if t<38.5:txt(d,p((475,830)),'盾带断裂',24,'#dc9f87',True,a='mm')
 if t>=84:ellipse((690,710),9,None,C['muted'],2)
 # Courier follows the same disc-agent grammar, with no body or carried prop.
 cp=path(t,COURIER)
 if cp[1]<1070:
  ellipse(cp,13,'#203a34',C['cyan'],2)
  a=state(t,'courier')['heading']
  d.polygon([p((cp[0]+math.cos(a)*9,cp[1]+math.sin(a)*9)),
             p((cp[0]+math.cos(a+2.5)*6,cp[1]+math.sin(a+2.5)*6)),
             p((cp[0]+math.cos(a-2.5)*6,cp[1]+math.sin(a-2.5)*6))],fill=C['cyan'])
  txt(d,p((cp[0],cp[1]+30)),'信使 · 受伤',20,C['cyan'],a='mm')
  if t<7:
   li((cp[0],cp[1]+45),(cp[0],1040),C['cyan'],2)
   txt(d,p((550,1000)),'南侧出口',23,C['cyan'],True,a='mm')
 for i,at in enumerate(DOWN):
  dt=t-at
  if i!=3 and 0<dt<1.1:
   q=ep[i]
   for j in range(11):
    a=j*2.399;r=(9+j%4*5)*cl(dt/.5)
    xx,yy=p((q[0]+math.cos(a)*r,q[1]+math.sin(a)*r))
    col='#8b8067' if dt<.45 else '#514f43'
    d.ellipse((xx-2,yy-2,xx+2,yy+2),fill=col)
 # Warm lantern pools and restrained atmospheric shade, composited below UI.
 shade=Image.new('RGBA',(W,H));sd=ImageDraw.Draw(shade)
 for q in [(260,400),(790,910)]:
  xx,yy=p(q)
  for r in range(120,5,-12):sd.ellipse((xx-r,yy-r,xx+r,yy+r),fill=(211,165,82,int(18*(1-r/125))))
 im=Image.alpha_composite(im.convert('RGBA'),shade).convert('RGB');im=ImageChops.multiply(im,VIGNETTE);d=ImageDraw.Draw(im)
 # Shield insert makes the material failure visible, without covering the fight.
 if 35.2<t<38.2:
  box(d,(110,335,585,520),'#10191c','#ab8b64',5,2)
  d.polygon([(150,365),(250,365),(245,435),(200,480),(155,435)],fill='#593c40',outline='#d6ad63',width=3)
  line(d,[(165,402),(200,421),(222,393)],'#b29b78',5)
  line(d,[(203,420),(211,437)],'#e0bc82',2)
  txt(d,(280,375),'盾带断裂',28,'#dfa487',True)
  txt(d,(280,425),'继续持剑 · 放弃回收',20,C['muted'])
 # Event captions and diegetic short orders.
 cues=[(12.5,16.5,'头目','把人留下，你可以走。',C['enemy']),
       (17,19.8,'红骑士','跟紧我。别停。',C['gold']),
       (28,30.8,'头目','斧头顶住，绕他后面！',C['enemy']),
       (35.1,38.5,'转折','左臂受伤 / 盾带断裂','#df9d85'),
       (40,43.5,'变招','不捡盾。先切断弩手视线。',C['gold']),
       (59,62.5,'头目','别管他，抓送信的！',C['enemy']),
       (65,68.5,'红骑士','往南走。别回头。',C['gold']),
       (80,83,'弩手','……我不打了。',C['enemy'])]
 for st,en,who,msg,col in cues:
  if st<=t<en:
   a=ez(min((t-st)/.2,(en-t)/.2));y=1320+int(20*(1-a))
   box(d,(95,y-75,985,y+80),'#111b1e',col,4,2)
   txt(d,(120,y-52),who,22,col,True);txt(d,(540,y+9),msg,29,C['ink'],True,a='mm')
 # Stable locator for the two groups when camera goes close.
 if z>1.18:
  box(d,(865,305,1015,535),'#10191c','#65736b',3)
  def mini(q):return(875+(q[0]-230)*.24,315+(q[1]-100)*.21)
  for i,q in enumerate(ep):
   xx,yy=mini(q);d.ellipse((xx-2,yy-2,xx+2,yy+2),fill=C['muted'] if t>=DOWN[i] else C['enemy'])
  for q,col in [(kp,C['gold']),(cp,C['cyan'])]:
   xx,yy=mini(q);d.ellipse((xx-4,yy-4,xx+4,yy+4),fill=col)
  txt(d,(940,543),'位置总览',16,C['muted'],a='mt')
 # Hide projected geometry outside the map viewport and draw instrument framing.
 d.rectangle((0,0,W,259),fill=C['bg']);d.rectangle((0,1439,W,H),fill=C['bg'])
 # Header redraw after crop.
 txt(d,(48,55),'外 境  /  战 场 记 录',24,C['muted']);txt(d,(48,100),'街口 · 护送未完',49,C['ink'],True)
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
  txt(d,(x+25,1486),str(i+1)+(' 降' if i==3 and t>=84 else ' 失能' if t>=DOWN[i] else ' 接敌'),19,col)
 box(d,(42,1570,1038,1754),'#10191b',None,7)
 for s,e,words in NARR:
  if s<=t<e:
   parts=wrap(words)
   for j,ss in enumerate(parts):txt(d,(540,1610+j*49),ss,31,C['ink'],True,a='mt')
 txt(d,(48,1790),'护送 / 信使撤离' if t<85 else '护送完成',23,C['gold']);txt(d,(1035,1790),'受伤 · 失盾' if t>35 else '已接敌' if t>21 else '尚未接触',23,'#d09277' if t>35 else C['muted'],a='ra')
 line(d,[(45,1845),(1035,1845)],C['line'],2);line(d,[(45,1845),(45+990*t/DURATION,1845)],C['gold'],3)
 txt(d,(45,1870),'极简单位 · 独立导航轨迹 · 演示剧情',19,C['muted'])
 if 0<t<5.8:
  box(d,(150,1190,930,1370),'#0e171a','#706549',4,2)
  txt(d,(540,1220),'赢下打斗，还不够。',42,C['ink'],True,a='mt');txt(d,(540,1286),'他还得把人带出去。',29,C['gold'],True,a='mt')
 if t>=88:
  ov=Image.new('RGBA',(W,H));od=ImageDraw.Draw(ov)
  box(od,(135,555,945,1175),(10,18,21,241),'#a48c5b',8,2)
  txt(od,(540,602),'交 战 结 束',48,C['gold'],True,a='mt')
  for yy,l,r in [(716,'信使','成功撤离'),(791,'暴徒','四人失能 · 一人投降'),(866,'红骑士','左臂受伤'),(941,'装备','遗失盾牌')]:
   txt(od,(190,yy),l,28,C['muted']);txt(od,(880,yy),r,28,C['ink'],True,a='ra')
  line(od,[(190,1000),(890,1000)],C['line'],2)
  txt(od,(540,1043),'人带走了。盾留在街上。',31,C['gold'],True,a='mt')
  im=Image.alpha_composite(im.convert('RGBA'),ov).convert('RGB')
 if t>95:im=Image.blend(im,Image.new('RGB',im.size,C['bg']),ez(t-95))
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
 for at,who,kind in ATTACKS:
  hit(at,kind in ('knife','sword','axe'),.12 if who==-1 else .085)
  wt=np.arange(int(sr*.22))/sr
  noise=rng.normal(0,1,len(wt));noise=np.convolve(noise,np.ones(11)/11,'same')
  add(at-.23,noise*np.sin(np.pi*wt/.22)**2*.055)
 for at in np.arange(28,35,.65):hit(at,False,.013)
 for at in np.arange(59,66,.5):hit(at,False,.016)
 for at in np.arange(78,83,1.1):hit(at,False,.02)
 for at in (35.1,84):
  vt=np.arange(int(sr*.65))/sr
  add(at,(np.sin(vt*math.tau*610)+.3*np.sin(vt*math.tau*1290))*np.exp(-vt*8)*.025)
 hit(21.8,True,.15)
 hit(35.1,False,.09)
 hit(42.5,False,.10)
 hit(84,True,.04)
 for at in np.arange(6,12,.6):hit(at,False,.015)
 for at in np.arange(39,42,.2):hit(at,False,.02)
 for at in np.arange(59,66,.42):hit(at,False,.025)
 log=[]
 for i,(s,e,words) in enumerate(NARR):
  src=ROOT/'音频'/f'v2_{i:02d}.mp3'
  dur=float(json.loads(subprocess.check_output(['ffprobe','-v','quiet','-show_format','-of','json',str(src)]))['format']['duration'])
  tempo=max(1,dur/(e-s-.12));log.append({'line':i,'source_duration':dur,'tempo':tempo})
  raw=subprocess.check_output(['ffmpeg','-v','error','-i',str(src),'-af',f'atempo={tempo:.6f},highpass=f=85,loudnorm=I=-17:TP=-2:LRA=7','-f','f32le','-ar',str(sr),'-ac','1','pipe:1'])
  add(s,np.frombuffer(raw,dtype='<f4')*1.13)
 sig*=np.minimum(1,tt/.25)[:,None]*np.minimum(1,(DURATION-tt)/1)[:,None]
 with wave.open(str(ROOT/'音频'/'修订混音.wav'),'wb') as w:
  w.setnchannels(2);w.setsampwidth(2);w.setframerate(sr);w.writeframes((np.clip(sig,-1,1)*32767).astype('<i2').tobytes())
 (ROOT/'音频'/'修订旁白适配.json').write_text(json.dumps(log,indent=2),encoding='utf8')
def main():
 if '--stills' in sys.argv:
  for t in [3,10,18,24.5,31,35.1,42,48,54.4,60,67,73.4,83,90]:frame(t).save(ROOT/f'极简预览_{t:04.1f}.jpg',quality=94)
  return
 audio()
 p=subprocess.Popen(['ffmpeg','-y','-v','warning','-f','rawvideo','-pixel_format','rgb24','-video_size',f'{W}x{H}','-framerate',str(FPS),'-i','pipe:0','-i',str(ROOT/'音频'/'修订混音.wav'),'-c:v','libx264','-preset','fast','-crf','18','-pix_fmt','yuv420p','-c:a','aac','-b:a','192k','-movflags','+faststart','-shortest',str(ROOT/'外境_红骑士街口_极简单位修订.mp4')],stdin=subprocess.PIPE)
 for i in range(FPS*DURATION):
  p.stdin.write(frame(i/FPS).tobytes())
  if i%(FPS*5)==0:print(f'render {i//FPS}/{DURATION}',flush=True)
 p.stdin.close()
 if p.wait():raise RuntimeError('Encoding failed')
 frame(18).save(ROOT/'极简封面.jpg',quality=95)
 print('DONE',flush=True)
if __name__=='__main__':main()
