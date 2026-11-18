"""Disc-agent navigation. No drawing, weapons, camera or combat adjudication."""
import math, heapq
CELL=10
RADIUS=18
def blocked(p,t):
 x,y=p
 if not 240+RADIUS<=x<=800-RADIUS or y<100+RADIUS or y>1120:return True
 for cx,cy in ((590,550),(315,250)):
  if math.hypot(x-cx,y-cy)<31+RADIUS:return True
 v=max(0,min(1,(t-39)/3));v=v*v*(3-2*v)
 r=(260+140*v,610-80*v,396+140*v,790-80*v)
 q=(max(r[0],min(x,r[2])),max(r[1],min(y,r[3])))
 return math.dist(p,q)<RADIUS
def clear(a,b,t):
 n=max(1,math.ceil(math.dist(a,b)/3))
 return all(not blocked((a[0]+(b[0]-a[0])*i/n,a[1]+(b[1]-a[1])*i/n),t) for i in range(n+1))
def astar(start,goal,t):
 if blocked(start,t) or blocked(goal,t):raise ValueError('Blocked endpoint')
 if clear(start,goal,t):return [start,goal]
 def node(p):return (round(p[0]/CELL),round(p[1]/CELL))
 def pos(n):return(n[0]*CELL,n[1]*CELL)
 # Select a connected grid node instead of snapping through an obstacle.
 def connect(p):
  a=node(p);choices=[(a[0]+dx,a[1]+dy) for dx in range(-2,3) for dy in range(-2,3)]
  return min((n for n in choices if clear(p,pos(n),t)),key=lambda n:math.dist(p,pos(n)))
 s,g=connect(start),connect(goal);todo=[(0,s)];cost={s:0};prev={}
 while todo:
  _,u=heapq.heappop(todo)
  if u==g:break
  for dx,dy in ((1,0),(-1,0),(0,1),(0,-1),(1,1),(1,-1),(-1,1),(-1,-1)):
   v=(u[0]+dx,u[1]+dy)
   if not clear(pos(u),pos(v),t):continue
   nc=cost[u]+math.hypot(dx,dy)
   if nc<cost.get(v,math.inf):
    cost[v]=nc;prev[v]=u;heapq.heappush(todo,(nc+math.dist(v,g),v))
 else:raise ValueError('Unreachable goal')
 out=[g]
 while out[-1]!=s:out.append(prev[out[-1]])
 pts=[start]+[pos(n) for n in reversed(out)]+[goal]
 # Line-of-sight smoothing, still checked against inflated obstacles.
 result=[pts[0]];i=0
 while i<len(pts)-1:
  j=len(pts)-1
  while j>i+1 and not clear(pts[i],pts[j],t):j-=1
  result.append(pts[j]);i=j
 return result
def interpolate(t,keys):
 if t<=keys[0][0]:return tuple(keys[0][1])
 for (s,a),(e,b) in zip(keys,keys[1:]):
  if t<=e:
   v=(t-s)/(e-s);return(a[0]+(b[0]-a[0])*v,a[1]+(b[1]-a[1])*v)
 return tuple(keys[-1][1])
