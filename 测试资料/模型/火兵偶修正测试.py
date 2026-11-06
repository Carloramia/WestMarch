from pathlib import Path
import json,collections
exec(Path('火兵偶测试.py').read_text(encoding='utf8').split('# Soldier target selection')[0],globals())
helper=''' def fturn():
  f=u['F']
  if f['out']:return
  speed=3 if f['down'] else 6;f['down']=False
  enemies=[z for z in '12345' if not u[z]['out']]
  if not enemies:return
  target=min(enemies,key=lambda z:dist(f['pos'],u[z]['pos']))
  if not melee('F',target):
   costs,previous=reachable('F',speed);best=min(costs,key=lambda x:(dist(x,u[target]['pos']),costs[x]))
   if best!=f['pos']:move('F',best,previous)
  if melee('F',target):counts['兵偶攻击']+=1;atk('F',target,'刺刀')
'''
src=src.replace(' for turn in range(1,13):',helper+' for turn in range(1,13):')
src=src.replace("   if melee(n,'P'):atk(n,'P','刺刀');continue", "   if melee(n,'P'):atk(n,'P','刺刀');continue\n   if not u['F']['out'] and melee(n,'F'):atk(n,'F','刺刀');continue")
# Keep original enemy movement selection. After movement, choose easier visible target.
src=src.replace("    atk(n,'P','射击')", "    options=[z for z in ('P','F') if not u[z]['out'] and 1.99<dist(v['pos'],u[z]['pos'])<=24 and los(v['pos'],u[z]['pos'])]\n    z=min(options,key=lambda z:int(z=='P')+int(covered(v['pos'],u[z]['pos']))+int(dist(v['pos'],u[z]['pos'])>12)) if options else 'P'\n    atk(n,z,'射击')")
a=src.index("  for n in '12345':\n   if p['out']:break")
b=src.index('  states.append',a)
old=src[a:b].splitlines()[1:]
# Finally executes even after continue, so the ally activates after the first living enemy.
block="  fdone=False\n  for n in '12345':\n   living=not u[n]['out']\n   try:\n"+'\n'.join(' '+line for line in old)+"\n   finally:\n    if living and not fdone and not p['out']:\n     fdone=True;fturn()\n"
src=src[:a]+block+src[b:]
exec(compile(src,'火兵偶修正模型','exec'),globals())
for i,s in enumerate([754491237,489690734,3808889068,4280649435,1844120670],1):
 result,logs=run(s,True);(OUT/f'{i}-完整记录.txt').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n\n'+'\n'.join(logs),encoding='utf-8');print(json.dumps({k:v for k,v in result.items() if k!='逐轮'},ensure_ascii=False))
results=[run(s)[0] for s in range(10000,10200)];count=collections.Counter(x['结果'] for x in results);print('BATCH',dict(count))
(OUT/'200场汇总.json').write_text(json.dumps({'结果':dict(count),'场次':results,'限制':'近似底座与策略；退场暂代死亡；转化占下次攻击；恢复原士兵移动策略；F在首名存活敌人激活后行动'},ensure_ascii=False),encoding='utf8')
