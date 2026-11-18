"""Hand-authored defense levels. Enemy deployments are generated on the server."""
from copy import deepcopy
from random import Random
from secrets import randbelow
from simulate import Battle, SKILLS, STOCK, REGION_SIZE, WIDTH, HEIGHT

COSTS = {
    'skills': {'guard': 2, 'archer': 3, 'scout': 2, 'medic': 3},
    'weapons': {'none': 0, 'melee': 2, 'ranged': 3},
    'armor': 2, 'banner': 3,
    'structures': {'reinforce':3,'tower':4,'ballista':5},
}
LEVELS = {
    'gate': dict(title='一 · 双门堡', description='西门、北门各有射击点，敌军随机主攻一面。',
                 budget=24, turns=62, bounds=(9,5,28,18), entries={'W':11,'N':20}, hp=16, enemy_count=8,
                 starts=((10,10),(19,6),(13,8),(19,13),(25,9),(26,11)),
                 blocked=((14,9,16,11),(21,13,23,15)), cover=((11,11),(20,7),(24,8))),
    'split': dict(title='二 · 三门围城', description='西、北、南三面可来敌。中央建筑将城内道路分成两路。',
                  budget=30, turns=70, bounds=(8,4,29,19), entries={'W':11,'N':18,'S':23}, hp=18, enemy_count=11,
                  starts=((9,10),(17,5),(22,18),(14,8),(24,13),(25,8),(27,10)),
                  blocked=((15,8,17,15),(21,7,23,10)), cover=((10,11),(18,6),(23,17),(24,8))),
    'stock': dict(title='三 · 四面围粮', description='四个方向均可突袭。城内还有护粮短墙，东门离粮仓最近。',
                  budget=34, turns=76, bounds=(7,4,29,20), entries={'W':11,'N':16,'S':20,'E':12}, hp=13, enemy_count=14,
                  starts=((8,10),(15,5),(19,19),(28,11),(22,7),(24,10),(26,9),(27,8)),
                  blocked=((12,7,14,13),(18,10,21,13),(24,12,27,13),(22,6,24,6)),
                  cover=((16,7),(22,8),(24,8),(25,9),(26,10),(28,8))),
}
DIRECTIONS = {'W':('西',(1,0)), 'N':('北',(0,1)), 'S':('南',(0,-1)), 'E':('东',(-1,0))}
LABELS = {key:value['label'] for key,value in SKILLS.items()}


def public_level(key, level):
    left, top, right, bottom = level['bounds']
    walls = {(x,y) for x in range(left,right+1) for y in (top,bottom)}
    walls |= {(x,y) for y in range(top,bottom+1) for x in (left,right)}
    gates, slits = [], []
    for side, offset in level['entries'].items():
        name, inward = DIRECTIONS[side]
        dx,dy = inward
        tangent = (abs(dy),abs(dx))
        x = left if side=='W' else right if side=='E' else offset
        y = top if side=='N' else bottom if side=='S' else offset
        cells = [(x,y),(x+tangent[0],y+tangent[1])]
        walls.difference_update(cells)
        gates.append(dict(id='G'+side,name=name+'门',hp=level['hp'],cells=[list(p) for p in cells],inward=list(inward),upgrades=[]))
        for shift in (-1,2):
            wall=(x+shift*tangent[0],y+shift*tangent[1])
            slits.append(dict(pos=[wall[0]+dx,wall[1]+dy],wall=list(wall),inward=list(inward),name=name+'墙射击点'))
    buildings = {(x,y) for x0,y0,x1,y1 in level['blocked']
                 for x in range(x0,x1+1) for y in range(y0,y1+1)}
    return {
        'id':key,'title':level['title'],'description':level['description'],
        'budget':level['budget'],'turns':level['turns'],'bounds':list(level['bounds']),
        'terrain':{'blocked':[list(p) for p in sorted(walls|buildings)],'cover':[list(p) for p in level['cover']],
                   'rough':[],'slits':slits},
        'gates':gates,
        'units':[dict(id=f'D{i}',team='D',kind='guard',pos=list(position),name=f'守军 {i+1}',
                      skills=[],equipment=dict(weapon='none',armor=False,banner=False),mission='hold')
                 for i,position in enumerate(level['starts'])],
    }


