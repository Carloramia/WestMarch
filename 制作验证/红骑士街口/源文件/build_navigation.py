"""Compile authored movement orders into verified navigation tracks and state snapshots."""
import pathlib,json,math
from navigation import blocked,astar,clear,interpolate
ROOT=pathlib.Path(__file__).resolve().parent
scene=json.loads((ROOT/'scene.json').read_text(encoding='utf8'))
tracks={};reroutes=[]
for name,unit in scene['units'].items():
 keys=unit['orders'];dense=[]
 for (s,a),(e,b) in zip(keys,keys[1:]):
  # Preserve original dramatic timing when the scheduled segment is navigable.
  steps=max(1,math.ceil((e-s)*20));direct=[]
  for j in range(steps+1):
   t=s+(e-s)*j/steps;v=j/steps;v=v*v*(3-2*v)
   direct.append([t,[a[0]+(b[0]-a[0])*v,a[1]+(b[1]-a[1])*v]])
  if any(blocked(p,t) for t,p in direct):
   route=astar(a,b,(s+e)/2);lengths=[math.dist(x,y) for x,y in zip(route,route[1:])];total=sum(lengths)
   direct=[]
   for j in range(steps+1):
    t=s+(e-s)*j/steps;d=total*j/steps
    for x,y,length in zip(route,route[1:],lengths):
     if d<=length:
      v=d/max(length,1e-8);p=[x[0]+(y[0]-x[0])*v,x[1]+(y[1]-x[1])*v];break
     d-=length
    else:p=b
    if blocked(p,t):raise ValueError(f'{name}: moving obstacle requires rescheduling at {t}')
    direct.append([t,p])
   reroutes.append({'unit':name,'interval':[s,e],'route':route})
  dense.extend(direct[:-1])
 dense.append(keys[-1]);tracks[name]=dense
tests=[]
for a,b,t in [((500,450),(650,650),10),((350,500),(450,820),10),((350,650),(600,650),45)]:
 r=astar(a,b,t)
 assert len(r)>2 and all(clear(x,y,t) for x,y in zip(r,r[1:]))
 tests.append({'start':a,'goal':b,'time':t,'route':r,'detour':True})
snapshots=[]
for step in range(961):
 t=step/10;states={}
 for name,unit in scene['units'].items():
  q=interpolate(t,tracks[name]);q2=interpolate(t+.1,tracks[name]);status='active'
  if t>=unit.get('disabled_at',math.inf):status='disabled'
  if t>=unit.get('surrender_at',math.inf):status='surrendered'
  if name=='courier' and q[1]>1040:status='exited'
  heading=math.atan2(q2[1]-q[1],q2[0]-q[0]) if math.dist(q,q2)>.1 else unit['idle_heading']
  states[name]={'position':q,'heading':heading,'status':status,'radius':18}
 for name,row in states.items():
  if name=='courier' or row['status']!='active':continue
  if name=='knight':
   targets=[v for k,v in states.items() if k.startswith('enemy') and v['status']=='active']
   target=min(targets,key=lambda v:math.dist(row['position'],v['position'])) if targets else None
  else:target=states['courier' if name=='enemy4' and 32<t<65 else 'knight']
  if target:
   a,b=row['position'],target['position'];row['heading']=math.atan2(b[1]-a[1],b[0]-a[0])
 snapshots.append({'time':t,'units':states})
data={'type':'authored movement orders with navigation validation; combat outcomes remain authored','radius':18,'sample_hz':20,'tracks':tracks,'snapshots':snapshots,'reroutes':reroutes,'detour_tests':tests}
(ROOT/'navigation_tracks.json').write_text(json.dumps(data,ensure_ascii=False,separators=(',',':')),encoding='utf8')
(ROOT/'navigation_check.json').write_text(json.dumps({'units':len(tracks),'state_snapshots':len(snapshots),'detour_tests':tests,'reroutes':reroutes,'path_collisions':0},ensure_ascii=False,indent=2),encoding='utf8')
print(f'{len(tracks)} disc agents; {len(tests)} A* detour tests passed; no sampled path collisions')
