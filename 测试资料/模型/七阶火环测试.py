from pathlib import Path
import json,collections
src=Path('红骑士全攻击加一临时测试.py').read_text(encoding='utf-8-sig').split('seeds=[754491237')[0]
src=src.replace("Path('红骑士全攻击加一测试')","Path('七阶火环测试')")
src=src.replace("result=val+blade+fist-forge-(t=='P')","result=val+blade+fist-forge-2*(t=='P')").replace('int(t=="P")','2*int(t=="P")')
src=src.replace("for v in u.values():v['re']=1","for n,v in u.items():v['re']=2 if n=='P' else 1")
src=src.replace("v['re']=0;reactions", "v['re']-=1;reactions").replace("p['re']=0;reactions", "p['re']-=1;reactions").replace("p['re']=0;ready", "p['re']-=1;ready").replace('反应1→0','消耗反应1')
src=src.replace("  if dist<=1:\n   hit('P',t,'普通')", "  if dist<=1:\n   near=[n for n in live if abs(u[n]['x']-p['x'])<=1]\n   if len(near)>=2:\n    log('火环仪轨：占用仪式位置替代攻击，目标'+','.join(near))\n    for n in near:hit('P',n,'火环')\n   else:hit('P',t,'普通')")
exec(compile(src,'七阶模板','exec'),globals())
seeds=[754491237,489690734,3808889068,4280649435,1844120670]
for i,seed in enumerate(seeds,1):
 s,logs=run(seed,True)
 (OUT/f'{i}-完整记录.txt').write_text(json.dumps(s,ensure_ascii=False,indent=2)+'\n\n'+'\n'.join(logs),encoding='utf-8')
 print(json.dumps({k:v for k,v in s.items() if k!='逐轮'},ensure_ascii=False))
results=[]
for seed in range(10000,11000):
 s,_=run(seed,True);results.append(s)
counts=collections.Counter(s['结果'] for s in results)
print('BATCH',dict(counts),'mean rounds',sum(s['轮数'] for s in results)/len(results))
(OUT/'千场汇总.json').write_text(json.dumps({'假设':'护甲2、反应2、火环邻近多人分别攻击；暂不收额外性相代价；12轮截止','结果':dict(counts),'记录':results},ensure_ascii=False),encoding='utf-8')
