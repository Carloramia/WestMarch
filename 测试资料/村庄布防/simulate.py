"""Bounded prototype: private observations -> four decision families -> navigation -> adjudication.
All combat values are illustrative. No HP; hit and injury are separate temporary checks.
"""
from dataclasses import dataclass,asdict,field as dataclass_field
from collections import deque,Counter
from functools import lru_cache
from itertools import zip_longest
from pathlib import Path
import math,json,random,heapq,hashlib,copy,csv
ROOT=Path(__file__).resolve().parent
WIDTH,HEIGHT=32,24
REGION_SIZE=(44,34)
# Include the region marker in navigation cache keys so the two map sizes stay isolated.
REGION_MARKER=tuple(-n for n in REGION_SIZE)
STOCK=(26,8)
GATES=((14,6),(14,17))
BLOCKED={(14,y) for y in range(HEIGHT) if y not in (6,7,17,18)}
BUILDINGS=[(18,2,22,5),(19,11,22,15),(25,12,29,15),(18,19,23,22)]
for x0,y0,x1,y1 in BUILDINGS:
 BLOCKED.update((x,y) for x in range(x0,x1+1) for y in range(y0,y1+1))
CFG={
 'guard':{'label':'守卫','sight':7,'reach':1.5,'hit':.62,'injury':.60},
 'archer':{'label':'射手','sight':9,'reach':6.2,'hit':.59,'injury':.60},
 'scout':{'label':'斥候','sight':11,'reach':1.5,'hit':.56,'injury':.53},
 'medic':{'label':'救护者','sight':7,'reach':1.5,'hit':.42,'injury':.43},
}
SKILLS = {
 'guard': {'label':'守卫', 'hint':'迎击岗位或队友附近的可见敌人；没有威胁时让下一项技能接手。'},
 'scout': {'label':'斥候', 'hint':'视野至少达到斥候预设，较其他观察者优先报点；无接触时核实敌情或巡视。'},
 'medic': {'label':'医疗', 'hint':'周围安全、有救护次数且冷却结束时，靠近伤员并治疗。'},
 'archer': {'label':'射手', 'hint':'远程攻击可见目标；敌人贴身时尝试拉开距离。近战装备会停用此技能。'},
}
PROFILES={
 'neither':{'label':'双方无初始敌情','D':False,'A':False},
 'defender':{'label':'仅守方获得预警','D':True,'A':False},
 'attacker':{'label':'仅攻方完成侦察','D':False,'A':True},
 'both':{'label':'双方均有初始敌情','D':True,'A':True},
}
INIT_D=[('guard',(16,6)),('guard',(25,17)),('archer',(20,8)),('archer',(24,10)),('scout',(17,16)),('medic',(27,17))]
INIT_A=[('guard',(3,5)),('guard',(3,7)),('archer',(2,6)),('archer',(3,17)),('scout',(3,19)),('medic',(1,17))]
def dist(a,b):return math.dist(a,b)
def walk(p,blocked=None):
 if blocked is None:blocked=BLOCKED
 w,h=REGION_SIZE if REGION_MARKER in blocked else (WIDTH,HEIGHT)
 return 0<=p[0]<w and 0<=p[1]<h and tuple(p) not in blocked
def neighbors(p,blocked=None):return [(p[0]+dx,p[1]+dy) for dx,dy in ((1,0),(-1,0),(0,1),(0,-1)) if walk((p[0]+dx,p[1]+dy),blocked)]
def los(a,b,blocked=None):
 n=max(1,math.ceil(dist(a,b)*5))
 return all((round(a[0]+(b[0]-a[0])*i/n),round(a[1]+(b[1]-a[1])*i/n)) not in (BLOCKED if blocked is None else blocked) for i in range(n+1))
@lru_cache(256)
def field(goal,blocked=None):
 goal=tuple(goal);ds={goal:0};q=deque([goal])
 while q:
  a=q.popleft()
  for b in neighbors(a,blocked):
   if b not in ds:ds[b]=ds[a]+1;q.append(b)
 return ds
def move_step(start,goal,occupied,blocked=None):
 goal=tuple(goal)
 if not walk(goal,blocked):
  options=[p for p in field(tuple(start),blocked) if walk(p,blocked)]
  goal=min(options,key=lambda p:dist(p,goal))
 ds=field(goal,blocked)
 options=[p for p in neighbors(start,blocked) if p not in occupied]
 if not options:return start
 best=min(options,key=lambda p:ds.get(p,999))
 if ds.get(best,999)<ds.get(start,999):return best
 # Occupied choke: local A* rather than walking through allied/enemy markers.
 todo=[(0,start)];prev={};cost={start:0}
 while todo:
  _,u=heapq.heappop(todo)
  if u==goal:
   while prev.get(u)!=start and u in prev:u=prev[u]
   return u if u not in occupied else start
  for v in neighbors(u,blocked):
   if v in occupied:continue
   nc=cost[u]+1
   if nc<cost.get(v,999):cost[v]=nc;prev[v]=u;heapq.heappush(todo,(nc+ds.get(v,999),v))
 return start
@dataclass
class Unit:
 id:str
 team:str
 kind:str
 pos:tuple
 wound:int=0
 treatments:int=2
 cooldown:int=0
 cargo:bool=False
 logic:str='守点/推进'
 reason:str='开局部署'
 action:str='hold'
 heading:float=0
 name:str=''
 armor:bool=False
 weapon:str='default'
 banner:bool=False
 morale_threshold:float=5
 routed:bool=False
 escaped:bool=False
 motion:list=dataclass_field(default_factory=list)
 skills:tuple|None=None
 current_skill:str|None=None
 may_reinforce:bool=False
 response_range:float=10
 mission:str='hold'
 training:int=2
 loyalty_threshold:int=0
 accepts_orders:bool=True
 order_note:str=''
 skill_rules:dict=dataclass_field(default_factory=dict)
 rotation_reserve:bool=False
 fatigue:int=0
 rest_steps:int=0
 vigor_until:int=0
 veteran:int=0
 @property
 def active(self):return self.wound<2 and not self.escaped
 def public(self):return {'id':self.id,'team':self.team,'kind':self.kind,'pos':list(self.pos),'wound':self.wound,'cargo':self.cargo,'active':self.active,'name':self.name or self.id,'armor':self.armor,'weapon':self.weapon,'banner':self.banner,'morale_threshold':self.morale_threshold,'routed':self.routed,'escaped':self.escaped}
def intent(family,action,reason,goal=None,target=None):return {'logic':family,'action':action,'reason':reason,'goal':list(goal) if goal is not None else None,'target':target}
def inside_fort(pos,bounds):
 left,top,right,bottom=bounds
 return left<pos[0]<right and top<pos[1]<bottom

def offset_gate(gate,inward,depth,lateral=0):
 dx,dy=inward
 return (gate[0]+dx*depth-dy*lateral,gate[1]+dy*depth+dx*lateral)

def pick_entry(q,intel,gates=GATES):
 return min(gates or [STOCK],key=lambda g:dist(q,g)+dist(g,STOCK)+sum(max(0,10-dist(e['pos'],g))*2.6 for e in intel))
