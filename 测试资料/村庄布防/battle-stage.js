// Persistent SVG scene. Simulation coordinates stay authoritative; recoil is screen-only.
window.createBattleStage=function(svg,data,onPick){
 const NS='http://www.w3.org/2000/svg',nodes=new Map(),effects=[],reduced=matchMedia('(prefers-reduced-motion: reduce)').matches;
 const make=(tag,attrs,parent,text)=>{const n=document.createElementNS(NS,tag);for(const [k,v] of Object.entries(attrs))n.setAttribute(k,v);if(text!==undefined)n.textContent=text;parent.append(n);return n;};
 const set=(n,k,v)=>n.setAttribute(k,v),color=t=>t==='D'?'#e0bb73':'#de8e80',point=p=>[p[0]*20+10,p[1]*20+10],clamp=v=>Math.max(0,Math.min(1,v));
 const scene=make('g',{},svg),terrain=make('g',{},scene),sites=make('g',{'pointer-events':'none'},scene),gates=make('g',{},scene),agents=make('g',{},scene),fx=make('g',{'pointer-events':'none','aria-hidden':'true'},scene);
 const defs=make('defs',{},svg),grid=make('pattern',{id:'village-grid',patternUnits:'userSpaceOnUse',width:40,height:40},defs);
 for(const [x,y,fill] of [[0,0,'#263234'],[20,20,'#263234'],[20,0,'#283537'],[0,20,'#283537']])make('rect',{x,y,width:20,height:20,fill,stroke:'#2c393b','stroke-width':.5},grid);
 let signature='',lastRound=-1,lastView='',lastMode='',raf=0,opts={},audio=null,soundAt=0,soundCount=0,shakeUntil=0,shakePower=0,lastTickTime=0,renderDuration=400;
 function terrainDraw(map,entries){
  const sig=JSON.stringify([map,entries]);if(sig===signature)return;signature=sig;terrain.replaceChildren();
  make('rect',{width:(map.width??32)*20,height:(map.height??24)*20,fill:'url(#village-grid)'},terrain);
  for(const [x,y] of map.blocked)make('rect',{x:x*20+1,y:y*20+1,width:18,height:18,fill:x===14?'#66746b':'#414e4d'},terrain);
  for(const [x,y] of entries){make('rect',{x:x*20,y:y*20,width:20,height:40,fill:'#343b2e',stroke:'#a28a5a'},terrain);make('text',{x:x*20-12,y:y*20+10,fill:'#d0c5a9','font-size':10,'text-anchor':'end'},terrain,`入口 ${y+1}`);}
  for(const [x,y] of map.cover){make('rect',{x:x*20+2,y:y*20+2,width:16,height:16,fill:'#4e7260'},terrain);make('path',{d:`M${x*20+3} ${y*20+16}l12 -12`,stroke:'#8dac81','stroke-width':2},terrain);}
  for(const [x,y] of map.rough)make('rect',{x:x*20+2,y:y*20+2,width:16,height:16,fill:'#725b42'},terrain);
  for(const slit of map.slits||[]){
   const [x,y]=point(slit.pos),[dx,dy]=slit.inward;
   make('rect',{x:x-8,y:y-8,width:16,height:16,rx:3,fill:'#2f4c4c',stroke:'#91cfd0','stroke-width':1,'data-firing-point':slit.name},terrain);
   make('path',{d:`M ${x} ${y} l ${-dx*13} ${-dy*13} m ${dx*4-dy*4} ${dy*4+dx*4} l ${-dx*4+dy*4} ${-dy*4-dx*4} l ${dx*4+dy*4} ${dy*4-dx*4}`,fill:'none',stroke:'#a5e4e7','stroke-width':1.4},terrain);
  }
  const [x,y]=data.map.stock;make('rect',{x:x*20-2,y:y*20-2,width:24,height:24,fill:'none',stroke:'#8bb5a3','stroke-width':2},terrain);make('text',{x:x*20+10,y:y*20-10,fill:'#c8d4c9','font-size':13,'text-anchor':'middle'},terrain,'粮仓');if(!map.slits)make('text',{x:22,y:465,fill:'#c8d4c9','font-size':12},terrain,'西侧撤离 ←');
 }
 function gateDraw(structures){
  gates.replaceChildren();
  for(const g of structures||[]){
   const icons=(g.upgrades||[]).map(key=>({reinforce:'▓',tower:'塔',ballista:'弩'}[key])).join(' ');
   if(icons){const [x,y]=point(g.cells[0]),[dx,dy]=g.inward||[1,0];make('text',{x:x+dx*20,y:y+dy*20+4,'font-size':9,'text-anchor':'middle',fill:'#cfefe3','data-fortification':g.id},gates,icons);}
   for(const [x,y] of g.cells)make('rect',{x:x*20+2,y:y*20+2,width:16,height:16,fill:g.hp>0?'#967348':'#393e35',stroke:g.hp>0?'#e0bb73':'#66746b'},gates);const [x,y]=g.cells[0];make('rect',{x:x*20-8,y:y*20-9,width:36,height:3,fill:'#172125'},gates);make('rect',{x:x*20-8,y:y*20-9,width:36*g.hp/(g.max_hp||g.hp||1),height:3,fill:'#e0bb73'},gates);make('text',{x:x*20+10,y:y*20-14,'text-anchor':'middle',fill:'#f0d5a4','font-size':9,stroke:'#202b2d','stroke-width':2,'paint-order':'stroke'},gates,`${g.name} ${g.hp}/${g.max_hp||g.hp}`);}
 }
 function siteDraw(items){
  sites.replaceChildren();
  for(const site of items||[]){
   const [x,y]=point(site.pos),ink=site.status==='争夺中'?'#e59380':site.status==='缺少守军'?'#a6b1aa':'#a8d2a4';
   make('rect',{x:x-8,y:y-8,width:16,height:16,rx:3,fill:'#273b32',stroke:ink,'data-production-site':site.id},sites);
   make('text',{x,y:y+18,fill:ink,'font-size':9,'text-anchor':'middle',stroke:'#243132','stroke-width':2,'paint-order':'stroke'},sites,site.name);
  }
 }
 function actor(u){
  const g=make('g',{class:'unit',tabindex:0,role:'button','data-unit-id':u.id,'aria-label':`${u.id} ${data.types[u.kind].label}`},agents);
  make('circle',{r:10,fill:'transparent','pointer-events':'all'},g);
  const ring=make('circle',{r:11,fill:'none',stroke:'#e7ebe5','stroke-width':1},g),body=make('circle',{r:6.5,'stroke-width':1.5},g),heading=make('path',{d:'M5 0 L-2.4 1.8 L-2.4 -1.8 Z',fill:'#172125'},g),cross=make('path',{d:'M-3 -3L3 3M3 -3L-3 3','stroke-width':1.2},g),route=make('circle',{r:9,fill:'none',stroke:'#efab73','stroke-dasharray':'2 2'},g),cargo=make('circle',{cx:8,cy:-7,r:2.5,fill:'#b0d5bf'},g),label=make('text',{class:'unit-name',x:0,y:-13,fill:'#eef0e8','font-size':10,'text-anchor':'middle',stroke:'#202b2d','stroke-width':2.5,'paint-order':'stroke'},g);
  g.onclick=()=>onPick(u.id);g.onkeydown=e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();onPick(u.id);}};
  const p=point(u.pos);return {g,ring,body,heading,cross,route,cargo,label,x:p[0],y:p[1],path:[p],start:0,duration:0,holdUntil:0,flashUntil:0,flashColor:'#fff3d1',angle:u.heading||0,angleFrom:u.heading||0,angleTo:u.heading||0,angleStart:0,angleDuration:0,kick:null,u};
 }
 function position(n,now){
  const t=clamp((now-n.start)/Math.max(n.duration,1)),path=n.path,part=t*(path.length-1),i=Math.min(path.length-2,Math.floor(part)),v=part-i;
  if(path.length===1)return path[0];return [path[i][0]+(path[i+1][0]-path[i][0])*v,path[i][1]+(path[i+1][1]-path[i][1])*v];
 }
 function sound(kind,metal,pan=0,delay=0){
  if(!audio||audio.state!=='running'||!document.getElementById('sound-fx').checked)return;
  const now=audio.currentTime+delay;if(now-soundAt>.15){soundAt=now;soundCount=0;}if(soundCount++>=5)return;
  const vol=kind==='breach'?.055:kind==='disabled'?.04:kind==='miss'?.008:.025;
  const gain=audio.createGain(),panner=audio.createStereoPanner();gain.gain.setValueAtTime(vol,now);gain.gain.exponentialRampToValueAtTime(.0001,now+.23);panner.pan.value=Math.max(-.75,Math.min(.75,pan));gain.connect(panner);panner.connect(audio.destination);
  for(const [hz,mix] of [[kind==='breach'?55:85,1],...(metal?[[690,.22],[1810,.05]]:[])]){const o=audio.createOscillator(),g=audio.createGain();o.frequency.setValueAtTime(hz,now);o.frequency.exponentialRampToValueAtTime(hz*.55,now+.16);g.gain.value=mix;o.connect(g);g.connect(gain);o.start(now);o.stop(now+.24);}
  const buf=audio.createBuffer(1,Math.ceil(audio.sampleRate*.1),audio.sampleRate),a=buf.getChannelData(0);let seed=7;for(let i=0;i<a.length;i++){seed=(seed*16807)%2147483647;a[i]=(seed/2147483647-.5)*.3;}const noise=audio.createBufferSource();noise.buffer=buf;noise.connect(gain);noise.start(now);noise.stop(now+.11);
 }
 function pulse(at,p,col,kind,dir,text='',delay=0){
  const g=make('g',{'data-effect':kind},fx),ring=make('circle',{cx:p[0],cy:p[1],r:4,fill:'none',stroke:col,'stroke-width':1.7},g),flash=make('circle',{cx:p[0],cy:p[1],r:kind==='breach'?10:5,fill:col},g),label=text?make('text',{x:p[0],y:p[1]-20,'text-anchor':'middle','font-size':kind==='disabled'?13:10,fill:col,stroke:'#172125','stroke-width':2,'paint-order':'stroke'},g,text):null;
  const count=kind==='miss'?2:kind==='breach'?13:kind==='disabled'?10:6,particles=[];
  for(let i=0;i<count;i++){const a=(i*2.399)+(dir||0),r=kind==='breach'?18+i%5*3:8+i%4*3;particles.push({n:make('rect',{x:p[0],y:p[1],width:kind==='breach'?2.5:1.6,height:kind==='breach'?2.5:1.6,fill:col},g),dx:Math.cos(a)*r,dy:Math.sin(a)*r});}
  effects.push({g,start:at+delay,duration:kind==='breach'?620:kind==='disabled'?520:330,paint(t){set(ring,'r',4+t*(kind==='breach'?32:19));set(ring,'opacity',1-t);set(flash,'opacity',Math.max(0,1-t*5));for(const q of particles){set(q.n,'x',p[0]+q.dx*t);set(q.n,'y',p[1]+q.dy*t+t*t*6);set(q.n,'opacity',1-t);}if(label){set(label,'y',p[1]-18-t*13);set(label,'opacity',Math.min(1,(1-t)*2));}}});
 }
 function lineEffect(at,a,b,col,ranged,delay){
  const line=make('line',{x1:a[0],y1:a[1],x2:a[0],y2:a[1],stroke:col,'stroke-width':ranged?1.7:2.3,'stroke-linecap':'round','data-effect':ranged?'projectile':'strike'},fx);
  effects.push({g:line,start:at,duration:delay+120,paint(t){const travel=clamp(t*(delay+120)/delay),tail=ranged?Math.max(0,travel-.18):0;set(line,'x1',a[0]+(b[0]-a[0])*tail);set(line,'y1',a[1]+(b[1]-a[1])*tail);set(line,'x2',a[0]+(b[0]-a[0])*travel);set(line,'y2',a[1]+(b[1]-a[1])*travel);set(line,'opacity',1-clamp((t-.55)/.45));}});
 }
 function eventFeedback(frame,events,shown,now){
  const showImpacts=document.getElementById('impact-fx').checked;
  const ids=new Map(shown.map(u=>[u.id,u]));let offset=0;
  for(const e of events){
   if(e.kind==='scout_call'){
    const [x,y]=point(e.pos);
    const ring=make('circle',{cx:x,cy:y,r:0,fill:'none',stroke:'#90e3ca','stroke-width':2,'data-effect':'scout-call'},fx);
    effects.push({g:ring,start:now,duration:1250,paint:t=>{set(ring,'r',e.radius*20*(.1+.9*t));set(ring,'opacity',.85*(1-t));}});
    pulse(now,[x,y],'#90e3ca','scout-call-label',0,'斥候呼援');continue;
   }
   if(!showImpacts)continue;
   if(e.kind==='ballista'){
    const origin=point(e.pos),target=point(e.target_pos);
    lineEffect(now,origin,target,'#f3d888',true,120);
    pulse(now,target,'#f3d888','ballista',0,e.hit?'弩炮命中':'弩炮落空',120);continue;
   }
   if(!['attack','siege','breach','heal','rout'].includes(e.kind))continue;
   const a=nodes.get(e.actor),u=ids.get(e.target),target=u&&nodes.get(e.target);if(!a)continue;
   const aPos=position(a,now),delay=e.kind==='attack'?(e.ranged?100:65):65;
   let p=target?position(target,now):null;
   if(e.gate){const g=frame.structures?.find(g=>g.id===e.gate);if(g)p=point(g.cells.reduce((best,q)=>Math.hypot(q[0]*20+10-aPos[0],q[1]*20+10-aPos[1])<Math.hypot(best[0]*20+10-aPos[0],best[1]*20+10-aPos[1])?q:best,g.cells[0]));}
   if(e.kind==='attack'&&!p)continue;
   const col=e.kind==='heal'?'#a4d7b9':e.kind==='breach'?'#f4d69b':e.outcome==='miss'?'#8c9c99':color(a.u.team),at=now+offset;
   if(e.kind==='rout'){pulse(at,aPos,'#efab73','rout',0,'溃逃');continue;}
   if(e.kind==='heal'){if(p)pulse(at,p,col,'heal',0,'救护',50);continue;}
   if(!p)continue;
   const dx=p[0]-aPos[0],dy=p[1]-aPos[1],angle=Math.atan2(dy,dx),kind=e.kind==='breach'?'breach':e.kind==='siege'?'siege':e.outcome||'blocked';
   if(e.kind!=='breach')lineEffect(at,aPos,p,col,!!e.ranged,delay);
   if(!e.ranged)a.kick={start:at,duration:180,dx:Math.cos(angle)*3,dy:Math.sin(angle)*3};
   const damaging=kind==='injury'||kind==='disabled',text=kind==='siege'?`−${e.damage}`:kind==='breach'?'破门':kind==='disabled'?'失能':kind==='injury'?'受伤':kind==='miss'?'落空':e.armored?'护甲抵御':'未致伤';
   pulse(at,p,damaging?'#f2bea0':col,kind,angle,text,delay);
   if(target&&kind!=='miss'&&!target.u.ghost){target.flashStart=at+delay;target.flashUntil=at+delay+115;target.holdStart=at+delay;target.holdUntil=reduced?0:at+delay+40;target.kick={start:at+delay,duration:240,dx:Math.cos(angle)*(damaging?4.5:2),dy:Math.sin(angle)*(damaging?4.5:2)};}
   if((kind==='disabled'||kind==='breach')&&!reduced){shakeUntil=at+delay+170;shakePower=kind==='breach'?1.5:.8;}
   sound(kind,e.armored||kind==='siege'||kind==='breach',(p[0]-320)/400,delay/1000);offset=Math.min(100,offset+12);
  }
 }
 function run(now){
  raf=0;let moving=false;
  for(const n of nodes.values()){
   let p=position(n,now); // Sampling is visual only.
   if(n.holdUntil>now&&now>=n.holdStart)p=[n.x,n.y];
   n.x=p[0];n.y=p[1];let kx=0,ky=0;
   if(n.kick&&now>=n.kick.start){const t=(now-n.kick.start)/n.kick.duration;if(t<1){const amp=Math.sin(Math.PI*t)*Math.exp(-t*2);kx=n.kick.dx*amp;ky=n.kick.dy*amp;moving=true;}else n.kick=null;}
   const turn=clamp((now-n.angleStart)/Math.max(n.angleDuration,1));n.angle=n.angleFrom+(n.angleTo-n.angleFrom)*(turn*turn*(3-2*turn));set(n.heading,'transform',`rotate(${n.angle*180/Math.PI})`);if(turn<1)moving=true;
   set(n.g,'transform',`translate(${(n.x+kx).toFixed(2)} ${(n.y+ky).toFixed(2)})`);
   const flash=now>=n.flashStart&&now<n.flashUntil;set(n.body,'fill',flash?'#fff0cb':n.u.ghost?'none':n.u.active?color(n.u.team):'#4d5955');
   if(now<n.start+n.duration||flash||n.holdUntil>now)moving=true;
  }
  for(let i=effects.length-1;i>=0;i--){const e=effects[i],elapsed=now-e.start;if(elapsed<0){set(e.g,'visibility','hidden');moving=true;continue;}if(elapsed>=e.duration){e.g.remove();effects.splice(i,1);continue;}set(e.g,'visibility','visible');e.paint(elapsed/e.duration);moving=true;}
  if(now<shakeUntil&&document.getElementById('screen-shake').checked){const amp=shakePower*clamp((shakeUntil-now)/170);set(scene,'transform',`translate(${Math.sin(now*.12)*amp} ${Math.cos(now*.094)*amp*.6})`);moving=true;}else scene.removeAttribute('transform');
  if(moving)raf=requestAnimationFrame(run);
 }
 function wake(){if(!raf)raf=requestAnimationFrame(run);}
 function clear(){for(const e of effects)e.g.remove();effects.length=0;shakeUntil=0;for(const n of nodes.values()){n.kick=null;n.flashUntil=0;n.holdUntil=0;}}
 return {
  unlock(){try{audio??=new(window.AudioContext||window.webkitAudioContext)();audio.resume().catch(()=>{});}catch{}},
  render(frame,shown,events,selected,settings){
   opts=settings;const now=performance.now(),sameContext=lastView===settings.view&&lastMode===settings.mode,advance=sameContext&&frame.round===lastRound+1,animate=advance&&settings.live&&!settings.paused&&!reduced;
   if(!sameContext||frame.round<lastRound||settings.editing)clear();
   terrainDraw(settings.terrain,settings.gates);siteDraw(frame.sites);gateDraw(frame.structures);
   if(advance){renderDuration=400/settings.speed;if(lastTickTime){const measured=now-lastTickTime;renderDuration=Math.max(renderDuration,Math.min(measured,renderDuration*1.3));}lastTickTime=now;}
   const visible=new Set(shown.map(u=>u.id));for(const [id,n] of nodes)if(!visible.has(id)){n.g.remove();nodes.delete(id);}
   for(const u of shown){let n=nodes.get(u.id);if(!n){n=actor(u);nodes.set(u.id,n);}const dest=point(u.pos),from=position(n,now);n.u=u;
    if(frame.round!==lastRound||!sameContext||settings.editing){n.path=animate?[from,...(u.motion?.slice(1).map(point)||[dest])]:[dest];if(n.path.length===1||n.path.at(-1)[0]!==dest[0]||n.path.at(-1)[1]!==dest[1])n.path.push(dest);n.start=now;n.duration=animate?renderDuration:0;n.angleFrom=n.angle;n.angleTo=n.angle+Math.atan2(Math.sin((u.heading||0)-n.angle),Math.cos((u.heading||0)-n.angle));n.angleStart=now;n.angleDuration=animate?Math.min(130,renderDuration):0;}
    const col=color(u.team);set(n.ring,'visibility',selected===u.id?'visible':'hidden');set(n.body,'stroke',!u.ghost&&u.vigor?'#c4f4a9':col);set(n.body,'stroke-dasharray',u.ghost?'3 2':'none');set(n.g,'opacity',u.ghost?.65:1);set(n.heading,'visibility',u.active&&!u.ghost?'visible':'hidden');set(n.cross,'visibility',u.active?'hidden':'visible');set(n.cross,'stroke',col);set(n.route,'visibility',u.routed?'visible':'hidden');set(n.cargo,'visibility',u.cargo?'visible':'hidden');n.label.textContent=(u.name||data.types[u.kind].label+u.id)+(u.routed?' · 逃':!u.ghost&&u.vigor?' · 精力充沛':!u.ghost&&u.rotation_state==='接岗中'?' · 接岗':!u.ghost&&u.rotation_state==='休整'?' · 休整':'');
   }
   if(advance&&!settings.editing&&(!settings.paused||settings.single))eventFeedback(frame,events,shown,now);
   lastRound=frame.round;lastView=settings.view;lastMode=settings.mode;wake();
  },
  debug(){return {actors:nodes.size,effects:effects.length,staticNodes:terrain.childElementCount,animating:!!raf};}
 };
};
