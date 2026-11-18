"""Regression checks for editable simulation, not a balance verdict."""
import copy,json,urllib.request,urllib.error
from simulate import Battle,tests,validate_scenario,choose,intent,los,field,STOCK

def scenario():
 return {'units':[{'id':'Def','team':'D','kind':'guard','pos':[28,23]}]+[{'id':f'Atk{i}','team':'A','kind':'scout','pos':[2,i+2]} for i in range(5)],'intel':{'D':['Atk0'],'A':[]},'terrain':{'blocked':[],'cover':[],'rough':[]},'stats':{'scout':{'speed':3,'hit':0,'sight':1,'treatments':0}}}

checks=tests()
s=scenario();b=Battle('custom',7,s);result=b.run(1)
assert len(result['first_orders'])==6
assert b.history[0]['intel']['D'].keys()=={'Atk0'}
assert all(u.treatments==0 for u in b.units if u.team=='A')
assert choose(Battle('custom',7,s).observe(Battle('custom',7,s).byid['Def']))['goal']==[28,23]
checks+=['unequal 1 vs 5 all activate','custom IDs and deployment homes','individual initial reports','per-type treatments']
# Configurable speed affects real movement, not replay animation.
b=Battle('custom',7,s);u=b.byid['Atk0'];obs=b.observe(u);b.round=2;b.apply(u,intent('守点/推进','move','test',(10,2)),obs);assert u.pos==(5,2)
s['terrain']['rough']=[[2,2]];b=Battle('custom',7,s);u=b.byid['Atk0'];b.round=1;b.apply(u,intent('守点/推进','move','test',(10,2)),b.observe(u));assert u.pos==(2,2)
s['terrain']['blocked']=[[5,y] for y in range(24) if y not in (3,7,12,18,22)]
b=Battle('custom',7,s);assert not los((4,4),(6,4),b.blocked) and los((4,12),(6,12),b.blocked)
assert field(STOCK,b.blocked).get((2,2)) is not None
checks+=['speed steps actual grid movement','rough terrain delays movement','custom wall LOS and five passages']
# Guaranteed hit: cover changes adjudication by exactly 15 percentage points.
s=scenario();s['units']=[{'id':'D','team':'D','kind':'archer','pos':[6,6]},{'id':'A','team':'A','kind':'scout','pos':[5,6]}];s['intel']={'D':[],'A':[]};s['stats']={'archer':{'hit':1,'injury':1}};s['terrain']['cover']=[[5,6]]
b=Battle('custom',7,s);b.rand=lambda u,ch: .9 if ch=='hit' else 0;u=b.byid['D'];b.apply(u,intent('交战/截击','attack','test',target='A'),b.observe(u));assert b.byid['A'].wound==0
s['terrain']['cover']=[];b=Battle('custom',7,s);b.rand=lambda u,ch: .9 if ch=='hit' else 0;u=b.byid['D'];b.apply(u,intent('交战/截击','attack','test',target='A'),b.observe(u));assert b.byid['A'].wound==1
checks+=['cover modifies actual hit roll']
# Editable terrain, stats, and asymmetric forces remain reproducible for multiple seeds.
for seed in range(5):
 s=scenario();a=Battle('custom',seed,s);b=Battle('custom',seed,s);assert a.run(40)==b.run(40) and a.history==b.history
checks+=['custom scenario seed reproducibility across five seeds']
bad=scenario();bad['units'][0]['pos']=bad['units'][1]['pos']
try:validate_scenario(bad);raise AssertionError('overlap accepted')
except ValueError:pass
request=urllib.request.Request('http://127.0.0.1:8877/api/simulate',data=json.dumps(bad).encode(),headers={'Content-Type':'application/json'})
try:urllib.request.urlopen(request);raise AssertionError('invalid API payload accepted')
except urllib.error.HTTPError as e:assert e.code==400
checks+=['overlap rejected by engine and HTTP API']
def post(path,payload):
 request=urllib.request.Request('http://127.0.0.1:8877/api/'+path,data=json.dumps(payload).encode(),headers={'Content-Type':'application/json'})
 with urllib.request.urlopen(request) as response:return json.load(response)
s=scenario();s.update(seed=7,limit=4);start=post('start',s)
assert len(start['frames'])==1 and start['summary']['rounds']==0 and start['summary']['result'] is None
frames=start['frames'][:]
for n in range(1,5):
 update=post('tick',{'session':start['session']});assert update['frame']['round']==n and update['done']==(n==4);frames.append(update['frame'])
b=Battle('custom',7,s);summary=b.run(4);assert frames==b.history and update['summary']==summary
post('stop',{'session':start['session']})
try:post('tick',{'session':start['session']});raise AssertionError('cancelled battle continued')
except urllib.error.HTTPError as e:assert e.code==400
checks+=['start API evaluates no future ticks','tick API advances exactly one step and matches batch result','stopped battle cannot continue']
print(json.dumps({'passed':len(checks),'checks':checks},ensure_ascii=True))
