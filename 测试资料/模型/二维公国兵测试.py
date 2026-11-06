import math,random,json,heapq,collections
from pathlib import Path
OUT=Path('二维公国兵测试');OUT.mkdir(exist_ok=True)
# Coordinates in inches, map 24 by 24. Unit footprint approximated by a 1-inch grid cell.
walls={(x,y) for x in range(12,16) for y in range(12,16)}|{(x,y) for x in range(4,8) for y in range(6,10)}
low={(x,18) for x in (6,7,8,16,17,18)}|{(x,12) for x in (2,3,4,18,19,20)}|{(x,4) for x in (10,11,12)}
start={'P':(11,3),'1':(9,21),'2':(19,21),'3':(3,15),'4':(21,15),'5':(17,7)}
def dist(a,b):return math.dist(a,b)
def ray(a,b):
 n=max(1,math.ceil(dist(a,b)*12));return {(round(a[0]+(b[0]-a[0])*i/n),round(a[1]+(b[1]-a[1])*i/n)) for i in range(1,n)}
def los(a,b):return not(ray(a,b)&walls)
def covered(a,b):return any(dist(b,c)<=1.5 and c in ray(a,b) for c in low)
def run(seed,detail=False):
 r=random.Random(seed);logs=[];states=[];u={n:dict(pos=p,b=0,down=False,out=False,burn=False,re=2 if n=='P' else 1) for n,p in start.items()};pool={'刃':2,'铸':1,'心':1,'月':1,'杯':1};spent={k:0 for k in pool};used={k:0 for k in pool};counts=collections.Counter()
 def log(s):
  if detail:logs.append(s)
 def use(k):pool[k]-=1;spent[k]+=1;used[k]+=1
 def roll(e):
  d=[r.randint(1,6) for _ in range(2+abs(e))];return d,sum(sorted(d,reverse=e>=0)[:2])
 def melee(a,b):return dist(u[a]['pos'],u[b]['pos'])<=1.99 and los(u[a]['pos'],u[b]['pos'])
 def atk(a,t,kind):
  v=u[t];shoot=kind=='射击';e=(3 if a=='P' else 0)-int(u[a]['down'])-int(u[a]['burn']);cov=shoot and covered(u[a]['pos'],v['pos']);long=shoot and dist(u[a]['pos'],v['pos'])>12;e-=int(cov)+int(long)
  ds,total=roll(e);raw=list(ds);month=''
  if a=='P' and total<7 and pool['月']:
   use('月');i=ds.index(min(ds));old=ds[i];ds[i]=r.randint(1,6);total=sum(sorted(ds,reverse=e>=0)[:2]);month=f' 月{old}→{ds[i]} 最终{ds}'
  counts['P攻击' if a=='P' else '兵攻击']+=1
  log(f'{a}{u[a]["pos"]}→{t}{v["pos"]} {kind} 命中骰{raw}{month} 净修正{e} 掩体{cov}远距{long} = {total} '+('命中' if total>=7 else '未中'))
  if total<7:return
  counts['P命中' if a=='P' else '兵命中']+=1;blade=forge=0
  if a=='P' and pool['刃']:use('刃');blade=1
  blood=v['b'];v['b']=0
  if t=='P' and pool['铸']:use('铸');forge=1
  ds,val=roll(blood+int(total>=12)+int(not shoot and v['down']));armor=2 if t=='P' else 1;res=val+int(a=='P')+blade-forge-armor
  if res>=9:v['out']=True;out='退场'
  elif res>=7:v['b']+=2 if v['down'] else 1;v['down']=True;out='倒地'
  elif res>=2:v['b']+=1;out='轻伤'
  else:out='无效'
  log(f'造伤{ds} 取二{val}；血印耗{blood} 固有+{int(a=="P")} 刃+{blade} 铸-{forge} 护甲-{armor} = {res} {out}')
  if a=='P' and not v['out']:v['burn']=True;v['b']+=1;log('火焰：血印+1，燃烧攻击-1骰')
  if t=='P' and not v['out'] and v['b'] and pool['心']:use('心');v['b']-=1;log('结算后心1清血印1')
  if t=='P' and not shoot and not v['out'] and not v['down'] and v['re'] and melee(a,t):
   v['re']-=1;counts['火拳']+=1;log('火拳，剩余反应'+str(v['re']));atk('P',a,'火拳')
 def reachable(n,budget):
  origin=u[n]['pos'];occupied={v['pos'] for k,v in u.items() if k!=n and not v['out']};q=[(0,origin)];cost={origin:0};prev={}
  while q:
   c,p=heapq.heappop(q)
   if c>cost[p]:continue
   for dx,dy in [(1,0),(-1,0),(0,1),(0,-1),(1,1),(1,-1),(-1,1),(-1,-1)]:
    t=(p[0]+dx,p[1]+dy)
    if not(0<=t[0]<24 and 0<=t[1]<24) or t in walls or t in occupied:continue
    if dx and dy and ((p[0]+dx,p[1]) in walls or (p[0],p[1]+dy) in walls):continue
    nc=c+math.hypot(dx,dy)*(2 if t in low else 1)
    if nc<=budget and nc<cost.get(t,999):cost[t]=nc;prev[t]=p;heapq.heappush(q,(nc,t))
  return cost,prev
 def move(n,target,prev):
  path=[target]
  while path[-1]!=u[n]['pos']:path.append(prev[path[-1]])
  path.reverse();log(f'{n}移动路径{path}');u[n]['pos']=target
 for turn in range(1,13):
  log('\n第'+str(turn)+'轮')
  for n,v in u.items():v['re']=2 if n=='P' else 1
  p=u['P']
  if pool['杯'] and spent['铸']:use('杯');pool['铸']+=1;spent['铸']-=1;log('杯1恢复铸1')
  near=[n for n in '12345' if not u[n]['out'] and melee('P',n)]
  for n in near:counts['火环目标']+=1;atk('P',n,'火环')
  stood=p['down'];p['down']=False
  if stood:log('P起身，移动减半')
  live=[n for n in '12345' if not u[n]['out']]
  if not live:break
  adjacent=[n for n in live if melee('P',n)]
  if adjacent:atk('P',max(adjacent,key=lambda n:u[n]['b']),'普通')
  else:
   budget=2 if stood else 4;cost,prev=reachable('P',budget)
   target=min(live,key=lambda n:dist(p['pos'],u[n]['pos']))
   # Prioritize approaching a target; among equally close cells prefer fewer clear enemy firing lines.
   best=min(cost,key=lambda x:(round(dist(x,u[target]['pos']),2),sum(los(v['pos'],x) and not covered(v['pos'],x) for n,v in u.items() if n!='P' and not v['out']),cost[x]))
   if best!=p['pos']:move('P',best,prev)
   if melee('P',target):atk('P',target,'普通')
  for n in '12345':
   if p['out']:break
   v=u[n]
   if v['out']:continue
   stood=v['down'];v['down']=False
   if stood:log(n+'起身')
   if melee(n,'P'):atk(n,'P','刺刀');continue
   # Avoid shooting into friendly melee; otherwise seek a clear, covered firing position.
   if any(k!=n and not u[k]['out'] and melee(k,'P') for k in '12345'):log(n+'避免误伤友军，保持位置');continue
   cost,prev=reachable(n,3 if stood else 6)
   candidates=[x for x in cost if 1.99<dist(x,p['pos'])<=24 and los(x,p['pos'])]
   if candidates:
    best=min(candidates,key=lambda x:(int(dist(x,p['pos'])>12)+int(covered(x,p['pos']))-int(covered(p['pos'],x)),cost[x],-dist(x,p['pos'])))
    if best!=v['pos']:move(n,best,prev)
    atk(n,'P','射击')
   else:log(n+'无安全射线')
  states.append({'轮':turn,'位置状态':{n:dict(v) for n,v in u.items()},'可用虚相':dict(pool),'耗用虚相':dict(spent)})
  if p['out'] or all(u[n]['out'] for n in '12345'):break
 result='角色退场' if p['out'] else '全歼' if all(u[n]['out'] for n in '12345') else '12轮未决'
 return {'种子':seed,'结果':result,'轮数':turn,'敌退场':[n for n in '12345' if u[n]['out']],'次数':dict(counts),'虚相累计':used,'末尾可用':pool,'逐轮':states},logs
seeds=[754491237,489690734,3808889068,4280649435,1844120670]
for i,s in enumerate(seeds,1):
 result,logs=run(s,True);(OUT/f'{i}-完整记录.txt').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n\n'+'\n'.join(logs),encoding='utf-8');print(json.dumps({k:v for k,v in result.items() if k!='逐轮'},ensure_ascii=False))
results=[run(s)[0] for s in range(10000,10200)];count=collections.Counter(x['结果'] for x in results);print('BATCH',dict(count));(OUT/'200场汇总.json').write_text(json.dumps({'结果':dict(count),'场次':results},ensure_ascii=False),encoding='utf-8')