def catalog():
    return {'levels':[public_level(key,level) for key,level in LEVELS.items()],'costs':COSTS,'skills':LABELS}


def owned_cost(unit):
    equipment = unit['equipment']
    return (sum(COSTS['skills'][key] for key in unit['skills'] if key!=unit.get('free_skill')) + COSTS['weapons'][equipment['weapon']]
            + equipment['armor']*COSTS['armor'] + equipment['banner']*COSTS['banner'])


def prepare(payload, seed=None, settlement=None):
    key = payload.get('level')
    if not isinstance(key,str) or key not in LEVELS:
        raise ValueError('请选择守城关卡')
    level = LEVELS[key]
    public = public_level(key,level)
    width,height=REGION_SIZE if settlement else (WIDTH,HEIGHT)
    if settlement:
        public['terrain']=settlement.map['terrain']
    soldiers = payload.get('units')
    if not isinstance(soldiers,list) or len(soldiers)!=len(public['units']):
        raise ValueError('守军人数由关卡决定')
    baseline = {u['id']:u for u in public['units']}
    defenders = []
    for soldier in soldiers:
        ident = soldier.get('id') if isinstance(soldier,dict) else None
        if not isinstance(ident,str) or ident not in baseline:
            raise ValueError('守军名单不符')
        position = soldier.get('pos')
        left,top,right,bottom=(0,0,width-1,height-1) if settlement else level['bounds']
        if not isinstance(position,list) or len(position)!=2 or any(type(v) is not int for v in position) or not (left<position[0]<right and top<position[1]<bottom):
            raise ValueError('守军须部署在地图有效区域' if settlement else '守军只能部署在城内')
        skills = soldier.get('skills')
        if not isinstance(skills,list) or len(skills)>len(SKILLS) or any(not isinstance(k,str) or k not in SKILLS for k in skills) or len(set(skills))!=len(skills):
            raise ValueError('训练列表无效')
        free_skill=soldier.get('free_skill',skills[0] if skills else None)
        if (skills and free_skill not in skills) or (not skills and free_skill is not None):
            raise ValueError('免费训练须属于已选技能')
        equipment = soldier.get('equipment')
        if (not isinstance(equipment,dict) or not isinstance(equipment.get('weapon'),str)
                or equipment['weapon'] not in COSTS['weapons'] or type(equipment.get('armor')) is not bool
                or type(equipment.get('banner')) is not bool):
            raise ValueError('装备配置无效')
        defenders.append({**baseline.pop(ident),'pos':position,'skills':skills,'free_skill':free_skill,'equipment':equipment,
                          'mission':soldier.get('mission','hold'),'rotation_reserve':soldier.get('rotation_reserve',False)})
    purchases=settlement.upgrades if settlement else payload.get('fortifications',{})
    valid_gates={g['id'] for g in public['gates']}
    prices=COSTS['structures']
    if (not isinstance(purchases,dict) or any(g not in valid_gates or not isinstance(items,list)
            or len(items)>len(prices) or any(not isinstance(item,str) or item not in prices for item in items)
            or len(set(items))!=len(items) for g,items in purchases.items())):
        raise ValueError('设施配置无效')
    structure_cost=0 if settlement else sum(prices[item] for items in purchases.values() for item in items)
    for gate in public['gates']:
        gate['upgrades']=purchases.get(gate['id'],[])
        if 'reinforce' in gate['upgrades']:
            gate['hp']+=10
    if sum(owned_cost({**u,'skills':[]} if settlement else u) for u in defenders)+structure_cost>level['budget']:
        raise ValueError('装备与训练超出本关点数')
    seed = randbelow(1_000_000) if seed is None else seed
    rng = Random(seed)
    chosen = rng.sample(public['gates'],1 if key=='gate' else 2)
    enemies, routes = [], {}
    occupied={tuple(u['pos']) for u in defenders} | {tuple(p) for p in public['terrain']['blocked']} | {tuple(p) for g in public['gates'] for p in g['cells']}
    enemy_count=level['enemy_count']
    if settlement and settlement.raids==0:
        enemy_count=(enemy_count*3+3)//4
    for i in range(enemy_count):
        gate = chosen[i%len(chosen)]
        x,y=gate['cells'][0]
        dx,dy=gate['inward']
        depth = i//len(chosen)
        spread=(0,-1,1,-2,2)[depth%5]
        distance=1+depth//5
        if settlement:distance+=3 if dx==-1 or dy==-1 else 1
        spawn=[x-dx*distance+abs(dy)*spread,y-dy*distance+abs(dx)*spread]
        if settlement:
            options=[(px,py) for px in range(width) for py in range(height)
                     if (px,py) not in occupied and (px-x)*dx+(py-y)*dy<0]
            spawn=list(min(options,key=lambda p:(abs(p[0]-spawn[0])+abs(p[1]-spawn[1]),p)))
            occupied.add(tuple(spawn))
        kind = 'archer' if depth%3==2 else 'scout'
        equipment = dict(armor=depth%3==0,banner=depth==0,
                         weapon='siege' if depth==0 else 'ranged' if kind=='archer' else 'melee')
        ident = f'A{i}'
        enemies.append(dict(id=ident,team='A',kind=kind,pos=spawn,equipment=equipment,
                            skills=['archer' if kind=='archer' else 'guard'],morale_threshold=3))
        exit_point=[(0 if dx==1 else width-1) if dx else x,(0 if dy==1 else height-1) if dy else y]
        routes[ident] = dict(entry=[x,y],entry_side=[dx,dy],exit_point=exit_point)
    scenario = dict(units=defenders+enemies,terrain=public['terrain'],gates=public['gates'],
                    intel={'D':[],'A':[]},alarm_bell=True,minimum_watch=1,
                    stats={'guard':{'hit':.70,'injury':.66},'scout':{'hit':.65,'injury':.56},'archer':{'hit':.67,'injury':.60}})
    battle = Battle('campaign',seed,scenario,regional=bool(settlement))
    battle.gates=tuple(tuple(g['cells'][0]) for g in public['gates'])
    battle.gate_metadata={tuple(g['cells'][0]):g for g in public['gates']}
    battle.slits={tuple(point['pos']):point for point in public['terrain']['slits']}
    battle.fort_bounds=public['bounds']
    if settlement:
        for gate in battle.structures:
            gate['hp']=settlement.gate_hp[gate['id']]
        battle.sync_gate_blocks()
        for unit in battle.units:
            if unit.team=='D':
                unit.veteran=settlement.rank(unit.id)
                unit.morale_threshold-=unit.veteran
    for ident,route in routes.items():
        battle.orders[ident].update(route)
        battle.orders[ident]['escape']=route['exit_point']
    return battle,level['turns']


def player_frame(frame):
    """Send only defender state, contacts acquired by them, and public objectives."""
    allies = [u for u in frame['units'] if u['team']=='D']
    known = frame['intel']['D']
    visible = {u['id'] for u in allies} | known.keys()
    events = [event for event in frame['events'] if event.get('team')!='A'
              and (event.get('actor') in visible or event.get('team')=='D' or event['kind']=='breach')
              and (event.get('target') is None or event['target'] in visible)]
    events = [{**event,'actor':None} if event['kind']=='breach' and event.get('actor') not in visible
              else event for event in events]
    return {**frame,'units':allies,'intel':{'D':known},
            'morale':{'D':frame['morale']['D']},'events':events}


def player_summary(battle):
    result = battle.result
    return {'rounds':battle.round,'result':result,
            'order_available':battle.field_order is None,
            'victory':result in ('deadline_no_extract','defender_clear') if result else None}
