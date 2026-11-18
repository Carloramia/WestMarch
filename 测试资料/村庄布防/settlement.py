"""Persistent village bookkeeping between raids, using the existing battle engine."""
from random import Random
from copy import deepcopy
from simulate import dist, inside_fort, STOCK, REGION_SIZE
from campaign import LEVELS, COSTS, public_level, prepare

WORK = {
    'reinforce': ('加固', 4, 4),
    'tower': ('瞭望塔', 5, 5),
    'ballista': ('弩炮', 7, 6),
    'repair': ('修复 +8', 3, 3),
}
RAIDS = 3


class Settlement:
    def __init__(self, level, seed):
        if not isinstance(level,str) or level not in LEVELS:
            raise ValueError('请选择守城关卡')
        self.level = level
        self.map = public_level(level, LEVELS[level])
        self.map['terrain'].update(width=REGION_SIZE[0],height=REGION_SIZE[1])
        for x,y in ((33,3),(34,16),(35,23),(14,26),(24,28)):
            self.map['terrain']['blocked'].extend([[x+dx,y+dy] for dx in range(2) for dy in range(3)])
        self.map['terrain']['rough'] += [[x,y] for x in range(36,43) for y in (8,9,18,19)]
        self.rng = Random(seed)
        self.clock = 0
        self.safe_until = 5
        self.next_raid = self.rng.randint(6, 11)
        self.raids = 0
        self.phase = 'safe'
        self.resources = {'materials': 9, 'supplies': 4}
        self.jobs = []
        self.upgrades = {g['id']: [] for g in self.map['gates']}
        self.gate_hp = {g['id']: g['hp'] for g in self.map['gates']}
        self.skills = {u['id']: [] for u in self.map['units']}
        self.xp = dict.fromkeys(self.skills, 0)
        self.sites = self.make_sites()
        self.map['terrain']['cover'] += [site['pos'] for site in self.sites if site.get('covered')]

    def make_sites(self):
        sites = [dict(id='mill', name='内堡粮场', pos=list(STOCK), resource='supplies', rate=1, outer=False)]
        for gate in self.map['gates']:
            x,y = gate['cells'][0]
            dx,dy = gate['inward']
            for kind, name, rate, offset in [('materials','工料场',2,-2), ('supplies','屯田',2,2)]:
                pos = [x-3*dx+offset*abs(dy), y-3*dy+offset*abs(dx)]
                sites.append(dict(id=gate['id']+kind,name=gate['name'][0]+name,pos=pos,resource=kind,rate=rate,
                                  outer=True,covered=kind=='supplies' and gate['id'] in ('GN','GS')))
        return sites+[
            dict(id='eastworks',name='东郊堆场',pos=[36,12],resource='materials',rate=3,outer=True,covered=False),
            dict(id='southfarm',name='南郊麦田',pos=[21,27],resource='supplies',rate=3,outer=True,covered=True),
        ]

    def rank(self, unit):
        return min(2, self.xp[unit]//3)

    def gates(self):
        return [{**g,'hp':self.gate_hp[g['id']],
                 'max_hp':g['hp']+10*('reinforce' in self.upgrades[g['id']]),
                 'upgrades':self.upgrades[g['id']][:]} for g in self.map['gates']]

    def public(self):
        return {'phase':self.phase,'clock':self.clock,'raids':self.raids,'total':RAIDS,
                'resources':self.resources,'sites':self.sites,'jobs':self.jobs,'gates':self.gates(),'terrain':self.map['terrain'],
                'work':WORK,'training':COSTS['skills'],'skills':self.skills,'xp':self.xp,
                'safe_left':max(0,self.safe_until-self.clock) if self.phase=='safe' else None,
                'ranks':{unit:self.rank(unit) for unit in self.xp}}

    def queue(self, target, kind):
        if self.phase!='safe':
            raise ValueError('只能在安全期新建队列')
        if not isinstance(target,str) or not isinstance(kind,str):
            raise ValueError('请选择工程或训练')
        training = target in self.skills
        crew = [job for job in self.jobs if job['training']==training]
        if len(crew)>=(2 if training else 1):
            raise ValueError('训练位已满' if training else '施工队正在工作')
        if any(job['target']==target for job in crew):
            raise ValueError('同一棋子只能训练一项')
        if training:
            if kind not in COSTS['skills'] or kind in self.skills[target]:
                raise ValueError('请选择尚未掌握的技能')
            cost = COSTS['skills'][kind] if self.skills[target] else 0
            resource, duration = 'supplies', 3
        else:
            gate = next((g for g in self.gates() if g['id']==target),None)
            if not gate or kind not in WORK or kind in self.upgrades[target]:
                raise ValueError('请选择可施工的城门和设施')
            if kind=='repair' and gate['hp']>=gate['max_hp']:
                raise ValueError('城门目前完好')
            _, cost, duration = WORK[kind]
            resource = 'materials'
        if self.resources[resource]<cost:
            raise ValueError('库存不足')
        self.resources[resource]-=cost
        self.jobs.append(dict(target=target,kind=kind,training=training,left=duration,paused=False))

    def advance(self, units):
        if self.phase!='safe':
            raise ValueError('当前无法推进安全期')
        if not isinstance(units,list) or len(units)!=len(self.skills):
            raise ValueError('守军名单无效')
        checked = []
        for unit in units:
            if not isinstance(unit,dict) or not isinstance(unit.get('id'),str) or unit['id'] not in self.skills:
                raise ValueError('守军名单无效')
            learned = self.skills[unit['id']]
            preference = unit.get('skills')
            if not isinstance(preference,list) or any(not isinstance(skill,str) for skill in preference):
                raise ValueError('训练排序无效')
            skills = list(dict.fromkeys([skill for skill in preference if skill in learned]+learned))
            checked.append({**unit,'skills':skills,'free_skill':learned[0] if learned else None})
        # Validation precedes spending time. The selected attack seed is independent of placement.
        seed = self.rng.getstate()
        try:
            battle, limit = prepare({'level':self.level,'units':checked}, self.rng.randrange(1000000), self)
        finally:
            self.rng.setstate(seed)
        if self.clock+1>=self.next_raid:
            self.rng.randrange(1000000)
            self.clock+=1
            self.phase='conflict'
            battle.snapshot()
            battle.history[-1]['sites']=deepcopy(self.sites)
            return battle, limit
        self.economy([tuple(u.pos) for u in battle.units if u.team=='D'], [])
        return None

    def economy(self, guards, enemies, battle=None):
        self.clock+=1
        for site in self.sites:
            pos=site['pos']
            threatened=any(dist(pos,p)<=3 for p in enemies)
            guarded=any(dist(pos,p)<=4 and (not site['outer'] or not inside_fort(p,self.map['bounds']))
                        for p in guards)
            if battle and threatened and site.get('status')!='争夺中':
                battle.record('site_contested',f'{site["name"]}遇袭，停止生产',
                              team='D',pos=pos,round=battle.round+1)
            site['status']='争夺中' if threatened else '缺少守军' if site['outer'] and not guarded else '生产中'
            if self.clock%2==0 and site['status']=='生产中':
                key=site['resource']
                self.resources[key]=min(60,self.resources[key]+site['rate'])
        gates={g['id']:g for g in (battle.structures if battle else self.gates())}
        for job in self.jobs[:]:
            key,kind=job['target'],job['kind']
            if job['training']:
                blocked=bool(battle)
            else:
                cells=gates[key]['cells']
                blocked=any(dist(cell,p)<=3 for cell in cells for p in enemies)
                blocked=blocked or (kind in ('repair','reinforce') and gates[key]['hp']==0
                                    and any(tuple(cell) in guards for cell in cells))
            job['paused']=blocked
            if blocked:
                continue
            job['left']-=1
            if job['left']:
                continue
            self.jobs.remove(job)
            if job['training']:
                self.skills[key].append(kind)
                continue
            if kind!='repair':
                self.upgrades[key].append(kind)
            maximum=gates[key]['max_hp']+10*(kind=='reinforce')
            self.gate_hp[key]=min(maximum,gates[key]['hp']+(8 if kind=='repair' else 10 if kind=='reinforce' else 0))
            if battle:
                gates[key].update(hp=self.gate_hp[key],max_hp=maximum,upgrades=self.upgrades[key][:])
                battle.sync_gate_blocks()
                battle.record('construction',f'{gates[key]["name"]}完成{WORK[kind][0]}',
                              gate=key,team='D',round=battle.round+1)

    def step(self, battle, limit):
        if self.phase!='conflict' or battle.result:
            return battle.history[-1]
        self.economy([u.pos for u in battle.units if u.team=='D' and u.active and not u.routed],
                     [u.pos for u in battle.units if u.team=='A' and u.active and not u.routed],battle)
        frame=battle.step(limit)
        frame['sites']=deepcopy(self.sites)
        self.gate_hp.update({g['id']:g['hp'] for g in battle.structures})
        if battle.result:
            self.raids+=1
            veterans={event.get('actor') for event in battle.events if event['kind']=='heal'
                      or (event['kind']=='attack' and event.get('outcome') in ('injury','disabled'))}
            for unit in battle.units:
                if unit.team=='D' and unit.active and not unit.routed:
                    self.xp[unit.id]+=1+(unit.id in veterans)
            if battle.result not in ('deadline_no_extract','defender_clear'):
                self.phase='lost'
            elif self.raids>=RAIDS:
                self.phase='won'
            else:
                self.phase='safe'
                self.safe_until=self.clock+3
                self.next_raid=self.clock+self.rng.randint(4,10)
        return frame
