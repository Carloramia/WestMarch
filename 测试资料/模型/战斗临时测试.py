import random,secrets,json
seed=secrets.randbits(32); rng=random.Random(seed)
units={'P':{'pos':0,'b':0,'down':False,'out':False,'react':1}}
for n,pos in [('A',1),('B',3),('C',5),('D',7),('E',9)]:units[n]={'pos':pos,'b':0,'down':False,'out':False,'react':1}
pool={'刃':2,'铸':1,'心':1,'月':1,'杯':1}; spent={k:0 for k in pool};events=[];states=[];ready=False
def log(s):events.append(s)
def use(k):pool[k]-=1;spent[k]+=1
def roll(extra=0):
 d=[rng.randint(1,6) for _ in range(2+abs(extra))];return d,sum(sorted(d,reverse=extra>=0)[:2])
def attack(a,t,kind='普通'):
 u,v=units[a],units[t]; bonus=1 if a=='P' else 0
 ds,total=roll(bonus)
 month=''
 if a=='P' and total<7 and pool['月']:
  use('月');i=ds.index(min(ds));old=ds[i];ds[i]=rng.randint(1,6);total=sum(sorted(ds,reverse=True)[:2]);month=f'；月重投{old}→{ds[i]}'
 log(f'{a}→{t} {kind} 命中骰{ds}{month}，取值和{total}：'+('命中' if total>=7 else '未中'))
 if total<7:return
 blade=forge=0
 if a=='P' and pool['刃']:use('刃');blade=1
 blood=v['b'];v['b']=0
 if t=='P' and pool['铸']:use('铸');forge=1
 extra=blood+(1 if total>=12 else 0)+(1 if v['down'] else 0)
 ds,val=roll(extra);mod=blade-forge-(1 if t=='P' else 0);result=val+mod
 if result>=9:v['out']=True;outcome='退场'
 elif result>=7:
  v['b']+=2 if v['down'] else 1;v['down']=True;outcome='倒地'
 elif result>=2:v['b']+=1;outcome='轻伤'
 else:outcome='无效'
 log(f'造伤骰{ds}，取最高两骰={val}；暴露血印消耗{blood}，刃+{blade}、铸-{forge}、护甲-{1 if t=="P" else 0}，最终{result}→{outcome}；{t}血印{v["b"]}')
 if t=='P' and not v['out'] and v['b'] and pool['心']:
  use('心');v['b']-=1;log('行动结算后P耗心1清除血印1；倒地状态不撤销')
def move(n,p):old=units[n]['pos'];units[n]['pos']=p;log(f'{n}位置{old}→{p}')
for turn in range(1,13):
 log(f'===第{turn}轮===')
 for u in units.values():u['react']=1
 p=units['P'];ready=False
 if p['out']:break
 if pool['杯'] and spent['铸']:
  use('杯');pool['铸']+=1;spent['铸']-=1;log('P激活开始：杯1恢复已耗铸1')
 if p['down']:p['down']=False;log('P激活起身；本次不移动')
 if turn==1:ready=True;log('P保留攻击准备速攻：C进入近战范围时攻击')
 else:
  alive=[n for n in 'ABCDE' if not units[n]['out']]
  if not alive:break
  t=min(alive,key=lambda n:abs(units[n]['pos']-p['pos']))
  if abs(units[t]['pos']-p['pos'])>1:move('P',max(p['pos'],units[t]['pos']-1))
  attack('P',t)
 for n in 'ABCDE':
  if p['out']:break
  u=units[n]
  if u['out']:continue
  if u['down']:u['down']=False;log(f'{n}激活起身')
  if n=='A' and turn==1:
   log('A宣告撤退，触发P借机；P放弃，保留速攻反应');move(n,4);continue
  if n in 'ABC':
   if abs(u['pos']-p['pos'])>1:move(n,p['pos']+1)
   if n=='C' and ready and p['react']:
    p['react']=0;ready=False;log('P速攻触发，反应1→0');attack('P',n,'速攻')
    if u['out'] or u['down']:continue
   attack(n,'P')
  else:attack(n,'P','射击')
 states.append({'轮':turn,'单位':json.loads(json.dumps(units)),'可用虚相':dict(pool),'耗用虚相':dict(spent)})
 if p['out'] or all(units[n]['out'] for n in 'ABCDE'):break
print('SEED',seed)
print('\n'.join(events))
print('STATES',json.dumps(states,ensure_ascii=False))
