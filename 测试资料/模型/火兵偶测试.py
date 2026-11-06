from pathlib import Path
import json,collections
wrapper=Path('二维火幕减伤测试.py').read_text(encoding='utf-8-sig').split("exec(compile(src,'二维火幕减伤模型','exec'),globals())")[0]
exec(wrapper,globals())
src=src.replace("Path('二维火幕减伤测试')","Path('火兵偶测试')")
src=src.replace("counts=collections.Counter()","counts=collections.Counter();converted=False;corpse=None")
# Create a placeholder ally excluded from normal enemy loops.
src=src.replace(" def log(s):", " u['F']=dict(pos=(0,0),b=0,down=False,out=True,burn=False,re=1)\n def log(s):")
src=src.replace("armor=2 if t=='P' else 1", "armor=2 if t=='P' else 0 if a=='P' else 1")
src=src.replace("  if res>=9:v['out']=True;out='退场'", "  if res>=9:\n   v['out']=True;out='退场'\n   if t in '12345' and corpse is None and not converted:corpse=t")
src=src.replace(" def atk(a,t,kind):", " def atk(a,t,kind):\n  nonlocal corpse")
src=src.replace("friends=[n for n in '12345' if n!=a and not u[n]['out'] and melee(n,'P')]", "friends=[n for n in '12345' if n!=a and not u[n]['out'] and melee(n,t)]")
src=src.replace("if kind=='射击' and t=='P':", "if kind=='射击' and t in ('P','F'):")
# Conversion requires an action in the next activation, replaces fireball + ordinary attack, aura unaffected.
begin=src.index("  shots=[n for n in live")
end=src.index("  for n in '12345':",begin)
block=src[begin:end]
new="  if corpse is not None and not converted:\n   converted=True;u['F'].update(pos=u[corpse]['pos'],b=0,down=False,out=False);counts['转化']+=1;log('仪式：首名退场士兵转化火兵偶F，替代本次攻击')\n  else:\n"+''.join(' '+line+'\n' for line in block.splitlines())
src=src[:begin]+new+src[end:]
# Soldier target selection: shoot either ally based on ease, melee nearby F if P not nearby.
src=src.replace("   if melee(n,'P'):atk(n,'P','刺刀');continue", "   if melee(n,'P'):atk(n,'P','刺刀')\n   elif not u['F']['out'] and melee(n,'F'):atk(n,'F','刺刀')\n   else:\n    targets=[z for z in ('P','F') if not u[z]['out'] and los(v['pos'],u[z]['pos']) and dist(v['pos'],u[z]['pos'])<=24]\n    if targets:\n     z=min(targets,key=lambda z:int(z=='P')+int(covered(v['pos'],u[z]['pos']))+int(dist(v['pos'],u[z]['pos'])>12));atk(n,z,'射击')\n    else:log(n+'无射线，保留位置')\n   if n==next((z for z in '12345' if not u[z]['out']),None) and not u['F']['out']:\n    f=u['F']\n    if f['down']:f['down']=False;speed=3;log('F起身')\n    else:speed=6\n    enemies=[z for z in '12345' if not u[z]['out']]\n    if enemies:\n     target=min(enemies,key=lambda z:dist(f['pos'],u[z]['pos']))\n     if not melee('F',target):\n      costs,previous=reachable('F',speed);best=min(costs,key=lambda x:(dist(x,u[target]['pos']),costs[x]))\n      if best!=f['pos']:move('F',best,previous)\n     if melee('F',target):counts['兵偶攻击']+=1;atk('F',target,'刺刀')\n   continue")
# The previous movement-and-shoot block after continue is unreachable; retained source does not execute it.
exec(compile(src,'火兵偶模型','exec'),globals())
seeds=[754491237,489690734,3808889068,4280649435,1844120670]
for i,s in enumerate(seeds,1):
 result,logs=run(s,True);(OUT/f'{i}-完整记录.txt').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n\n'+'\n'.join(logs),encoding='utf-8');print(json.dumps({k:v for k,v in result.items() if k!='逐轮'},ensure_ascii=False))
results=[run(s)[0] for s in range(10000,10200)];count=collections.Counter(x['结果'] for x in results);print('BATCH',dict(count))
(OUT/'200场汇总.json').write_text(json.dumps({'结果':dict(count),'场次':results,'限制':'死亡以退场暂代；转化占下次攻击；F独立近战；敌方暂维持射线不重选移动'},ensure_ascii=False),encoding='utf-8')
