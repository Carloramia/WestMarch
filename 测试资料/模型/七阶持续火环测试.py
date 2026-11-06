from pathlib import Path
import json,collections
src=Path('红骑士全攻击加一临时测试.py').read_text(encoding='utf-8-sig').split('seeds=[754491237')[0]
src=src.replace("Path('红骑士全攻击加一测试')","Path('七阶持续火环测试')")
src=src.replace("(2 if a=='P' else 0)","(3 if a=='P' else 0)")
src=src.replace("result=val+blade+fist-forge-(t=='P')","result=val+blade+fist-forge-2*(t=='P')").replace('int(t=="P")','2*int(t=="P")')
src=src.replace("for v in u.values():v['re']=1","for n,v in u.items():v['re']=2 if n=='P' else 1")
src=src.replace("v['re']=0;reactions", "v['re']-=1;reactions").replace("p['re']=0;reactions", "p['re']-=1;reactions").replace("p['re']=0;ready", "p['re']-=1;ready").replace('反应1→0','消耗反应1')
src=src.replace("  stood=p['down'];p['down']=False", "  near=[n for n in 'ABCDE' if not u[n]['out'] and abs(u[n]['x']-p['x'])<=1]\n  if near:log('持续火环：激活开始结算，不占攻击；目标'+','.join(near))\n  for n in near:hit('P',n,'持续火环')\n  stood=p['down'];p['down']=False")
# Recheck survivors after the aura; do not attack an already removed target.
exec(compile(src,'持续火环模板','exec'),globals())
seeds=[754491237,489690734,3808889068,4280649435,1844120670]
for i,seed in enumerate(seeds,1):
 s,logs=run(seed,True)
 (OUT/f'{i}-完整记录.txt').write_text(json.dumps(s,ensure_ascii=False,indent=2)+'\n\n'+'\n'.join(logs),encoding='utf-8')
 print(json.dumps({k:v for k,v in s.items() if k!='逐轮'},ensure_ascii=False))
results=[run(seed,True)[0] for seed in range(10000,11000)]
counts=collections.Counter(s['结果'] for s in results)
print('BATCH',dict(counts),'平均轮数',sum(s['轮数'] for s in results)/1000)
(OUT/'千场汇总.json').write_text(json.dumps({'假设':'护甲2、反应2、命中5d6取二；火环自身激活开始逐目标结算，不占攻击，无额外性相代价；12轮截止','结果':dict(counts),'记录':results},ensure_ascii=False),encoding='utf-8')
