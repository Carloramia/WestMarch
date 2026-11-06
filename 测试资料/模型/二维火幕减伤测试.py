from pathlib import Path
import json,collections
# Load the previous generated model without running its test batch.
wrapper=Path('二维火球冲刺测试.py').read_text(encoding='utf-8-sig').split("exec(compile(src,'二维火球冲刺模板','exec'),globals())")[0]
exec(wrapper,globals())
src=src.replace("Path('二维火球冲刺测试')","Path('二维火幕减伤测试')")
src=src.replace("v=u[t];e=", "v=u[t];e=")
src=src.replace("e-=int(cov)+int(long)","e-=int(cov)+int(long)+int(shoot and t=='P')")
src=src.replace("res=val+int(a=='P')+blade-forge-armor", "burnmit=int(t=='P' and u[a]['burn']);res=val+int(a=='P')+blade-forge-armor-burnmit")
src=src.replace('护甲-{armor} = {res}', '护甲-{armor} 燃烧减伤-{burnmit} = {res}')
# Prefer clear fire and cover instead of approaching the nearest target regardless of exposure.
old="best=min(cost,key=lambda x:(round(dist(x,u[target]['pos']),2),sum(los(v['pos'],x) and not covered(v['pos'],x) for n,v in u.items() if n!='P' and not v['out']),cost[x]))"
new="""def score(x):
     exposed=sum((0.5 if covered(v['pos'],x) else 1.0)*(0.5 if v['burn'] else 1.0) for n,v in u.items() if n!='P' and not v['out'] and dist(v['pos'],x)<=24 and los(v['pos'],x))
     shots=any(dist(x,u[n]['pos'])<=24 and los(x,u[n]['pos']) for n in live)
     close=sum(dist(x,u[n]['pos'])<=1.99 and los(x,u[n]['pos']) for n in live)
     return (0 if shots else 4)+exposed*2-min(close,1)*0.7+min(dist(x,u[n]['pos']) for n in live)*0.05+cost[x]*0.03
    best=min(cost,key=score)"""
assert old in src
src=src.replace(old,new)
exec(compile(src,'二维火幕减伤模型','exec'),globals())
seeds=[754491237,489690734,3808889068,4280649435,1844120670]
for i,s in enumerate(seeds,1):
 result,logs=run(s,True);(OUT/f'{i}-完整记录.txt').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n\n'+'\n'.join(logs),encoding='utf-8');print(json.dumps({k:v for k,v in result.items() if k!='逐轮'},ensure_ascii=False))
results=[run(s)[0] for s in range(10000,10200)];count=collections.Counter(x['结果'] for x in results);print('BATCH',dict(count))
(OUT/'200场汇总.json').write_text(json.dumps({'假设':'火幕远程命中-1骰；燃烧敌人对P造伤结果-1；可与护甲掩体叠加；改进寻掩体策略非全局最优；其余沿用上版','结果':dict(count),'场次':results},ensure_ascii=False),encoding='utf-8')
