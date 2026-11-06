from pathlib import Path
import json,collections
src=Path('二维公国兵测试.py').read_text(encoding='utf-8-sig').split('seeds=[754491237')[0]
src=src.replace("Path('二维公国兵测试')","Path('二维火球冲刺测试')")
src=src.replace("v=u[t];shoot=kind=='射击';e=", "shoot=kind in ('射击','火球')\n  if kind=='射击' and t=='P':\n   friends=[n for n in '12345' if n!=a and not u[n]['out'] and melee(n,'P')]\n   if friends:\n    check=r.randint(1,6);log(f'缠斗误伤骰{check}')\n    if check<=3:t=r.choice(friends);counts['误伤选中']+=1;log('目标改为友军'+t)\n  v=u[t];e=")
src=src.replace("near=[n for n in '12345' if not u[n]['out'] and melee('P',n)]", "near=[n for n in '12345' if not u[n]['out'] and dist(p['pos'],u[n]['pos'])<=2 and los(p['pos'],u[n]['pos'])]")
start=src.index("  adjacent=[n for n in live if melee('P',n)]")
end=src.index("  for n in '12345':",start)
new='''  shots=[n for n in live if dist(p['pos'],u[n]['pos'])<=24 and los(p['pos'],u[n]['pos'])]
  if shots:
   target=min(shots,key=lambda n:(int(covered(p['pos'],u[n]['pos'])),dist(p['pos'],u[n]['pos'])))
   counts['火球']+=1;atk('P',target,'火球')
  live=[n for n in '12345' if not u[n]['out']]
  if live:
   adjacent=[n for n in live if melee('P',n)]
   if adjacent:atk('P',max(adjacent,key=lambda n:u[n]['b']),'普通')
   else:
    budget=3.5 if stood else 7;cost,prev=reachable('P',budget)
    target=min(live,key=lambda n:dist(p['pos'],u[n]['pos']))
    best=min(cost,key=lambda x:(round(dist(x,u[target]['pos']),2),sum(los(v['pos'],x) and not covered(v['pos'],x) for n,v in u.items() if n!='P' and not v['out']),cost[x]))
    if best!=p['pos']:log('火焰冲刺');move('P',best,prev)
    if melee('P',target):atk('P',target,'普通')
'''
src=src[:start]+new+src[end:]
src=src.replace("   if any(k!=n and not u[k]['out'] and melee(k,'P') for k in '12345'):log(n+'避免误伤友军，保持位置');continue", "   # Soldiers may risk shooting into melee; target determined inside atk.")
exec(compile(src,'二维火球冲刺模板','exec'),globals())
seeds=[754491237,489690734,3808889068,4280649435,1844120670]
for i,s in enumerate(seeds,1):
 result,logs=run(s,True);(OUT/f'{i}-完整记录.txt').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n\n'+'\n'.join(logs),encoding='utf-8');print(json.dumps({k:v for k,v in result.items() if k!='逐轮'},ensure_ascii=False))
results=[run(s)[0] for s in range(10000,10200)];count=collections.Counter(x['结果'] for x in results);print('BATCH',dict(count));print('COUNTS',dict(sum((collections.Counter(x['次数']) for x in results),collections.Counter())))
(OUT/'200场汇总.json').write_text(json.dumps({'结果':dict(count),'场次':results},ensure_ascii=False),encoding='utf-8')