def skill_action(skill, obs, allies, visible):
 """Return an eligible action or let the next skill try."""
 me = obs['self']
 q = tuple(me['pos'])
 home = obs['orders']['home']
 reach = obs['reach']
 terrain = obs['terrain']
 occupied = {tuple(u['pos']) for u in allies + visible if u['active']}
 occupied.discard(q)
 preference=me.get('skill_rules',{}).get(skill,{}).get('target','default')
 def target_key(target):
  if preference=='nearest':return (0,dist(q,target['pos']))
  if preference=='wounded':return (target['wound']!=1,dist(q,target['pos']))
  return (not target['cargo'],dist(q,target['pos']))
 if skill == 'medic':
  if not me['treatments'] or me['cooldown'] or any(dist(q,e['pos']) <= 3.1 for e in visible):
   return None
  patients = [u for u in allies if u['wound'] == 1]
  for patient in sorted(patients,key=lambda u:dist(q,u['pos'])):
   target = tuple(patient['pos'])
   if dist(q,target) <= 1.5:
    return intent('保全/支援','heal','安全且救护可用，治疗队友',target,patient['id'])
   approaches = [p for p in neighbors(target,terrain) if p not in occupied]
   reachable = [(field(p,terrain).get(q), p) for p in approaches]
   reachable = [(length,p) for length,p in reachable if length is not None]
   if reachable:
    return intent('保全/支援','move','接近可达的伤员',min(reachable)[1],patient['id'])
 elif skill == 'guard':
  assignment=obs.get('reinforcement')
  if assignment:
   protected=[assignment['goal']]
  elif me.get('fixed_watch'):
   protected=[home]
  else:
   protected=[home]+[u['pos'] for u in allies]
  threats = [e for e in visible if min(dist(e['pos'],p) for p in protected) <= 4]
  if obs.get('fort_bounds'):
   threats=[e for e in threats if inside_fort(e['pos'],obs['fort_bounds']) or dist(q,e['pos'])<=1.5]
  threats.sort(key=target_key)
  for enemy in threats:
   if dist(q,enemy['pos']) <= min(1.5,reach):
    return intent('交战/截击','attack','近身迎击岗位或队友附近的敌人',target=enemy['id'])
  for enemy in threats:
   if q in field(tuple(enemy['pos']),terrain):
    return intent('交战/截击','move','前往截击岗位或队友附近的敌人',enemy['pos'],enemy['id'])
 elif skill == 'archer' and reach > 2 and visible:
  current_gap = min(dist(q,e['pos']) for e in visible)
  if current_gap < 2.2 and (not obs.get('at_slit') or any(inside_fort(e['pos'],obs['fort_bounds']) and dist(q,e['pos'])<2.2 for e in visible)):
   safer = [p for p in neighbors(q,terrain) if p not in occupied and min(dist(p,e['pos']) for e in visible)>current_gap]
   if safer:
    return intent('保全/支援','move','敌人贴身，拉开距离',max(safer,key=lambda p:min(dist(p,e['pos']) for e in visible)))
  target = min((e for e in visible if dist(q,e['pos']) <= reach),key=target_key,default=None)
  if target:
   return intent('交战/截击','attack','向射程内的可见目标射击',target=target['id'])
 elif skill == 'scout' and not visible:
  reports = [e for e in obs['intel'] if e['active'] and 0 <= obs['round']-e['seen_at'] <= 8]
  reachable = field(q,terrain)
  for report in sorted(reports,key=lambda e:dist(q,e['pos'])):
   target = tuple(report['pos'])
   if target in reachable and dist(q,target)>1:
    return intent('侦察/验证','move','前往核实尚未目击的敌情',target,report['id'])
  if not reports and me['team']=='D' and obs['gates']:
   gate = obs['gates'][(obs['round']//9)%len(obs['gates'])]
   target = offset_gate(gate,obs.get('gate_inward',{}).get(gate,(1,0)),2)
   if target in reachable and dist(q,target)>1:
    return intent('侦察/验证','move','没有接触，巡视预定入口',target)
 return None

def choose_skills(obs):
 me = obs['self']
 q = me['pos']
 allies = [u for u in obs['allies'] if u['id']!=me['id'] and u['active'] and not u.get('routed')]
 visible = [u for u in obs['visible'] if u['active']]
 for skill in me['skills']:
  condition=me.get('skill_rules',{}).get(skill,{}).get('condition','always')
  if condition=='safe' and any(dist(q,e['pos'])<=3.1 for e in visible):
   continue
  if condition=='wounded' and not any(a['wound']==1 for a in allies):
   continue
  if condition=='alert' and not obs.get('reinforcement'):
   continue
  order = skill_action(skill,obs,allies,visible)
  if order and (not obs.get('rally') or order['action'] in ('attack','heal')):
   return {**order,'skill':skill}
  assignment = obs.get('reinforcement')
  if assignment and skill == assignment['role']:
   goal = assignment['goal']
   entrance=assignment.get('gate_name',f"第{assignment['gate'][1]+1}行入口")
   post = '粮仓旁的岗位' if assignment.get('mission')=='stock' else '门内拦截位' if skill=='guard' else '门后射击位'
   return {**intent('保全/支援','hold' if list(q)==goal else 'move',
                    f"收到{assignment['source']}的报告，前往或守住{entrance}的{post}",goal),'skill':skill}
 if me.get('basic_defense'):
  target=min((e for e in visible if dist(q,e['pos'])<=1.5),key=lambda e:dist(q,e['pos']),default=None)
  if target:
   return intent('交战/截击','attack','基础自卫：近身反击',target=target['id'])
  assignment=obs.get('reinforcement')
  if assignment and assignment.get('called'):
   goal=assignment['goal']
   return intent('保全/支援','hold' if q==goal else 'move','响应斥候呼援，前往或守住战位',goal)
 if me['team']=='A':
  # Shared scenario objectives stay available to any loadout.
  rally = obs.get('rally')
  if rally:
   return intent('守点/推进','hold' if dist(q,rally)<=2 else 'move','在集合点等待队友就位',rally)
  order = choose_legacy(obs, objectives_only=True)
  if order:
   return order
 home = obs['orders']['home']
 return intent('守点/推进','move' if dist(q,home)>1 else 'hold','没有可用技能，返回或留在部署点',home)

def choose(obs):
 if obs['self'].get('skills') is None:
  return choose_legacy(obs)
 shared = choose_legacy(obs, survival_only=True)
 if shared:return shared
 assignment=obs.get('reinforcement')
 if assignment and assignment.get('manual'):
  q=obs['self']['pos']
  legal=[e for e in obs['visible'] if e['active'] and dist(q,e['pos'])<=(obs['reach'] if q==assignment['goal'] and assignment['role']=='archer' else 1.5)]
  if legal:
   return intent('交战/截击','attack','执行传令时处理当前目标',target=min(legal,key=lambda e:dist(q,e['pos']))['id'])
  return intent('保全/支援','hold' if q==assignment['goal'] else 'move','执行传令，前往或守住指定战位',assignment['goal'])
 rotation=obs.get('rotation')
 if rotation and (rotation['state']!='休整' or not any(e['active'] and dist(e['pos'],obs['self']['pos'])<=1.5 for e in obs['visible'])):
  goal=rotation['goal']
  return intent('保全/支援','hold' if goal==obs['self']['pos'] else 'move',rotation['state'],goal)
 return choose_skills(obs)

def choose_legacy(obs,survival_only=False,objectives_only=False):
 """Pure policy: receives observation only, never the authoritative enemy list."""
 me=obs['self'];q=me['pos'];kind=me['kind'];team=me['team'];round_=obs['round']
 stats=obs.get('stats',CFG);reach=obs.get('reach',stats[kind]['reach']);terrain=obs.get('terrain');gates=obs.get('gates',GATES)
 allies=obs['allies'];visible=[e for e in obs['visible'] if e['active']]
 intel=[e for e in obs['intel'] if e['active'] and round_-e['seen_at']<=8]
 near=[e for e in visible if dist(q,e['pos'])<=3.1]
 wounded=[a for a in allies if a['active'] and a['wound']==1 and a['id']!=me['id']]
 if me.get('routed'):return intent('保全/支援','move','士气崩溃，逃离战场',obs['orders']['escape'])
 carrying=next((a for a in allies if a['active'] and a['cargo']),None)
 if team=='A' and (me['cargo'] or (not carrying and sum(not a['active'] for a in allies)>=math.ceil(len(allies)*2/3))):
  return intent('保全/支援','move','携粮撤离' if me['cargo'] else '损失过大，停止袭扰',obs['orders'].get('exit_point',(1,q[1])))
 if survival_only:return None
 if not objectives_only and kind=='medic' and me['treatments']>0 and wounded:
  patient=min(wounded,key=lambda a:dist(q,a['pos']))
  if not near:
   return intent('保全/支援','heal' if dist(q,patient['pos'])<=1.5 else 'move','救护者前往已知伤员',patient['pos'],patient['id'])
 if not objectives_only and me['wound']==1 and near and len(near)>sum(a['active'] and dist(q,a['pos'])<=3.1 for a in allies):
  home=min((a for a in allies if a['active'] and a['kind']=='medic'),key=lambda a:dist(q,a['pos']),default=None)
  return intent('保全/支援','move','受伤且局部人数劣势，向支援点退却',home['pos'] if home else (27,18) if team=='D' else (1,q[1]))
 if not objectives_only and reach>2 and any(dist(q,e['pos'])<2.2 for e in visible):
  cells=[p for p in neighbors(tuple(q),terrain) if p not in {tuple(a['pos']) for a in allies if a['active']}]
  if cells:return intent('保全/支援','move','射手脱离贴身威胁',max(cells,key=lambda p:min(dist(p,e['pos']) for e in visible)))
 # A defender with cargo intel intercepts the last known location, never hidden truth.
 if team=='D':visible.sort(key=lambda e:(not e['cargo'],dist(e['pos'],STOCK),dist(q,e['pos'])))
 else:visible.sort(key=lambda e:(e['kind']!='medic',e['wound']!=1,dist(q,e['pos'])))
 valid=[e for e in visible if dist(q,e['pos'])<=reach]
 if valid and not objectives_only:return intent('交战/截击','attack','目视合法目标，按任务威胁优先' if team=='D' else '目视目标，优先脆弱支援者',target=valid[0]['id'])
 if team=='A':
  close=[]
  for g in obs.get('structures',[]):
   if g['hp']<=0:continue
   target=min(g['cells'],key=lambda p:dist(q,p))
   if dist(q,target)<=1.5 and los(q,target,(terrain or frozenset())-frozenset(map(tuple,g['cells']))):close.append((dist(q,target),g,target))
  if close:
   _,g,p=min(close,key=lambda item:item[0]);return intent('交战/截击','siege','破坏挡路城门',p,g['id'])
 if team=='D':
  inside=[e for e in intel if e['pos'][0]>=14 or e['cargo']]
  if inside:
   e=min(inside,key=lambda e:(not e['cargo'],dist(e['pos'],STOCK),dist(q,e['pos'])))
   if kind!='medic':return intent('交战/截击','move','敌人进入村内，向目击/最后目击位置截击',e['pos'],e['id'])
  if kind=='scout':
   if intel:
    gate=max(gates or [STOCK],key=lambda g:sum(1/(2+dist(e['pos'],g)) for e in intel))
    return intent('侦察/验证','move','验证敌情报告对应入口',(16,gate[1]))
   return intent('侦察/验证','move','无敌情，交替检查南北入口',(min(31,gates[(round_//9)%len(gates)][0]+2),gates[(round_//9)%len(gates)][1]) if gates else q)
  if kind=='guard':
   if obs['orders']['station']:anchor=tuple(obs['orders']['home'])
   elif intel:
    gate=max(gates or [STOCK],key=lambda g:sum(1/(2+dist(e['pos'],g)) for e in intel));anchor=(16,gate[1])
   else:anchor=tuple(obs['orders']['reserve'])
   # Keep the first guard on station; others become reserves under reports.
   if visible and not obs['orders']['station']:return intent('交战/截击','move','预备守卫前往可见接触点',visible[0]['pos'],visible[0]['id'])
   return intent('守点/推进','move' if dist(q,anchor)>1 else 'hold','按警戒区守点，未获敌情不出村追逐',anchor)
  anchor=tuple(obs['orders']['home'])
  return intent('守点/推进','move' if dist(q,anchor)>1 else 'hold','维持射击/救护支援位',anchor)
 if carrying:return intent('保全/支援','move','掩护己方携粮者撤离',carrying['pos'])
 if not objectives_only and visible and kind!='medic' and (q[0]>=15 or dist(q,visible[0]['pos'])<3.2):return intent('交战/截击','move','接触威胁已阻碍当前路线，接近目视目标',visible[0]['pos'],visible[0]['id'])
 if dist(q,obs['loot'])<=1.5:return intent('守点/推进','loot','抵达物资点，尝试夺取补给',obs['loot'])
 # Route danger uses known enemy positions only. Both teams know public terrain.
 gate=tuple(obs['orders']['entry'])
 if not gates:return intent('守点/推进','move','墙体无入口，尝试可达路线',obs['loot'])
 direction=obs['orders'].get('entry_side')
 if direction and not inside_fort(q,obs['fort_bounds']):
  outside=offset_gate(gate,direction,-1)
  inner=offset_gate(gate,direction,1)
  relative=(q[0]-gate[0])*direction[0]+(q[1]-gate[1])*direction[1]
  goal=outside if relative<0 and tuple(q)!=outside else inner
  return intent('守点/推进','move','沿选定城门进入堡内',goal)
 if not direction and q[0]<15:
  outside=(13,gate[1]);goal=outside if q[0]<=13 and tuple(q)!=outside else (15,gate[1])
  return intent('侦察/验证' if kind=='scout' else '守点/推进','move','执行已选入口路线，先到墙外接近点',goal)
 if kind=='medic' and not objectives_only:
  front=min((a for a in allies if a['active'] and a['kind']=='guard'),key=lambda a:dist(q,a['pos']),default=me)
  return intent('保全/支援','move' if dist(q,front['pos'])>3 else 'hold','保持支援距离',front['pos'])
 return intent('守点/推进','move','尚无接触，继续执行夺粮目标',obs['loot'])

def validate_scenario(s, regional=False):
 if not isinstance(s,dict) or not isinstance(s.get('units'),list) or not 2<=len(s['units'])<=32:raise ValueError('总棋子数须为2至32，双方至少各一枚')
 terrain=s.get('terrain',{})
 if not isinstance(terrain,dict):raise ValueError('地形格式错误')
 w,h=REGION_SIZE if regional else (WIDTH,HEIGHT)
 for name in ('blocked','cover','rough'):
  cells=terrain.get(name,[])
  if not isinstance(cells,list) or len(cells)>w*h or any(not isinstance(p,list) or len(p)!=2 or any(type(v)!=int for v in p) or not (0<=p[0]<w and 0<=p[1]<h) for p in cells):raise ValueError('地形坐标无效')
 blocked=frozenset(map(tuple,terrain.get('blocked',BLOCKED)))
 if regional:blocked=blocked|{REGION_MARKER}
 if STOCK in blocked or any((1,y) in blocked for y in range(24)):raise ValueError('粮仓与西侧撤离列须保持可通行')
 for kind,values in s.get('stats',{}).items():
  if kind not in CFG or not isinstance(values,dict):raise ValueError('兵种参数无效')
  for key,value in values.items():
   bounds={'sight':(1,20),'reach':(1,15),'hit':(0,1),'injury':(0,1),'speed':(1,3),'treatments':(0,10)}
   if key not in bounds or type(value) not in (int,float) or not math.isfinite(value) or not bounds[key][0]<=value<=bounds[key][1] or (key in ('speed','treatments') and int(value)!=value):raise ValueError('兵种数值超出允许范围')
 authority=s.get('authority',{'D':2,'A':2})
 if not isinstance(authority,dict) or any(type(authority.get(t)) is not int or not 0<=authority[t]<=3 for t in ('D','A')):
  raise ValueError('双方威信须为0至3')
 minimum=s.get('minimum_watch',1)
 if type(minimum) is not int or not 0<=minimum<=3:raise ValueError('最低留守须为0至3')
 rally=s.get('rally')
 if rally is not None and (not isinstance(rally,list) or len(rally)!=2 or any(type(v) is not int for v in rally) or not walk(rally,blocked) or rally[0]>=14):
  raise ValueError('集结点须为城外可通行格')
 if type(s.get('alarm_bell',False)) is not bool:raise ValueError('警钟设置必须是开关')
 gate_cells=set();gate_ids=set()
 gates=s.get('gates',[])
 if not isinstance(gates,list) or len(gates)>32:raise ValueError('城门最多32座')
 for gate in gates:
  if not isinstance(gate,dict) or not isinstance(gate.get('id'),str) or not gate['id'].isascii() or not gate['id'].isalnum() or gate['id'] in gate_ids:raise ValueError('城门编号无效')
  hp=gate.get('hp',20);cells=gate.get('cells')
  if type(hp) not in (int,float) or not math.isfinite(hp) or not 1<=hp<=500 or not isinstance(cells,list) or not 1<=len(cells)<=4:raise ValueError('城门血量须为1至500，每门最多4格')
  for p in cells:
   if not isinstance(p,list) or len(p)!=2 or any(type(v)!=int for v in p) or not walk(p,blocked) or tuple(p) in gate_cells or tuple(p)==STOCK or p[0]==1:raise ValueError('城门位置无效或重叠')
   gate_cells.add(tuple(p))
  gate_ids.add(gate['id'])
 morale=s.get('morale',{})
 if not isinstance(morale,dict):raise ValueError('士气配置无效')
 for key,lo,hi in [('interval',1,30),('chance',0,1)]:
  value=morale.get(key,5 if key=='interval' else .25)
  if type(value) not in (int,float) or not math.isfinite(value) or not lo<=value<=hi or (key=='interval' and int(value)!=value):raise ValueError('溃逃间隔或概率无效')
 ids=set();positions=set();teams=Counter()
 for u in s['units']:
  if not isinstance(u,dict):raise ValueError('棋子格式错误')
  ident=u.get('id');p=u.get('pos')
  if not isinstance(u.get('name',''),str) or len(u.get('name',''))>16:raise ValueError('名字最多16字')
  skills=u.get('skills')
  if skills is not None and (not isinstance(skills,list) or len(skills)>len(SKILLS) or any(not isinstance(x,str) or x not in SKILLS for x in skills) or len(set(skills))!=len(skills)):
   raise ValueError('技能列表无效或含重复技能')
  if type(u.get('may_reinforce',False)) is not bool:raise ValueError('回援设置必须是开关')
  response=u.get('response_range',10)
  if type(response) not in (int,float) or not 0<=response<=32:raise ValueError('响应范围须为0至32格')
  if u.get('mission','hold') not in ('hold','reserve','stock'):raise ValueError('无效预案')
  for key,cap,default in [('training',2,2),('loyalty_threshold',3,0)]:
   value=u.get(key,default)
   if type(value) is not int or not 0<=value<=cap:raise ValueError('训练或威信要求超出范围')
  rules=u.get('skill_rules',{})
  if not isinstance(rules,dict) or any(key not in SKILLS or not isinstance(rule,dict)
       or rule.get('condition','always') not in ('always','safe','wounded','alert')
       or rule.get('target','default') not in ('default','nearest','wounded') for key,rule in rules.items()):
   raise ValueError('无效技能条件或目标偏好')
  if type(u.get('rotation_reserve',False)) is not bool:raise ValueError('轮换后备必须是开关')
  gear=u.get('equipment',{})
  if not isinstance(gear,dict) or type(gear.get('armor',False))!=bool or type(gear.get('banner',False))!=bool or gear.get('weapon','default') not in ('default','none','melee','ranged','siege'):raise ValueError('装备配置无效')
  threshold=u.get('morale_threshold',5)
  if type(threshold) not in (int,float) or not math.isfinite(threshold) or not 0<=threshold<=10:raise ValueError('士气属性须为0至10')
  if not isinstance(ident,str) or not ident.isascii() or not ident.isalnum() or len(ident)>12 or ident in ids:raise ValueError('棋子编号无效或重复')
  if u.get('team') not in ('D','A') or u.get('kind') not in CFG:raise ValueError('阵营或单位类型无效')
  if not isinstance(p,list) or len(p)!=2 or any(type(v)!=int for v in p) or not walk(p,blocked) or tuple(p) in gate_cells or tuple(p) in positions:raise ValueError('棋子不可重叠或部署在建筑、墙体、地图外')
  ids.add(ident);positions.add(tuple(p));teams[u['team']]+=1
 if not teams['D'] or not teams['A']:raise ValueError('双方至少各保留一枚棋子')
 intel=s.get('intel')
 if not isinstance(intel,dict):raise ValueError('缺少初始情报')
 for team in ('D','A'):
  known=intel.get(team)
  enemies={u['id'] for u in s['units'] if u['team']!=team}
  if not isinstance(known,list) or any(not isinstance(x,str) or x not in enemies for x in known):raise ValueError('情报只能包含敌方棋子编号')

class Battle:
 def __init__(self,profile='neither',seed=7,scenario=None,regional=False):
  self.width,self.height=REGION_SIZE if regional else (WIDTH,HEIGHT)
  self.profile=profile;self.seed=seed;self.round=0;self.memory={'D':{},'A':{}};self.events=[];self.history=[];self.captures=Counter();self.loot_pos=STOCK;self.loot_progress={};self.result=None;self.first_orders={};self.policy_counts=Counter();self.audit_attacks=[];self.blocked_moves=Counter()
  self.units=[Unit(f'{team}{i}',team,k,p) for team,rows in [('D',INIT_D),('A',INIT_A)] for i,(k,p) in enumerate(rows)]
  if scenario is not None:
   validate_scenario(scenario,regional)
   self.units=[Unit(r['id'],r['team'],r['kind'],tuple(r['pos']),name=r.get('name',''),armor=r.get('equipment',{}).get('armor',False),weapon=r.get('equipment',{}).get('weapon','default'),banner=r.get('equipment',{}).get('banner',False),morale_threshold=r.get('morale_threshold',5),skills=tuple(r['skills']) if r.get('skills') is not None else None,may_reinforce=r.get('may_reinforce',False),response_range=r.get('response_range',10),mission=r.get('mission','reserve' if r.get('may_reinforce') else 'hold'),training=r.get('training',2),loyalty_threshold=r.get('loyalty_threshold',0),skill_rules=r.get('skill_rules',{}),rotation_reserve=r.get('rotation_reserve',False)) for r in scenario['units']]
  self.authority=(scenario or {}).get('authority',{'D':2,'A':2})
  self.minimum_watch=(scenario or {}).get('minimum_watch',1)
  self.rally=(scenario or {}).get('rally')
  self.rally_released=False
  for unit in self.units:
   unit.accepts_orders=self.authority[unit.team]>=unit.loyalty_threshold
   if unit.skills is None:
    continue
   if not unit.accepts_orders:
    unit.skills=(unit.kind,)
    unit.order_note='威信不足，沿用起始技能与岗位'
   elif unit.training==0:
    unit.skills=(unit.kind,)
    unit.order_note='训练不足，沿用起始技能'
   elif unit.training==1:
    unit.skills=unit.skills[:2]
    unit.order_note='基础训练，最多执行前两项技能'
  self.morale_config=(scenario or {}).get('morale',{});self.morale_enabled=scenario is not None
  self.blocked=frozenset(map(tuple,scenario.get('terrain',{}).get('blocked',BLOCKED))) if scenario else frozenset(BLOCKED)
  if regional:self.blocked=self.blocked|{REGION_MARKER}
  self.structures=[{**copy.deepcopy(g),'max_hp':g.get('hp',20)} for g in (scenario or {}).get('gates',[])]
  self.base_blocked=self.blocked
  self.blocked=frozenset(set(self.base_blocked)|{tuple(p) for g in self.structures for p in g['cells']})
  self.cover=set(map(tuple,scenario.get('terrain',{}).get('cover',[]))) if scenario else set()
  self.rough=set(map(tuple,scenario.get('terrain',{}).get('rough',[]))) if scenario else set()
  self.stats=copy.deepcopy(CFG)
  for kind in self.stats:self.stats[kind].update((scenario or {}).get('stats',{}).get(kind,{}))
  for u in self.units:u.treatments=int(self.stats[u.kind].get('treatments',2))
  self.gates=tuple((14,y) for y in range(24) if (14,y) not in self.base_blocked and (y==0 or (14,y-1) in self.base_blocked))
  self.gate_metadata={}
  self.slits={}
  self.fort_bounds=None
  self.scout_calls={}
  self.field_order=None
  self.watch_reserves=set()
  self.call_ready={}
  self.byid={u.id:u for u in self.units}
  for team in ('D','A'):
   known=scenario['intel'][team] if scenario is not None else [u.id for u in self.units if u.team!=team and PROFILES[profile][team]]
   for u in self.units:
    if u.id in known:self.memory[team][u.id]={**u.public(),'seen_at':0,'source':'initial_report'}
  self.received={u.id:dict(self.memory[u.team]) for u in self.units}
  self.orders={}
  self.reinforcements={}
  self.alarm_bell=(scenario or {}).get('alarm_bell',False)
  self.alarm_gate=None
  self.call_network={}
  self.rotation_posts=[]
  self.rotation_orders={}
  for u in self.units:
   intel=list(self.received[u.id].values())
   reserve=(16,max(self.gates or [STOCK],key=lambda g:sum(1/(2+dist(e['pos'],g)) for e in intel))[1]) if intel else (25,17)
   if not intel:reserve=u.pos
   station=next((a.id for a in self.units if a.team==u.team and a.kind=='guard'),None)==u.id
   self.orders[u.id]={'entry':list(pick_entry(u.pos,intel,self.gates)),'reserve':list(reserve),'home':list(u.pos),'station':station,'escape':[0 if u.team=='A' else self.width-1,u.pos[1]]}
  self.setup_rotation()

 def setup_rotation(self):
  defenders=[u for u in self.units if u.team=='D' and u.accepts_orders and u.skills and u.mission=='hold']
  available=[u for u in defenders if not u.rotation_reserve]
  for reserve in sorted((u for u in defenders if u.rotation_reserve),key=lambda u:u.id):
   path=field(reserve.pos,self.blocked)
   def compatible(guard):
    return ('guard' in guard.skills and 'guard' in reserve.skills) or (
     'archer' in guard.skills and 'archer' in reserve.skills and min(self.reach(guard),self.reach(reserve))>2)
   candidates=[u for u in available if u.pos in path and compatible(u)]
   if not candidates:
    reserve.order_note='未找到同类、可达的在岗棋子，按原岗位行动'
    continue
   guard=min(candidates,key=lambda u:(path[u.pos],u.id))
   available.remove(guard)
   self.rotation_posts.append({'watch':guard.id,'rest':reserve.id,'post':guard.pos,'camp':reserve.pos,'watch_cell':guard.pos,'relief':None})
   self.rotation_orders[reserve.id]={'state':'休整','goal':list(reserve.pos)}

 def rotation_state(self,u):
  order=self.rotation_orders.get(u.id)
  return order['state'] if order else '在岗' if any(post['watch']==u.id for post in self.rotation_posts) else ''

 def plan_rotation(self):
  self.rotation_orders={}
  occupied={u.pos for u in self.units if u.active}
  for post in self.rotation_posts:
   guard=self.byid[post['watch']]
   reserve=self.byid[post['rest']]
   if not reserve.active or reserve.routed:
    post['relief']=None
    continue
   goal=post['relief']
   if goal and goal in occupied and reserve.pos!=goal:
    post['relief']=None
    goal=None
   if goal and reserve.pos==goal:
    post['watch'],post['rest']=reserve.id,guard.id
    post['watch_cell']=goal
    post['relief']=None
    reserve.vigor_until=self.round+4
    reserve.rest_steps=0
    guard.rest_steps=0
    self.record('rotation',f'{reserve.name or reserve.id}接岗，精力充沛。{guard.name or guard.id}离岗休整',actor=reserve.id,team='D')
    guard,reserve=reserve,guard
    goal=None
   if goal is None and reserve.rest_steps>=3 and (not guard.active or guard.routed or guard.fatigue>=3):
    path=field(reserve.pos,self.blocked)
    reserved={other['relief'] for other in self.rotation_posts if other is not post}
    cells=[post['post'],*neighbors(post['post'],self.blocked)]
    candidates=[p for p in cells if p in path and p not in reserved and (p not in occupied or p==reserve.pos)]
    if candidates:
     goal=min(candidates,key=lambda p:(path[p],p))
     post['relief']=goal
     self.record('rotation',f'{reserve.name or reserve.id}前往接岗，前线交接后才撤下',actor=reserve.id,team='D')
   if reserve.active and not reserve.routed:
    state='接岗中' if goal else '休整' if reserve.pos==post['camp'] else '返回休整'
    self.rotation_orders[reserve.id]={'state':state,'goal':list(goal or post['camp'])}

 def reach(self,u):
  if u.weapon in ('melee','none','siege'):
   return 1.5
  if u.weapon=='ranged':
   return max(6.2,self.stats[u.kind]['reach'])
  if u.skills is not None and 'archer' in u.skills:
   return self.stats['archer']['reach']
  return self.stats[u.kind]['reach']
 def morale(self,team):
  own=[u for u in self.units if u.team==team];alive=sum(u.active for u in own);leaders=sum(u.active and not u.routed and u.banner for u in own)
  base=alive/len(own)*10 if own else 0
  return {'alive':alive,'total':len(own),'base':round(base,3),'leaders':leaders,'bonus':4 if leaders else 0,'current':round(min(10,base+(4 if leaders else 0)),3)}
 def check_morale(self):
  if not self.morale_enabled or self.round%int(self.morale_config.get('interval',5)):return
  scores={team:self.morale(team)['current'] for team in ('D','A')}
  for u in self.units:
   if u.active and not u.routed and scores[u.team]<u.morale_threshold and self.rand(u,'morale')<self.morale_config.get('chance',.25):
    u.routed=True;u.logic='保全/支援';u.reason='士气崩溃，逃离战场';u.action='move'
    self.record('rout',f'{u.name or u.id}溃逃（本方士气{scores[u.team]:.1f}＜属性{u.morale_threshold:g}）',actor=u.id)
    if u.cargo:u.cargo=False;self.loot_pos=u.pos;self.record('drop',f'{u.name or u.id}丢弃补给',actor=u.id)
 def rally_goal(self,u):
  if u.team=='A' and u.accepts_orders and u.skills is not None and not self.rally_released:
   return self.rally
  return None

 def update_rally(self):
  if not self.rally or self.rally_released:
   return
  squad=[u for u in self.units if u.active and not u.routed and self.rally_goal(u)]
  ready=[u for u in squad if dist(u.pos,self.rally)<=2]
  siege=[u for u in squad if u.weapon=='siege']
  quorum=bool(squad) and len(ready)>=min(2,len(squad)) and (not siege or any(u in ready for u in siege))
  if quorum or self.round>=12:
   self.rally_released=True
   if self.gates:
    entry=min(self.gates,key=lambda gate:(dist(self.rally,gate),gate))
    for unit in squad:
     self.orders[unit.id]['entry']=list(entry)
   self.record('reinforce','集结完成，开始推进' if quorum else '集结超时，按原目标推进',team='A')

 def relay_intel(self):
  """Forward actual contact data one hop using the previous step's inboxes."""
  active = [u for u in self.units if u.active and not u.routed]
  current = {uid:{key:report for key,report in reports.items()
                  if self.round-report['seen_at']<=8}
             for uid,reports in self.received.items()}
  for unit in active:
   reports = dict(current[unit.id])
   for ally in active:
    if ally.team!=unit.team or ally.id==unit.id or not unit.response_range or dist(unit.pos,ally.pos)>unit.response_range:
     continue
    for enemy,report in current[ally.id].items():
     old=reports.get(enemy)
     if old is None or (report['seen_at'],bool(report.get('scout_report'))) > (old['seen_at'],bool(old.get('scout_report'))):
      reports[enemy]=report
   self.received[unit.id]=reports

 def gate_name(self,gate):
  return self.gate_metadata.get(tuple(gate),{}).get('name',f'第{gate[1]+1}行入口')

 def gate_inward(self,gate):
  return self.gate_metadata.get(tuple(gate),{}).get('inward',(1,0))

 def can_see(self,u,target):
  if los(u.pos,target,self.blocked):
   return True
  slit=self.slits.get(u.pos)
  if not slit or u.team!='D' or 'archer' not in (u.skills or ()) or self.reach(u)<=2:
   return False
  wall=slit['wall']
  dx,dy=slit['inward']
  tx,ty=target[0]-wall[0],target[1]-wall[1]
  outward=-(tx*dx+ty*dy)
  lateral=abs(tx*dy-ty*dx)
  return outward>0 and lateral<=outward and los(u.pos,target,self.blocked-{tuple(wall)})

 def relay_call(self, gate, reports, defenders):
  """Each step forwards the call one hop through active defenders."""
  callers = self.call_network.get(gate,set()) & defenders.keys()
  callers |= {r['source'] for r in reports if r['source'] in defenders}
  initial = any(r['source']=='initial_report' for r in reports)
  # Initial intelligence is treated as a call originating at the threatened gate.
  origins = [defenders[uid].pos for uid in callers] + ([gate] if initial else [])
  reached = callers | {
   uid for uid,u in defenders.items()
   if u.response_range > 0 and any(dist(u.pos,origin)<=u.response_range for origin in origins)
  }
  for uid in sorted(reached-callers):
   self.record('reinforce',f'{uid}收到{self.gate_name(gate)}呼援，将在下一步转报',actor=uid,team='D')
  return reached

 def broadcast_scout_calls(self,defenders):
  self.scout_calls={uid:order for uid,order in self.scout_calls.items()
                    if uid in defenders and self.round<=order['until']}
  if self.profile!='campaign':
   return
  for scout in defenders.values():
   if 'scout' not in (scout.skills or ()):
    continue
   fresh=[report for report in self.received[scout.id].values() if report['active'] and not report.get('routed')
          and 0<=self.round-report['seen_at']<=1]
   if not fresh:
    continue
   report=min(fresh,key=lambda report:(report['source']!=scout.id,dist(scout.pos,report['pos']),report['id']))
   gate=min(self.gates,key=lambda point:dist(point,report['pos']))
   if self.round<self.call_ready.get((scout.id,gate),0):
    continue
   self.call_ready[(scout.id,gate)]=self.round+8
   radius=10
   heard=[u for u in defenders.values() if dist(u.pos,scout.pos)<=radius]
   for unit in heard:
    self.scout_calls[unit.id]={'gate':gate,'until':self.round+7}
    old=self.received[unit.id].get(report['id'])
    if old is None or old['seen_at']<report['seen_at']:
     self.received[unit.id][report['id']]=report
   self.record('scout_call',f'{scout.name or scout.id}呼援：{self.gate_name(gate)}，{len(heard)} 人听到',
               actor=scout.id,team='D',pos=list(scout.pos),radius=radius)

 def operate_fortifications(self):
  if not self.fort_bounds:
   return
  left,top,right,bottom=self.fort_bounds
  outer=frozenset(p for p in self.blocked if left<=p[0]<=right and top<=p[1]<=bottom
                  and (p[0] in (left,right) or p[1] in (top,bottom)))
  for gate in self.structures:
   if not gate.get('upgrades'):
    continue
   point=tuple(gate['cells'][0])
   inward=gate['inward']
   operator=any(u.team=='D' and u.active and not u.routed
                and inside_fort(u.pos,self.fort_bounds) and dist(u.pos,point)<=2.25 for u in self.units)
   ballista='ballista' in gate['upgrades'] and operator
   tower='tower' in gate['upgrades']
   if not tower and not ballista:
    continue
   for enemy in self.units:
    if enemy.team!='A' or not enemy.active or inside_fort(enemy.pos,self.fort_bounds):
     continue
    outward=-sum((enemy.pos[i]-point[i])*inward[i] for i in (0,1))
    if outward<=0:
     continue
    distance=dist(point,enemy.pos)
    tower_sees=tower and distance<=12 and los(point,enemy.pos,self.blocked-outer)
    can_fire=ballista and distance<=8 and los(point,enemy.pos,self.blocked-frozenset(map(tuple,gate['cells'])))
    if not (tower_sees or can_fire):
     continue
    report={**enemy.public(),'seen_at':self.round,'source':gate['name']+('瞭望塔' if tower_sees else '弩炮')}
    old=self.memory['D'].get(enemy.id)
    if not old or old['seen_at']<self.round:
     self.memory['D'][enemy.id]=report
    for unit in self.units:
     if unit.team=='D' and unit.active and dist(unit.pos,point)<=unit.response_range:
      self.received[unit.id][enemy.id]=report
    if can_fire and self.round>=gate.get('next_shot',0):
     gate['next_shot']=self.round+3
     hit=random.Random(f'{self.seed}|{self.round}|{gate["id"]}|ballista').random()<.65
     if hit:
      enemy.wound+=1
      if not enemy.active and enemy.cargo:
       enemy.cargo=False
       self.loot_pos=enemy.pos
     self.record('ballista',f'{gate["name"]}弩炮'+('命中' if hit else '落空'),target=enemy.id,
                 team='D',pos=list(point),target_pos=list(enemy.pos),hit=hit)

 def can_take_field_order(self,u):
  return (u.team=='D' and u.active and not u.routed and u.accepts_orders and u.mission=='reserve'
          and u.id not in self.watch_reserves
          and self.rotation_state(u) not in ('休整','返回休整','接岗中'))

 def field_positions(self,u,gate,occupied):
  inward=self.gate_inward(gate)
  archer='archer' in (u.skills or ()) and self.reach(u)>2
  positions=[offset_gate(gate,inward,depth,lateral) for depth in range(1,6) for lateral in range(-4,5)]
  route=field(u.pos,self.blocked)
  target=offset_gate(gate,inward,3 if archer else 1)
  legal=[p for p in positions if p in route and p not in occupied and inside_fort(p,self.fort_bounds)]
  return min(legal,key=lambda p:(not(archer and p in self.slits and tuple(self.slits[p]['inward'])==tuple(inward)),
                                 dist(p,target),route[p],p),default=None)

 def issue_field_order(self,gate_id):
  if self.profile!='campaign' or self.result or not self.round:
   raise ValueError('战斗开始后才能传令')
  if self.field_order is not None:
   raise ValueError('本场的传令机会已经用完')
  gate=next((g for g in self.gate_metadata if self.gate_metadata[g]['id']==gate_id),None)
  if gate is None:
   raise ValueError('请选择本关城门')
  candidates=[u for u in self.units if self.can_take_field_order(u)]
  candidates.sort(key=lambda u:(field(u.pos,self.blocked).get(offset_gate(gate,self.gate_inward(gate),1),1000),u.id))
  posts={}
  occupied={u.pos for u in self.units if u.team=='D' and u.active}
  for unit in candidates:
   unavailable=(occupied-{unit.pos})|set(posts.values())
   goal=self.field_positions(unit,gate,unavailable)
   if goal:
    posts[unit.id]=goal
   if len(posts)==2:
    break
  if not posts:
   raise ValueError('没有可到达战位的机动守军。本次未消耗传令')
  self.field_order={'gate':gate,'posts':posts,'starts':self.round+1,'ends':self.round+8}
  return {'gate':self.gate_name(gate),'count':len(posts),'starts':self.round+1}

 def apply_field_orders(self,assignments):
  order=self.field_order
  if not order or not order['starts']<=self.round<=order['ends']:
   return
  gate=order['gate']
  if self.round==order['starts']:
   self.record('field_order',f'传令：{len(order["posts"])} 名机动守军调往{self.gate_name(gate)}，命令有效 8 步',team='D')
  recipients={uid:goal for uid,goal in order['posts'].items() if self.can_take_field_order(self.byid[uid])}
  goals=set(recipients.values())
  for uid,assignment in list(assignments.items()):
   if uid in recipients or tuple(assignment['goal']) in goals:
    del assignments[uid]
  for uid,goal in recipients.items():
   unit=self.byid[uid]
   role='archer' if 'archer' in (unit.skills or ()) and self.reach(unit)>2 else 'guard'
   assignments[uid]={'role':role,'goal':list(goal),'gate':list(gate),'source':'传令',
                     'gate_name':self.gate_name(gate),'manual':True}
   if unit.pos==goal and uid not in order.setdefault('arrived',set()):
    order['arrived'].add(uid)
    self.record('order_arrival',f'{unit.name or uid}抵达{self.gate_name(gate)}战位',actor=uid,team='D')

 def plan_reinforcements(self):
  """Respond to shared reports only; never inspect unseen enemy positions."""
  previous = self.reinforcements
  assignments = {}
  defenders = {u.id:u for u in self.units if u.team=='D' and u.active and not u.routed}
  self.broadcast_scout_calls(defenders)
  threats = {}
  for report in self.memory['D'].values():
   if not report['active'] or report.get('routed') or not 0<=self.round-report['seen_at']<=8 or not self.gates:
    continue
   gate = min(self.gates,key=lambda g:dist(g,report['pos']))
   if dist(gate,report['pos'])<=6:
    threats.setdefault(gate,[]).append(report)
  ranked = sorted(threats,key=lambda g:(-len(threats[g]),-max(r['seen_at'] for r in threats[g]),g))
  alarm = ranked[0] if ranked and self.alarm_bell else None
  if alarm != self.alarm_gate:
   message = f'警钟响起，全体守军收到{self.gate_name(alarm)}警报' if alarm else '警钟解除，全军回援结束'
   self.record('reinforce',message,team='D')
  self.alarm_gate = alarm
  self.call_network = {} if alarm else {gate:self.relay_call(gate,threats[gate],defenders) for gate in ranked}
  posts = set()
  licensed = {uid:u for uid,u in defenders.items() if u.accepts_orders and u.skills}
  capable = {uid:u for uid,u in licensed.items() if 'guard' in u.skills or ('archer' in u.skills and self.reach(u)>2)}
  zones = {uid:min(self.gates,key=lambda gate:dist(gate,self.orders[uid]['home'])) for uid in capable if self.gates}
  self.watch_reserves.clear()
  for gate in self.gates:
   local = [u for uid,u in capable.items() if zones[uid]==gate and u.mission!='stock']
   staying = sum(u.mission=='hold' for u in local)
   extra = sorted((u for u in local if u.mission=='reserve'),key=lambda u:(dist(u.pos,gate),u.id))
   for unit in extra[:max(0,self.minimum_watch-staying)]:
    self.watch_reserves.add(unit.id)
    licensed.pop(unit.id,None)
  if alarm:
   for uid,u in sorted(capable.items()):
    if u.mission!='stock':
     continue
    path=field(u.pos,self.blocked)
    candidates=[p for p in neighbors(STOCK,self.blocked) if p in path and p not in posts]
    if not candidates:
     continue
    goal=min(candidates,key=lambda p:(path[p],p))
    posts.add(goal)
    role=next(k for k in u.skills if k=='guard' or (k=='archer' and self.reach(u)>2))
    assignments[uid]={'role':role,'goal':list(goal),'gate':list(alarm),'source':'警钟','mission':'stock','gate_name':self.gate_name(alarm)}
  homes = {uid:tuple(self.orders[uid]['home']) for uid in defenders}
  for index,gate in enumerate(ranked):
   remaining=sum(u.mission=='reserve' and uid in licensed and uid not in assignments for uid,u in capable.items())
   quota=math.ceil(remaining/(len(ranked)-index)) if alarm else remaining
   assigned_here=0
   heard = defenders.keys() if alarm else self.call_network[gate]
   report = max(threats[gate],key=lambda r:(r['seen_at'],bool(r.get('scout_report')),r['id']))
   source = '警钟' if alarm else '开局情报' if report['source']=='initial_report' else report['source']
   inward=self.gate_inward(gate)
   anchor=offset_gate(gate,inward,1)
   def arrival(uid):
    unit=defenders[uid]
    distance=field(unit.pos,self.blocked).get(anchor,1000)
    return (uid not in previous,distance/self.stats[unit.kind].get('speed',1),uid)
   for uid in sorted(heard,key=arrival):
    if assigned_here>=quota:
     break
    u = defenders[uid]
    if uid in assignments or uid not in licensed or u.mission!='reserve':
     continue
    path = field(u.pos,self.blocked)
    occupied_posts = posts | {pos for ally,pos in homes.items() if ally!=uid}
    for role in u.skills:
     if role not in ('guard','archer') or (role=='archer' and self.reach(u)<=2):
      continue
     if role=='guard':
      offsets = [(dx,dy) for dx in range(1,7) for dy in range(-5,6)]
     else:
      offsets = [(dx,dy) for dx in range(1 if self.fort_bounds else 2,9) for dy in range(-6,7)]
     goals = [offset_gate(gate,inward,depth,lateral) for depth,lateral in offsets]
     if self.fort_bounds:goals=[p for p in goals if inside_fort(p,self.fort_bounds)]
     goals = [p for p in goals if p in path and p not in occupied_posts]
     if role=='archer':
      goals = [p for p in goals if dist(p,anchor)<=self.reach(u) and los(p,anchor,self.blocked)]
     if not goals:
      continue
     preferred=offset_gate(gate,inward,1 if role=='guard' else 4)
     slit_goals=[p for p in goals if p in self.slits and tuple(self.slits[p]['inward'])==tuple(inward) and dist(p,gate)<=3]
     if role=='archer' and slit_goals:
      goals=slit_goals
     old = previous.get(uid)
     old_goal = tuple(old['goal']) if old and old['role']==role and old['gate']==list(gate) else None
     goal = min(goals,key=lambda p:(p!=old_goal,dist(p,preferred),path[p],p))
     posts.add(goal)
     assignments[uid] = {'role':role,'goal':list(goal),'gate':list(gate),'source':source,'gate_name':self.gate_name(gate)}
     assigned_here+=1
     break
  for uid,call in sorted(self.scout_calls.items()):
   u=defenders[uid]
   if not u.accepts_orders or self.rotation_state(u) in ('休整','返回休整','接岗中'):
    continue
   gate=call['gate']
   home=tuple(self.orders[uid]['home'])
   if u.mission=='stock' or ((u.mission=='hold' or uid in self.watch_reserves)
                            and min(self.gates,key=lambda point:dist(home,point))!=gate):
    continue
   inward=self.gate_inward(gate)
   path=field(u.pos,self.blocked)
   candidates=[offset_gate(gate,inward,depth,lateral) for depth in range(1,6) for lateral in range(-5,6)]
   occupied_homes={position for ally,position in homes.items() if ally!=uid}
   own_previous=assignments.get(uid)
   if own_previous:
    posts.discard(tuple(own_previous['goal']))
   candidates=[p for p in candidates if p in path and p not in posts and p not in occupied_homes and inside_fort(p,self.fort_bounds)]
   if not candidates:
    if own_previous:posts.add(tuple(own_previous['goal']))
    continue
   role='archer' if 'archer' in u.skills and self.reach(u)>2 else 'guard'
   old=previous.get(uid)
   target=offset_gate(gate,inward,1 if role=='guard' else 3)
   goal=min(candidates,key=lambda p:(not (old and old.get('called') and old['goal']==list(p)),
       not(role=='archer' and p in self.slits and tuple(self.slits[p]['inward'])==tuple(inward)),dist(target,p),path[p],p))
   posts.add(goal)
   assignments[uid]={'role':role,'goal':list(goal),'gate':list(gate),'source':'斥候呼援','gate_name':self.gate_name(gate),'called':True}
  self.apply_field_orders(assignments)
  for uid,order in assignments.items():
   old = previous.get(uid)
   if not old or (old['goal'],old['role'])!=(order['goal'],order['role']):
    name = '粮仓岗位' if order.get('mission')=='stock' else '拦截位' if order['role']=='guard' else '射击位'
    self.record('reinforce',f"{uid}响应{order['source']}，调往{order['gate_name']}{name}",actor=uid,team='D')
  for uid in sorted(previous.keys()-assignments.keys()):
   self.record('reinforce',f'{uid}解除回援命令',actor=uid,team='D')
  self.reinforcements = assignments
 def observe(self,u):
  visible=[]
  scout = 'scout' in (u.skills or ())
  sight = max(self.stats[u.kind]['sight'],self.stats['scout']['sight']) if scout else self.stats[u.kind]['sight']
  for e in self.units:
   if e.team!=u.team and dist(u.pos,e.pos)<=sight and self.can_see(u,e.pos):
    v={**e.public(),'seen_at':self.round,'source':u.id,'scout_report':scout}
    visible.append(v)
    self.received[u.id][e.id]=v
    old = self.memory[u.team].get(e.id)
    if not old or old['seen_at']!=self.round or scout or not old.get('scout_report'):
     self.memory[u.team][e.id]=v
  self.memory[u.team]={k:v for k,v in self.memory[u.team].items() if self.round-v['seen_at']<=8}
  return {'self':{**u.public(),'treatments':u.treatments,'cooldown':u.cooldown,'skills':u.skills,'basic_defense':self.profile=='campaign' and u.team=='D','skill_rules':u.skill_rules if u.training==2 and u.accepts_orders else {},'fixed_watch':u.team=='D' and (u.mission!='reserve' or not u.accepts_orders or u.id not in self.reinforcements)},'allies':[a.public() for a in self.units if a.team==u.team],'visible':copy.deepcopy(visible),'intel':copy.deepcopy(list((self.memory[u.team] if u.skills is None else self.received[u.id]).values())),'round':self.round,'loot':list(self.loot_pos if u.team=='A' else STOCK),'orders':copy.deepcopy(self.orders[u.id]),'stats':self.stats,'reach':self.reach(u),'reinforcement':self.reinforcements.get(u.id),'rally':self.rally_goal(u),'rotation':self.rotation_orders.get(u.id),'morale':self.morale(u.team),'terrain':self.blocked,'gates':self.gates,'gate_inward':{g:self.gate_inward(g) for g in self.gates},'fort_bounds':self.fort_bounds,'at_slit':u.pos in self.slits,'structures':copy.deepcopy(self.structures)}
 def record(self,kind,text,**extra):
  event={'round':self.round,'kind':kind,'text':text,**extra};self.events.append(event);return event
 def rand(self,u,channel):return random.Random(f'{self.seed}|{self.round}|{u.id}|{channel}').random()
 def sync_gate_blocks(self):
  self.blocked=frozenset(set(self.base_blocked)|{tuple(p) for gate in self.structures if gate['hp']>0 for p in gate['cells']})

 def apply(self,u,d,obs):
  u.current_skill=d.get('skill');u.logic=d['logic'];u.reason=d['reason'];u.action=d['action'];self.policy_counts[d['logic']]+=1
  if u.id not in self.first_orders:self.first_orders[u.id]={'logic':u.logic,'reason':u.reason,'goal':d['goal'],'target':d['target']}
  rotation=self.rotation_orders.get(u.id)
  paired=rotation or any(post['watch']==u.id for post in self.rotation_posts)
  if paired and d['action']=='attack':
   u.fatigue=min(6,u.fatigue+1)
   u.rest_steps=0
  if rotation and rotation['state']=='休整' and d['action']=='hold':
   u.rest_steps+=1
   u.fatigue=max(0,u.fatigue-2)
  if d['action']=='siege':
   g=next((g for g in self.structures if g['id']==d['target']),None)
   if g and g['hp']>0 and u.team=='A' and any(dist(u.pos,p)<=1.5 and los(u.pos,p,self.blocked-frozenset(map(tuple,g['cells']))) for p in g['cells']):
    damage=6 if u.weapon=='siege' else 1 if u.weapon=='none' else 2
    g['hp']=max(0,g['hp']-damage);self.record('siege',f'{u.name or u.id}对{g.get("name",g["id"])}造成{damage}点伤害（余{g["hp"]:g}）',actor=u.id,gate=g['id'],damage=damage)
    if not g['hp']:
     self.sync_gate_blocks();self.record('breach',f'{g.get("name",g["id"])}被摧毁，通路打开',actor=u.id,gate=g['id'])
   return
  if d['action']=='attack':
   e=self.byid[d['target']]
   assert e.id in {v['id'] for v in obs['visible']} and e.active and dist(u.pos,e.pos)<=self.reach(u) and self.can_see(u,e.pos)
   self.audit_attacks.append([self.round,u.id,e.id])
   hit=self.stats[u.kind]['hit']-(.12 if u.wound else 0)-(.15 if e.pos in self.cover else 0)-(.15 if u.weapon=='none' else 0)
   if self.round<u.vigor_until:hit+=.16
   hit+=.05*u.veteran
   if u.fatigue>=4:hit-=.12
   strike=self.record('attack',f'{u.id}攻击{e.id}',actor=u.id,target=e.id,outcome='miss',ranged=self.reach(u)>2,armored=e.armor)
   if self.rand(u,'hit')<hit:
    strike['outcome']='blocked'
    injury=self.stats[u.kind]['injury']-(.16 if e.kind=='guard' else 0)-(.20 if e.armor else 0)-(.05 if self.profile=='campaign' and e.team=='D' else 0)
    if self.rand(u,'injury')<injury:
     e.wound+=1;strike['outcome']='disabled' if e.wound>=2 else 'injury';self.record('injury',f'{e.id}'+('失能' if e.wound>=2 else '受伤'),actor=u.id,target=e.id)
     if e.wound>=2 and e.cargo:e.cargo=False;self.loot_pos=e.pos;self.record('drop',f'{e.id}失能，补给落地')
   u.heading=math.atan2(e.pos[1]-u.pos[1],e.pos[0]-u.pos[0]);return
  if d['action']=='heal':
   a=self.byid[d['target']]
   if a.active and a.wound==1 and dist(u.pos,a.pos)<=1.5 and u.cooldown==0 and u.treatments>0:
    a.wound=0;u.treatments-=1;u.cooldown=3;self.record('heal',f'{u.id}救护{a.id}',actor=u.id,target=a.id)
   return
  if d['action']=='loot':
   if dist(u.pos,self.loot_pos)<=1.5 and not any(a.cargo for a in self.units):
    # Guarded store cannot be looted while a defender is close enough to contest.
    contested=any(a.active and a.team=='D' and dist(a.pos,self.loot_pos)<=2.5 for a in self.units)
    if not contested:
     self.loot_progress[u.id]=self.loot_progress.get(u.id,0)+1
     if self.loot_progress[u.id]>=2:u.cargo=True;self.captures[u.team]+=1;self.record('loot',f'{u.id}取得补给',actor=u.id)
   return
  if d['action']=='move' and d['goal'] is not None:
   if (u.wound or u.pos in self.rough) and self.round%2:return
   occupied={tuple(a['pos']) for a in obs['allies']+obs['visible'] if a['active'] and a['id']!=u.id}
   goal=tuple(d['goal'])
   for _ in range(int(self.stats[u.kind].get('speed',1))):
    if (rotation and d['reason']==rotation['state']) or (obs.get('reinforcement') or {}).get('manual'):
     route=field(goal,self.blocked|frozenset(occupied)) if goal not in occupied else {}
     q=min((p for p in neighbors(u.pos,self.blocked) if route.get(p,math.inf)<route.get(u.pos,math.inf)),
           key=lambda p:route[p],default=u.pos)
    else:
     q=move_step(u.pos,goal,occupied,self.blocked)
    actual_occupied={a.pos for a in self.units if a.active and a.id!=u.id}
    if q in actual_occupied:q=u.pos
    if q==u.pos and dist(u.pos,goal)>1:self.blocked_moves[u.team]+=1
    assert walk(q,self.blocked) and q not in occupied and dist(q,u.pos)<=1.01
    if q!=u.pos:u.heading=math.atan2(q[1]-u.pos[1],q[0]-u.pos[0]);u.pos=q;u.motion.append(list(q))
 def snapshot(self):
  self.history.append({'round':self.round,'units':[{**u.public(),'logic':u.logic,'reason':u.reason,'heading':round(u.heading,3),'action':u.action,'skills':u.skills,'current_skill':u.current_skill,'order_note':u.order_note,'mission':u.mission,'rotation_state':self.rotation_state(u),'fatigue':u.fatigue,'rest_steps':u.rest_steps,'vigor':max(0,u.vigor_until-self.round),'reinforcement':self.reinforcements.get(u.id),'motion':copy.deepcopy(u.motion)} for u in self.units],
   'intel':copy.deepcopy(self.memory),'alarm_gate':self.alarm_gate,'alarm_name':self.gate_name(self.alarm_gate) if self.alarm_gate else None,'morale':{team:self.morale(team) for team in ('D','A')},'structures':copy.deepcopy(self.structures),'events':[e for e in self.events if e['round']==self.round]})
 def step(self,limit=72):
  """Advance only one simulation tick; no future state is evaluated."""
  if not self.history:self.snapshot()
  if self.result:return self.history[-1]
  if self.round>=limit:self.result='deadline_no_extract';return self.history[-1]
  self.round+=1;n=self.round
  for u in self.units:u.motion=[list(u.pos)]
  self.check_morale()
  self.relay_intel()
  self.operate_fortifications()
  self.plan_rotation()
  self.plan_reinforcements()
  self.update_rally()
  order={team:[u for u in self.units if u.team==team] for team in ('D','A')}
  for team in order:random.Random(f'{self.seed}|{n}|{team}|order').shuffle(order[team])
  first='D' if n%2 else 'A';second='A' if first=='D' else 'D'
  for a,b in zip_longest(order[first],order[second]):
   for u in (a,b):
    if u is None or not u.active:continue
    if u.cooldown:u.cooldown-=1
    for post in self.rotation_posts:
     if post['watch']==u.id:
      self.orders[u.id]['home']=list(post['watch_cell'])
      break
    obs=self.observe(u);d=choose(obs);self.apply(u,d,obs)
    exit_point=self.orders[u.id].get('exit_point')
    if u.routed and (u.pos==tuple(exit_point) if exit_point else u.pos[0] in (0,self.width-1)):u.escaped=True;self.record('escape',f'{u.name or u.id}逃离战场',actor=u.id)
    if u.cargo and (u.pos==tuple(exit_point) if exit_point else u.pos[0]<=1):self.result='attacker_extract';break
   if self.result:break
  positions=[u.pos for u in self.units if u.active]
  assert len(positions)==len(set(positions))
  if not self.result and not any(u.active and u.team=='A' for u in self.units):self.result='defender_clear'
  if not self.result and self.profile=='campaign' and not any(u.active and not u.routed for u in self.units if u.team=='D'):
   self.result='defender_overrun'
  if not self.result and self.round>=limit:self.result='deadline_no_extract'
  self.snapshot()
  return self.history[-1]
 def run(self,limit=72):
  if not self.history:self.snapshot()
  while not self.result:self.step(limit)
  return self.summary()
 def summary(self):
  return {'profile':self.profile,'seed':self.seed,'result':self.result,'rounds':self.round,
          'D_disabled':sum(u.wound>=2 and u.team=='D' for u in self.units),'A_disabled':sum(u.wound>=2 and u.team=='A' for u in self.units),
          'routed':{team:sum(u.routed and u.team==team for u in self.units) for team in ('D','A')},'morale':{team:self.morale(team) for team in ('D','A')},'loot_taken':sum(self.captures.values()),'heals':sum(e['kind']=='heal' for e in self.events),'first_orders':self.first_orders,'logic_counts':dict(self.policy_counts),'blocked_moves':dict(self.blocked_moves)}

def tests():
 b=Battle('neither');u=b.byid['D0'];o1=b.observe(u);d1=choose(o1)
 b.byid['A0'].pos=(2,22);o2=b.observe(u)
 assert o1==o2 and d1==choose(o2),'Hidden enemy truth leaked into decision'
 b.loot_pos=(2,22);assert b.observe(u)==o2,'Hidden drop position leaked to defender'
 # An old memory point is retained, not silently updated from the true actor.
 b.memory['D']['A0']={'id':'A0','team':'A','kind':'guard','pos':[4,6],'wound':0,'cargo':False,'active':True,'seen_at':0,'source':'test'}
 b.round=4;obs=b.observe(u);assert next(e for e in obs['intel'] if e['id']=='A0')['pos']==[4,6]
 b.round=9;assert not any(e['id']=='A0' for e in b.observe(u)['intel'])
 # Terrain line-of-sight and two disjoint gate passages.
 assert not los((13,10),(15,10)) and los((13,6),(15,6))
 assert field(STOCK).get((3,5)) is not None and field(STOCK).get((3,19)) is not None
 a=Battle('attacker',7);c=Battle('attacker',7);assert a.run()==c.run() and a.history==c.history
 n=Battle('neither');d=Battle('defender');a=Battle('attacker')
 assert choose(n.observe(n.byid['D1']))['goal']!=choose(d.observe(d.byid['D1']))['goal']
 assert choose(n.observe(n.byid['A0']))['goal']!=choose(a.observe(a.byid['A0']))['goal']
 return ['hidden-state noninterference','hidden loot-drop noninterference','last-seen memory and expiry','wall sight occlusion','two navigable entrances','seed replay determinism','initial intel changes both sides orders','per-action LOS/range legality','per-round active occupancy uniqueness']

def main():
 passed=tests();summaries=[];replays=[]
 for name in PROFILES:
  b=Battle(name,7);s=b.run();summaries.append(s);replays.append({'summary':s,'frames':b.history})
 batch=[]
 for seed in range(20):
  for name in PROFILES:batch.append(Battle(name,seed).run())
 outputs={'map':{'width':WIDTH,'height':HEIGHT,'blocked':sorted(BLOCKED),'buildings':BUILDINGS,'gates':GATES,'stock':STOCK},'types':CFG,'profiles':PROFILES,'replays':replays}
 (ROOT/'replays.json').write_text(json.dumps(outputs,ensure_ascii=False,separators=(',',':')),encoding='utf8')
 (ROOT/'results.json').write_text(json.dumps({'tests_passed':passed,'representative_seed':7,'summaries':summaries,'runs':batch},ensure_ascii=False,indent=2),encoding='utf8')
 with (ROOT/'results.csv').open('w',encoding='utf-8-sig',newline='') as f:
  cols=['profile','seed','result','rounds','D_disabled','A_disabled','loot_taken','heals'];w=csv.DictWriter(f,cols,extrasaction='ignore');w.writeheader();w.writerows(batch)
 print(json.dumps({'tests':passed,'results':[{k:v for k,v in s.items() if k not in ('first_orders','logic_counts')} for s in summaries]},ensure_ascii=True))
if __name__=='__main__':main()
