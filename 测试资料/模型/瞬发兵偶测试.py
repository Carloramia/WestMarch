from pathlib import Path
import json,collections
exec(Path('火兵偶修正测试.py').read_text(encoding='utf8').split("exec(compile(src,'火兵偶修正模型','exec'),globals())")[0],globals())
src=src.replace("Path('火兵偶测试')","Path('瞬发兵偶测试')")
a=src.index('  if corpse is not None and not converted:')
b=src.index('  fdone=False',a)
block=src[a:b];body=block[block.index('  else:\n')+len('  else:\n'):]
src=src[:a]+''.join(line[1:]+'\n' for line in body.splitlines())+src[b:]
src=src.replace('  nonlocal corpse','  nonlocal corpse,converted')
old="if t in '12345' and corpse is None and not converted:corpse=t"
new="""if t in '12345' and corpse is None and not converted:
    corpse=t;converted=True;u['F'].update(pos=v['pos'],b=0,down=False,out=False);counts['转化']+=1;log('瞬发转化：'+t+'成为F，不占攻击，不立即插入攻击')"""
assert old in src
src=src.replace(old,new)
exec(compile(src,'瞬发兵偶模型','exec'),globals())
seeds=[754491237,489690734,3808889068,4280649435,1844120670]
for i,s in enumerate(seeds,1):
 result,logs=run(s,True);(OUT/f'{i}-完整记录.txt').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n\n'+'\n'.join(logs),encoding='utf-8');print(json.dumps({k:v for k,v in result.items() if k!='逐轮'},ensure_ascii=False))
results=[run(s)[0] for s in range(10000,10200)];count=collections.Counter(x['结果'] for x in results);print('BATCH',dict(count))
print('MEANS',sum(x['轮数'] for x in results)/200,'Fattacks',sum(x['次数'].get('兵偶攻击',0) for x in results))
(OUT/'200场汇总.json').write_text(json.dumps({'结果':dict(count),'场次':results,'假设':'仅转化瞬发化；退场暂代死亡，无额外性相代价；F继承普通士兵近战面板，独立激活'},ensure_ascii=False),encoding='utf8')
