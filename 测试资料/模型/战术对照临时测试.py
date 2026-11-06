import random,secrets,json
from pathlib import Path
OUT=Path('临时战斗测试');OUT.mkdir(exist_ok=True)
def run(seed,tactical):
 r=random.Random(seed); logs=[]; snapshots=[]
 u={n:dict(x=x,b=0,down=False,out=False,re=1) for n,x in [('P',0),('A',1),('B',3),('C',5),('D',7),('E',9)]}
 pool={'刃':2,'铸':1,'心':1,'月':1,'杯':1};spent={k:0 for k in pool};used={k:0 for k in pool};ready=False;hits={'P':0,'敌':0};att={'P':0,'敌':0};reactions=[]
 def log(s):logs.append(s)
 def use(k):pool[k]-=1;spent[k]+=1;used[k]+=1
 def dice(ex):
  a=[r.randint(1,6) for _ in range(2+abs(ex))];return a,sum(sorted(a,reverse=ex>=0)[:2])
 def hit(a,t,kind):
  v=u[t];ex=(1 if a=='P' else 0)-(1 if u[a]['down'] else 0)
  cover=kind=='射击' and u[t]['x'] in (0,4,8)
  if cover:ex-=1
  key='P' if a=='P' else '敌';att[key]+=1
  ds,total=dice(ex);before=list(ds);reroll=''
  if a=='P' and total<7 and pool['月']:
   use('月');i=ds.index(min(ds));old=ds[i];ds[i]=r.randint(1,6);total=sum(sorted(ds,reverse=ex>=0)[:2]);reroll=f'，月{old}→{ds[i]}，最终骰{ds}'
  log(f'{a}→{t} {kind}；命中{before}{reroll}，净骰修正{ex}（掩体{cover}），和{total} '+('命中' if total>=7 else '失败'))
  if total<7:return
  hits[key]+=1;blade=forge=0
  if a=='P' and pool['刃']:use('刃');blade=1
  blood=v['b'];v['b']=0
  if t=='P' and pool['铸']:use('铸');forge=1
  ex=blood+(total>=12)+(kind!='射击' and v['down']);ds,val=dice(ex);result=val+blade-forge-(t=='P')
  if result>=9:v['out']=True;res='退场'
  elif result>=7:v['b']+=2 if v['down'] else 1;v['down']=True;res='倒地'
  elif result>=2:v['b']+=1;res='轻伤'
  else:res='无效'
  log(f'造伤{ds}取二={val}；耗目标血印{blood}；刃+{blade} 铸-{forge} 护甲-{int(t=="P")}；结果{result} {res}，血印{v["b"]}')
  if t=='P' and not v['out'] and v['b'] and pool['心']:
   use('心');v['b']-=1;log('结算后：心1清除血印1，不撤销倒地')
 def move(n,x):old=u[n]['x'];u[n]['x']=x;log(f'位置 {n}:{old}→{x}')
 def pturn(turn):
  nonlocal ready
  ready=False;p=u['P']
  if pool['杯'] and spent['铸']:use('杯');pool['铸']+=1;spent['铸']-=1;log('激活开始：杯1恢复铸1')
  stood=p['down'];p['down']=False
  if stood:log('P起身；保守战术本次不移动')
  if not tactical and turn==1:ready=True;log('准备速攻C；占攻击位置');return
  live=[n for n in 'ABCDE' if not u[n]['out']]
  if not live:return
  t=min(live,key=lambda n:abs(u[n]['x']-p['x']));dist=abs(u[t]['x']-p['x'])
  if dist<=1:
   hit('P',t,'普通')
   if tactical and not stood and not any(not u[n]['out'] and abs(u[n]['x']-p['x'])<=1 for n in 'ABCDE'):
    # Fall back to cover only after all adjacent threats are removed; no free disengage.
    opts=[x for x in (0,4,8) if 0<abs(x-p['x'])<=4]
    if opts:move('P',max(opts,key=lambda x:min(abs(x-u[n]['x']) for n in live if not u[n]['out']) if any(not u[n]['out'] for n in live) else 99))
  elif dist<=5 and not stood:
   # Charge, not move+shoot; movement 4 plus 1 reach, no random charge bonus used.
   move('P',u[t]['x']-(1 if u[t]['x']>p['x'] else -1));hit('P',t,'冲锋近战')
  else:
   if not stood and dist>5:
    step=max(-4,min(4,u[t]['x']-p['x']));move('P',p['x']+step)
   ready=True;log('准备速攻：首个敌人进入近战范围')
 def enemy(n,turn):
  nonlocal ready
  v=u[n];p=u['P']
  if v['out']:return
  if v['down']:v['down']=False;log(n+'起身；移动减半') ;speed=2
  else:speed=4
  if n=='A' and turn==1:
   if abs(v['x']-p['x'])<=1 and p['re'] and not p['down']:
    if not tactical:log('A撤退，P放弃借机保留速攻')
    else:p['re']=0;reactions.append(f'R{turn}借机A');log('P借机，反应1→0');hit('P','A','借机')
   if not v['out'] and not v['down']:move(n,min(10,v['x']+3))
   return
  dist=abs(v['x']-p['x'])
  if n in 'ABC':
   if dist>1:move(n,v['x']+max(-speed,min(speed,p['x']+(1 if v['x']>p['x'] else -1)-v['x'])))
   if abs(v['x']-p['x'])>1:log(n+'未接敌，无攻击');return
   if ready and p['re'] and not p['down'] and (tactical or turn!=1 or n=='C'):
    p['re']=0;ready=False;reactions.append(f'R{turn}速攻{n}');log('P速攻，反应1→0');hit('P',n,'速攻')
    if v['out'] or v['down']:return
   hit(n,'P','普通')
  else:
   if dist>8:move(n,v['x']+max(-speed,min(speed,p['x']-v['x'])))
   if abs(v['x']-p['x'])<=1:hit(n,'P','普通')
   elif abs(v['x']-p['x'])<=8:hit(n,'P','射击')
 for turn in range(1,13):
  log(f'\n第{turn}轮')
  for v in u.values():v['re']=1
  pturn(turn)
  for n in 'ABCDE':
   if u['P']['out']:break
   enemy(n,turn)
  snapshots.append({'轮':turn,'位置状态':{n:f'{v["x"]}'+('退场' if v['out'] else '倒地' if v['down'] else '') for n,v in u.items()},'可用':dict(pool),'耗用':dict(spent),'反应剩余':u['P']['re']})
  if u['P']['out'] or all(u[n]['out'] for n in 'ABCDE'):break
 summary={'种子':seed,'战术':'先攻/掩体' if tactical else '等待速攻','结果':'角色退场' if u['P']['out'] else '全歼' if all(u[n]['out'] for n in 'ABCDE') else '12轮未决','轮数':turn,'敌退场':[n for n in 'ABCDE' if u[n]['out']],'攻击次数':att,'命中次数':hits,'反应':reactions,'累计虚相使用':used,'末尾可用':pool,'逐轮':snapshots}
 return summary,logs
seeds=[754491237,489690734,3808889068,4280649435,1844120670]; summaries=[]
for i,seed in enumerate(seeds,1):
 for tactical in (False,True):
  s,logs=run(seed,tactical);summaries.append(s)
  (OUT/f'{i}-{s["战术"].replace("/","_")}.txt').write_text(json.dumps(s,ensure_ascii=False,indent=2)+'\n\n'+'\n'.join(logs),encoding='utf-8')
(OUT/'结果.json').write_text(json.dumps(summaries,ensure_ascii=False,indent=2),encoding='utf-8')
for s in summaries:print(json.dumps({k:v for k,v in s.items() if k!='逐轮'},ensure_ascii=False))
print('TACTICAL STATES')
for s in summaries:
 if s['战术']=='先攻/掩体':print(s['种子'],json.dumps(s['逐轮'],ensure_ascii=False))
