import copy,json
from simulate import Battle,choose,intent,validate_scenario,field
def scenario():
 return {'units':[{'id':'D0','team':'D','kind':'scout','name':'旗手','pos':[20,6],'equipment':{'banner':True},'morale_threshold':5}]+[{'id':f'D{i}','team':'D','kind':'guard','pos':[20,i+7]} for i in range(1,4)]+[{'id':'A0','team':'A','kind':'guard','pos':[3,6],'equipment':{'weapon':'siege'}}],
 'intel':{'D':[],'A':[]},'terrain':{'blocked':[],'cover':[],'rough':[]},'morale':{'interval':5,'chance':1},'gates':[{'id':'G1','name':'测试城门','hp':12,'cells':[[4,6]]}]}
checks=[]
s=scenario();b=Battle('custom',7,s)
for i in range(1,4):b.byid[f'D{i}'].wound=2
assert b.morale('D')['base']==2.5 and b.morale('D')['current']==6.5
b.round=5;b.check_morale();assert not b.byid['D0'].routed
b.byid['D0'].banner=False;b.round=6;b.check_morale();assert not b.byid['D0'].routed
b.round=10;b.check_morale();assert b.byid['D0'].routed
obs=b.observe(b.byid['D0']);assert choose(obs)['goal']==[31,6] and choose(obs)['action']=='move'
checks+=['base survival morale with initial denominator','banner adds exactly four points','banner prevents low-morale check','checks only at configured interval','low morale can route','routing overrides normal AI']
s=scenario();b=Battle('custom',7,s);b.byid['D0'].routed=True;assert b.morale('D')['bonus']==0
b.byid['D0'].routed=False;b.byid['D0'].wound=2;assert b.morale('D')['bonus']==0
b=Battle('custom',7,s);assert b.morale('D')['current']==10
b.byid['D1'].banner=True;b.byid['D2'].wound=2;b.byid['D3'].wound=2;assert b.morale('D')['bonus']==4
for u in b.units:u.escaped=True
assert b.morale('D')['base']==0
checks+=['routed or disabled leader loses bonus','morale capped ten and banners do not stack','escaped unit excluded without shrinking denominator']
s=scenario();s['units'][0]['morale_threshold']=10;b=Battle('custom',7,s);b.round=5;b.check_morale();assert not b.byid['D0'].routed
checks+=['equal morale does not trigger routing']
s=scenario();b=Battle('custom',7,s);u=b.byid['A0'];d=choose(b.observe(u));assert d['action']=='siege'
b.snapshot();b.apply(u,d,b.observe(u));assert b.structures[0]['hp']==6 and (4,6) in b.blocked
b.apply(u,choose(b.observe(u)),b.observe(u));assert b.structures[0]['hp']==0 and (4,6) not in b.blocked
assert b.history[0]['structures'][0]['hp']==12
checks+=['AI chooses adjacent closed gate','siege weapon deals six damage','gate destroyed releases navigation','past gate health snapshots immutable']
s=scenario();s['units'][-1]['equipment']['weapon']='melee';b=Battle('custom',7,s);u=b.byid['A0'];b.apply(u,choose(b.observe(u)),b.observe(u));assert b.structures[0]['hp']==10
s['units'][-1]['equipment']['weapon']='ranged';b=Battle('custom',7,s);assert b.reach(b.byid['A0'])==6.2
s['units'][-1]['equipment']['weapon']='melee';b=Battle('custom',7,s);assert b.reach(b.byid['A0'])==1.5
checks+=['ordinary gate damage two','ranged and melee equipment change actual reach']
s=scenario();s['gates']=[];s['units']=[{'id':'D','team':'D','kind':'scout','pos':[5,6],'equipment':{'armor':True}},{'id':'A','team':'A','kind':'guard','pos':[4,6]}];s['stats']={'guard':{'hit':1,'injury':1}}
b=Battle('custom',7,s);b.rand=lambda u,c:0 if c=='hit' else .9;u=b.byid['A'];b.apply(u,intent('交战/截击','attack','test',target='D'),b.observe(u));assert b.byid['D'].wound==0
s['units'][0]['equipment']['armor']=False;b=Battle('custom',7,s);b.rand=lambda u,c:0 if c=='hit' else .9;u=b.byid['A'];b.apply(u,intent('交战/截击','attack','test',target='D'),b.observe(u));assert b.byid['D'].wound==1
checks+=['armor changes real injury roll']
s=scenario();a=Battle('custom',7,s);b=Battle('custom',7,s);assert a.run(40)==b.run(40) and a.history==b.history
checks+=['equipment morale gate scenario deterministic']
print(json.dumps({'passed':len(checks),'checks':checks},ensure_ascii=True))
