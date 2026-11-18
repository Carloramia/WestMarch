// Deployment is separate from authoritative replay frames: returning never moves starting pieces.
window.createSandbox=function(data,draw,stop){
 const $=id=>document.getElementById(id);
 const initial=data.replays[0].frames[0].units.map(({id,team,kind,pos})=>({id,team,kind,pos:[...pos],skills:[kind],mission:['D1','D2'].includes(id)?'reserve':id==='D3'?'stock':'hold',name:data.types[kind].label+' '+id,equipment:{armor:false,weapon:'default',banner:false},morale_threshold:5}));
 function defaults(){
  const terrain={blocked:structuredClone(data.map.blocked),cover:[[13,4],[13,11],[15,11],[17,7],[23,8],[24,8],[17,17],[24,18]],rough:[[9,9],[10,9],[11,9],[9,10],[10,10],[11,10],[21,17],[22,17],[23,17]]};
  // Additional north, middle and south passages, plus broken approach walls.
  terrain.blocked=terrain.blocked.filter(([x,y])=>x!==14||![2,3,11,12,21,22].includes(y));
  for(const y of [3,4,5,12,13,14,20,21])terrain.blocked.push([8,y]);
  for(const x of [18,19,20,24,25])terrain.blocked.push([x,18]);
  return {authority:{D:2,A:2},minimum_watch:1,alarm_bell:false,units:structuredClone(initial),intel:{D:[],A:[]},gates:[2,6,11,17,21].map((y,i)=>({id:'G'+(i+1),name:'城门 '+(i+1),hp:20,cells:[[14,y],[14,y+1]]})),morale:{interval:5,chance:.25},terrain,stats:Object.fromEntries(Object.entries(data.types).map(([k,v])=>[k,{sight:v.sight,reach:v.reach,hit:v.hit,injury:v.injury,speed:1,treatments:2}]))};
 }
 let tutorialBackup=null;
 let config=defaults(),editing=true,replay=null,selected=null,drag=null,busy=false,painting=false,live=false,paused=false,session=null,tickTimer=null,inflight=false,epoch=0,opened=null,lastPick={id:null,time:0},selectedGate=null;
 let campaign=null,campaignCatalog=null,sandboxBackup=null,retryToken=null,orderPending=false;
 let settlement=null,settlementKey=null;
 const map=$('map');
 let mapSize=[640,480], mapView=[0,0,640,480], zoom=1, panMode=false, space=false, pan=null, overMap=false;
 function world(e){
  return new DOMPoint(e.clientX,e.clientY).matrixTransform(map.getScreenCTM().inverse());
 }
 function camera(cx,cy,factor){
  zoom=Math.max(1,Math.min(3.5,factor));
  const [width,height]=mapSize, fitHeight=Math.max(height,width*0.75), h=fitHeight/zoom,w=h*4/3;
  const bound=(center,extent,size)=>extent>=size?(size-extent)/2:Math.max(0,Math.min(size-extent,center-extent/2));
  mapView=[bound(cx,w,width),bound(cy,h,height),w,h];map.setAttribute('viewBox',mapView.join(' '));
 }
 function fitMap(){camera(mapSize[0]/2,mapSize[1]/2,1);}
 function zoomMap(factor,e){
  const [x,y,w,h]=mapView, point=e?world(e):{x:x+w/2,y:y+h/2};
  const scale=zoom/Math.max(1,Math.min(3.5,zoom*factor));
  camera(point.x+(x+w/2-point.x)*scale,point.y+(y+h/2-point.y)*scale,zoom*factor);
 }
 function locate(position){camera(position[0]*20+10,position[1]*20+10,Math.max(zoom,1.7));}
 function setMap(){
  mapSize=[(config.terrain.width??32)*20,(config.terrain.height??24)*20];
  $('map-locate').replaceChildren(new Option('定位地点',''),...[
   {name:'粮仓',pos:data.map.stock},...config.gates.map(g=>({name:g.name,pos:g.cells[0]})),...(settlement?.sites??[]),
  ].map(p=>new Option(p.name,p.pos.join(','))));
  fitMap();
 }
 $('map-pan').onclick=()=>{
  panMode=!panMode;$('map-pan').setAttribute('aria-pressed',panMode);map.toggleAttribute('data-pan',panMode);
 };
 $('map-in').onclick=()=>zoomMap(1.3);$('map-out').onclick=()=>zoomMap(1/1.3);$('map-fit').onclick=fitMap;
 $('map-locate').onchange=e=>{if(e.target.value)locate(e.target.value.split(',').map(Number));e.target.value='';};
 map.addEventListener('wheel',e=>{e.preventDefault();zoomMap(e.deltaY<0?1.15:1/1.15,e);},{passive:false});
 map.addEventListener('pointerenter',()=>{overMap=true;});
 map.addEventListener('pointerleave',()=>{overMap=false;});
 document.addEventListener('keydown',e=>{
  if(e.code==='Space'&&!e.target.closest('input,select,textarea,button,[contenteditable]')&&(overMap||map.contains(e.target))){
   space=true;e.preventDefault();
  }
 });
 document.addEventListener('keyup',e=>{if(e.code==='Space')space=false;});
 window.addEventListener('blur',()=>{space=false;});
 map.addEventListener('pointerdown',e=>{
  if(e.button!==1&&!(e.button===0&&(space||panMode)))return;
  const scale=map.getScreenCTM();
  pan={id:e.pointerId,x:e.clientX,y:e.clientY,scale:scale.a,view:mapView};
  map.setPointerCapture(e.pointerId);map.setAttribute('data-dragging','');
  e.preventDefault();e.stopImmediatePropagation();
 },true);
 map.addEventListener('pointermove',e=>{
  if(pan?.id!==e.pointerId)return;
  const [x,y,w,h]=pan.view;
  camera(x+w/2-(e.clientX-pan.x)/pan.scale,y+h/2-(e.clientY-pan.y)/pan.scale,zoom);
  e.stopImmediatePropagation();
 },true);
 for(const type of ['pointerup','pointercancel','lostpointercapture'])map.addEventListener(type,e=>{
  if(pan?.id!==e.pointerId)return;
  pan=null;map.removeAttribute('data-dragging');e.stopImmediatePropagation();
 },true);
 for(const type of ['click','dblclick'])map.addEventListener(type,e=>{if(panMode||space)e.stopImmediatePropagation();},true);
 function applySettlement(state){
  settlement=state;
  for(const unit of config.units){
   const learned=state.skills[unit.id];
   unit.skills=[...new Set([...unit.skills,...learned])];
   unit.free_skill=learned[0]??null;
  }
 }
 async function queueWork(target,kind){
  if(busy)return;
  busy=true;draw();
  try{
   const update=await post('/api/settlement',{action:'queue',key:settlementKey,target,kind});
   applySettlement(update.settlement);msg('已排入队列，推进时间后开始结算。');
  }catch(error){msg(error.message);}
  finally{busy=false;refresh();}
 }
 function campaignSpend(){
  const costs=campaignCatalog.costs;
  const structures=settlement?0:Object.values(config.fortifications).flat().reduce((sum,key)=>sum+costs.structures[key],0);
  return config.units.reduce((total,u)=>total+(settlement?0:u.skills.reduce((sum,key)=>sum+(key===u.free_skill?0:costs.skills[key]),0))
    +costs.weapons[u.equipment.weapon]+Number(u.equipment.armor)*costs.armor+Number(u.equipment.banner)*costs.banner,structures);
 }
 function campaignGateDetails(container,gate){
  $('unit-title').textContent=gate.name+' · 城防设施';
  container.replaceChildren();
  if(settlement){
   const current=settlement.gates.find(g=>g.id===gate.id);
   const hp=document.createElement('p');hp.textContent=`城门 ${current.hp} / ${current.max_hp}`;container.append(hp);
   for(const [key,[name,cost,time]] of Object.entries(settlement.work)){
    const button=document.createElement('button');button.textContent=`${name} · ${cost} 工料 · ${time} 步`;
    button.disabled=busy||settlement.phase!=='safe'||settlement.resources.materials<cost||settlement.jobs.some(j=>!j.training)
      ||current.upgrades.includes(key)||(key==='repair'&&current.hp===current.max_hp);
    button.onclick=()=>queueWork(gate.id,key);container.append(button);
   }
   return;
  }
  const upgrades=config.fortifications[gate.id]??=[];
  const choices=[
   ['reinforce','加固城门','城门最大血量 +10'],
   ['tower','瞭望塔','12 格警戒，可观察外墙之外'],
   ['ballista','弩炮','射程 8 格，每 3 步可射一次，需有守军在门内附近']
  ];
  for(const [key,name,description] of choices){
   const label=document.createElement('label');
   const checkbox=document.createElement('input');checkbox.type='checkbox';checkbox.id='campaign-'+key;checkbox.checked=upgrades.includes(key);
   checkbox.onchange=()=>{
    if(checkbox.checked)upgrades.push(key);else upgrades.splice(upgrades.indexOf(key),1);
    if(campaignSpend()>campaign.budget){upgrades.pop();msg('点数不足，未购买该设施。');}
    refresh();
   };
   label.textContent=name+' · '+campaignCatalog.costs.structures[key]+' 点';
   const hint=document.createElement('small');hint.textContent=description;
   label.append(checkbox,hint);container.append(label);
  }
 }
 function displayedStructures(){
  if(settlement)return settlement.gates;
  return config.gates.map(g=>{
   const upgrades=campaign?(config.fortifications[g.id]||[]):null;
   const hp=g.hp+(upgrades?.includes('reinforce')?10:0);
   return {...g,hp,max_hp:hp,...(upgrades?{upgrades}:{})};
  });
 }
 function campaignDetails(container,u){
  $('unit-title').textContent=u?u.name:'守军训练与配装';
  container.replaceChildren();
  const note=document.createElement('p');
  note.textContent=settlement?(u?`经验 ${settlement.xp[u.id]} · ${['新兵','熟练','老兵'][settlement.ranks[u.id]]} · 每阶命中 +5 个百分点，溃逃阈值 -1`:'点守军训练，点城门施工。装备使用布防点数。')
    :u?'守军自带基础攻防。第一项训练免费，后续训练及装备扣除点数。':'拖动守军调整位置。点击任一棋子，查看训练和装备。点城门购买城防设施。';
  container.append(note);
  if(!u)return;
  const firingPoint=campaign.terrain.slits.find(point=>point.pos[0]===u.pos[0]&&point.pos[1]===u.pos[1]);
  if(firingPoint){
   const hint=document.createElement('p');
   const ready=u.skills.includes('archer')&&u.equipment.weapon==='ranged';
   hint.textContent=firingPoint.name+(ready?' · 已具备向城外射击的条件':' · 需要射手训练和远程武器');
   container.append(hint);
  }
  const costs=campaignCatalog.costs;
  function buy(change,rollback){
   change();
   if(campaignSpend()>campaign.budget){
    rollback();msg('点数不足，购买未生效。');refresh();return;
   }
   refresh();
  }
  function field(text,control){
   const label=document.createElement('label');label.textContent=text;label.append(control);container.append(label);
  }
  const order=document.createElement('ol');
  for(const [index,key] of u.skills.entries()){
   const row=document.createElement('li');row.textContent=campaignCatalog.skills[key]+(key===u.free_skill?'（免费） ':' ');
   for(const [delta,text] of [[-1,'↑'],[1,'↓']]){
    const button=document.createElement('button');button.type='button';button.textContent=text;
    button.setAttribute('aria-label',campaignCatalog.skills[key]+(delta<0?'上移':'下移'));
    button.disabled=index+delta<0||index+delta>=u.skills.length;
    button.onclick=()=>{[u.skills[index],u.skills[index+delta]]=[u.skills[index+delta],u.skills[index]];refresh();};
    row.append(button);
   }
   if(!settlement){
    const remove=document.createElement('button');remove.type='button';remove.textContent='退回';
    remove.onclick=()=>{u.skills.splice(index,1);if(key===u.free_skill)u.free_skill=u.skills[0]??null;refresh();};row.append(remove);
   }
   order.append(row);
  }
  container.append(order);
  const training=document.createElement('select');training.id='campaign-training';training.add(new Option('选择要购买的训练',''));
  for(const [key,cost] of Object.entries(costs.skills))if(!u.skills.includes(key)){
   const option=new Option(campaignCatalog.skills[key]+(u.skills.length?' · '+cost+(settlement?' 补给':' 点'):' · 免费')+(settlement?' · 3 步':''),key);
   option.disabled=!!settlement&&u.skills.length>0&&cost>settlement.resources.supplies;training.add(option);
  }
  if(settlement)training.disabled=busy||settlement.phase!=='safe'||settlement.jobs.some(j=>j.target===u.id)||settlement.jobs.filter(j=>j.training).length>=2;
  training.onchange=()=>{
   if(!training.value)return;
   if(settlement){queueWork(u.id,training.value);return;}
   const free=u.free_skill;
   buy(()=>{if(!u.skills.length)u.free_skill=training.value;u.skills.push(training.value);},()=>{u.skills.pop();u.free_skill=free;});
  };
  field(settlement?'安排训练':'购买训练',training);
  const weapon=document.createElement('select');weapon.id='campaign-weapon';
  const names={none:'无武器',melee:'近战武器',ranged:'远程武器'};
  for(const [key,cost] of Object.entries(costs.weapons))weapon.add(new Option(names[key]+' · '+cost+' 点',key));
  weapon.value=u.equipment.weapon;
  weapon.onchange=()=>{const old=u.equipment.weapon;buy(()=>{u.equipment.weapon=weapon.value;},()=>{u.equipment.weapon=old;});};
  field('武器',weapon);
  for(const [key,label] of [['armor','护甲'],['banner','战旗']]){
   const checkbox=document.createElement('input');checkbox.type='checkbox';checkbox.id='campaign-'+key;checkbox.checked=u.equipment[key];
   checkbox.onchange=()=>{const old=u.equipment[key];buy(()=>{u.equipment[key]=checkbox.checked;},()=>{u.equipment[key]=old;});};
   field(label+' · '+costs[key]+' 点',checkbox);
  }
  const mission=document.createElement('select');
  for(const [key,label] of [['hold','守区'],['reserve','机动回援'],['stock','护粮']])mission.add(new Option(label,key));
  mission.value=u.mission;
  mission.onchange=()=>{u.mission=mission.value;refresh();};
  field('守军任务',mission);
  const rotate=document.createElement('input');rotate.type='checkbox';rotate.checked=!!u.rotation_reserve;
  rotate.disabled=u.mission!=='hold';rotate.onchange=()=>{u.rotation_reserve=rotate.checked;};
  field('轮换后备',rotate);
 }
 $('campaign-enter').onclick=async()=>{
  if(!editing||busy)return;
  try{
   if(!campaignCatalog){
    const response=await fetch('/api/campaign');
    if(!response.ok)throw Error('关卡目录不可用');
    campaignCatalog=await response.json();
    for(const level of campaignCatalog.levels)$('campaign-level').add(new Option(level.title,level.id));
   }
   $('campaign-dialog').showModal();
   showLevel();
  }catch(error){msg(error.message);}
 };
 function showLevel(){
  const level=campaignCatalog.levels.find(item=>item.id===$('campaign-level').value);
  $('campaign-description').textContent=level.description+' '+level.units.length+' 名守军，'+level.budget+' 点，守 '+level.turns+' 步。';
 }
 $('campaign-level').onchange=showLevel;
 $('campaign-close').onclick=()=>$('campaign-dialog').close();
 $('campaign-load').onclick=async()=>{
  if(!editing||busy)return;
  const level=campaignCatalog.levels.find(item=>item.id===$('campaign-level').value);
  let state=null;
  if($('settlement-enable').checked){
   busy=true;$('campaign-load').disabled=true;
   try{state=await post('/api/settlement',{action:'new',level:level.id});}
   catch(error){msg(error.message);$('campaign-dialog').close();return;}
   finally{busy=false;$('campaign-load').disabled=false;}
  }
  if(!campaign)sandboxBackup={config,selected,opened,selectedGate};
  campaign=level;settlement=null;settlementKey=state?.key??null;
  retryToken=null;$('same-attack').checked=false;
  $('order-gate').replaceChildren(...campaign.gates.map(g=>new Option(g.name,g.id)));
  config=structuredClone(campaign);config.fortifications={};config.intel={D:[],A:[]};
  if(state){
   applySettlement(state.settlement);
   config.terrain=structuredClone(settlement.terrain);
  }
  selected=config.units[0].id;opened=selected;selectedGate=null;replay=null;
  $('campaign-dialog').close();
  setMap();msg(settlement?'安全期。可把守军部署到外围生产点，再按「推进 1 步」结算时间。':'守军已部署。点选棋子购买训练和装备，开战后才会发现敌人。');refresh();
 };
 $('campaign-exit').onclick=()=>{
  if(!editing||busy||!sandboxBackup)return;
  ({config,selected,opened,selectedGate}=sandboxBackup);
  campaign=null;sandboxBackup=null;retryToken=null;settlement=null;settlementKey=null;replay=null;setMap();msg('已返回自由试场。');refresh();
 };
 function blocked(){return new Set([...config.terrain.blocked,...config.gates.flatMap(g=>g.cells)].map(p=>p.join(',')));}
 const msg=s=>$('status').textContent=s;
 function valid(p,id){
  const w=config.terrain.width??32,h=config.terrain.height??24;
  if(campaign){const [left,top,right,bottom]=settlement?[0,0,w-1,h-1]:campaign.bounds;if(!(left<p[0]&&p[0]<right&&top<p[1]&&p[1]<bottom))return false;}
  return p[0]>=0&&p[0]<w&&p[1]>=0&&p[1]<h&&!blocked().has(p.join(','))&&!config.units.some(u=>u.id!==id&&u.pos.join(',')===p.join(','));}
 function paint(p){
  const tool=$('add-kind').value;
  const oldGate=config.gates.find(g=>g.cells.some(q=>q.join(',')===p.join(',')));
  if(oldGate){if(tool==='erase'){config.gates=config.gates.filter(g=>g.id!==oldGate.id);selectedGate=null;refresh();}return;}
  if(tool==='gate'){if(!valid(p)){msg('城门须放在无棋子和障碍的空地。');return;}let n=1;while(config.gates.some(g=>g.id==='G'+n))n++;const id='G'+n;config.gates.push({id,name:'城门 '+n,hp:20,cells:[p]});selectedGate=id;selected=null;msg('已添加城门，在右侧调整血量与位置。');refresh();return;}
  if(p[0]<0||p[0]>=32||p[1]<0||p[1]>=24)return;
  if(config.units.some(u=>u.pos.join(',')===p.join(','))||p.join(',')===data.map.stock.join(',')||p[0]===1){msg('棋子所在格、粮仓和西侧撤离列保持可通行。');return;}
  for(const key of ['blocked','cover','rough'])config.terrain[key]=config.terrain[key].filter(q=>q.join(',')!==p.join(','));
  if(tool!=='erase')config.terrain[tool==='wall'?'blocked':tool].push(p);
  msg('地形已修改，重新推演后生效。');refresh();
 }
 const bounds={sight:[1,20,1],reach:[1,15,.1],hit:[0,1,.01],injury:[0,1,.01],speed:[1,3,1],treatments:[0,10,1]};
 function statsUI(){
  const tbody=$('stats').querySelector('tbody');tbody.replaceChildren();
  for(const [kind,values] of Object.entries(config.stats)){
   const row=document.createElement('tr'),name=document.createElement('td');name.textContent=data.types[kind].label;row.append(name);
   for(const key of Object.keys(bounds)){const td=document.createElement('td'),input=document.createElement('input');input.type='number';input.value=values[key];[input.min,input.max,input.step]=bounds[key];input.id=`stat-${kind}-${key}`;input.setAttribute('aria-label',`${data.types[kind].label} ${key}`);input.onchange=()=>{if(!input.checkValidity()){input.reportValidity();return;}config.stats[kind][key]=+input.value;msg('参数已修改，重新推演后生效。');};td.append(input);row.append(td);}tbody.append(row);
  }
 }
 statsUI();
 function cell(e){const p=world(e);return [Math.floor(p.x/20),Math.floor(p.y/20)];}
 function sync(){
  if(campaign)return;
  for(const team of ['D','A']){
   const mode=$('intel-'+team).value,ids=config.units.filter(u=>u.team!==team).map(u=>u.id);
   config.intel[team]=mode==='all'?ids:mode==='none'?[]:config.intel[team].filter(id=>ids.includes(id));
  }
 }
 function refresh(){sync();draw();}
 function pick(id){selectedGate=null;selected=id;refresh();}
 function details(container){
  if(campaign){
   const gate=config.gates.find(g=>g.id===selectedGate);
   if(gate)campaignGateDetails(container,gate);else campaignDetails(container,config.units.find(u=>u.id===selected));
   return;
  }
  const gate=config.gates.find(g=>g.id===selectedGate);
  if(gate){$('unit-title').textContent=gate.name;container.replaceChildren();const note=document.createElement('p');note.textContent='关闭时挡路及视线；血量归零后打开。普通武器每次2伤害，攻城武器6伤害。';container.append(note);
   const controls={};for(const [key,caption,value,min,max] of [['hp','城门血量',gate.hp,1,500],['x','位置 X',gate.cells[0][0],0,31],['y','位置 Y',gate.cells[0][1],0,23]]){const label=document.createElement('label');label.textContent=caption;const input=document.createElement('input');input.type='number';input.id='gate-'+key;input.value=value;input.min=min;input.max=max;input.step=1;label.append(input);container.append(label);controls[key]=input;}
   const save=document.createElement('button');save.id='save-gate';save.textContent='应用城门设置';save.onclick=()=>{if(Object.values(controls).some(i=>!i.checkValidity())){msg('请填写范围内的整数。');return;}const dx=+controls.x.value-gate.cells[0][0],dy=+controls.y.value-gate.cells[0][1],cells=gate.cells.map(([x,y])=>[x+dx,y+dy]);const reserved=new Set([...config.terrain.blocked,...config.gates.filter(g=>g!==gate).flatMap(g=>g.cells),...config.units.map(u=>u.pos),data.map.stock].map(p=>p.join(',')));if(cells.some(p=>p[0]<0||p[0]>31||p[1]<0||p[1]>23||p[0]===1||reserved.has(p.join(',')))){msg('城门新位置与障碍、棋子、粮仓或其他城门冲突。');return;}gate.hp=+controls.hp.value;gate.cells=cells;msg('城门设置已更新。');refresh();};container.append(save);
   const remove=document.createElement('button');remove.id='delete-gate';remove.textContent='移除城门';remove.onclick=()=>{config.gates=config.gates.filter(g=>g.id!==gate.id);selectedGate=null;refresh();};container.append(remove);return;}
  const u=config.units.find(u=>u.id===selected);
  $('unit-title').textContent=u?`${u.name||u.id} · ${data.types[u.kind].label}`:'棋子配置';container.replaceChildren();
  const p=document.createElement('p');p.textContent=u?`${u.team==='D'?'守方':'攻方'} · 起始格 (${u.pos.join(', ')})。${opened===u.id?'在下方配置技能、装备与士气。':'双击棋子打开配置。'}`:'从左侧拖入棋子，再双击打开它。';container.append(p);
  if(!u)return;
  const observer=u.team==='D'?'A':'D',label=document.createElement('label'),check=document.createElement('input');check.type='checkbox';check.id='known-piece';check.checked=config.intel[observer].includes(u.id);
  check.onchange=()=>{$('intel-'+observer).value='custom';config.intel[observer]=config.intel[observer].filter(id=>id!==u.id);if(check.checked)config.intel[observer].push(u.id);refresh();};
  label.style.display='flex';label.append(check,document.createTextNode(`${observer==='D'?'守方':'攻方'}开局知道此单位的位置`));container.append(label);
  if(opened===u.id){
   const form=document.createElement('div');form.className='loadout';u.equipment??={armor:false,weapon:'default',banner:false};
   const field=(caption,input)=>{const label=document.createElement('label');label.textContent=caption;label.append(input);form.append(label);};
   const name=document.createElement('input');name.type='text';name.id='piece-name';name.maxLength=16;name.value=u.name||u.id;name.onchange=()=>{u.name=name.value.trim()||u.id;refresh();};field('名字',name);
   const training=document.createElement('select');training.id='piece-training';
   ['未受训 · 固定起始技能','基础训练 · 最多前两项','熟练 · 完整技能顺序'].forEach((label,i)=>training.add(new Option(label,i)));
   training.value=u.training??2;training.onchange=()=>{u.training=+training.value;refresh();};field('训练程度',training);
   const required=document.createElement('input');required.type='number';required.id='loyalty-threshold';
   required.min=0;required.max=3;required.step=1;required.value=u.loyalty_threshold??0;
   required.onchange=()=>{if(required.value!==''&&required.checkValidity()){u.loyalty_threshold=+required.value;refresh();}};
   field('接受指挥所需威信（0–3）',required);
   const accepts=config.authority[u.team]>=(u.loyalty_threshold??0);
   const locked=!accepts||u.training===0;
   const skillPanel=document.createElement('fieldset');skillPanel.className='skill-panel';
   const legend=document.createElement('legend');legend.textContent='技能优先级';skillPanel.append(legend);
   const explanation=document.createElement('p');
   explanation.textContent=!accepts?'威信不足。开战后沿用起始技能和岗位。':u.training===0?'未受训。开战后沿用起始技能。':u.training===1?'仅前两项技能会生效。':'从上往下执行第一个可用技能。';
   skillPanel.append(explanation);
   const preset=document.createElement('select');preset.id='skill-preset';preset.setAttribute('aria-label','技能预设');
   preset.add(new Option('套用技能预设…',''));
   const presets={guard:['guard','archer'],scout:['scout','guard'],medic:['medic','archer']};
   for(const [key,label] of Object.entries({guard:'据点警戒',scout:'侦察接应',medic:'救护掩护'}))preset.add(new Option(label,key));
   preset.disabled=locked;
   preset.onchange=()=>{if(preset.value){u.skills=[...presets[preset.value]];u.skill_rules={};refresh();}};
   skillPanel.append(preset);
   const skillOrder=document.createElement('ol');skillOrder.id='skill-order';skillPanel.append(skillOrder);
   u.skills??=[u.kind];
   for(const [index,key] of u.skills.entries()){
    const row=document.createElement('li');
    const title=document.createElement('strong');title.textContent=data.skills[key].label;row.append(title);
    const actions=document.createElement('div');
    const button=(text,label,click,disabled=false)=>{
     const node=document.createElement('button');node.type='button';node.textContent=text;
     node.setAttribute('aria-label',label);node.disabled=disabled||locked;node.onclick=click;actions.append(node);
    };
    const move=delta=>{[u.skills[index],u.skills[index+delta]]=[u.skills[index+delta],u.skills[index]];refresh();};
    button('↑',data.skills[key].label+'上移',()=>move(-1),index===0);
    button('↓',data.skills[key].label+'下移',()=>move(1),index===u.skills.length-1);
    button('移除','移除'+data.skills[key].label,()=>{u.skills.splice(index,1);refresh();});
    const hint=document.createElement('p');hint.textContent=data.skills[key].hint;row.append(actions,hint);
    if(!locked&&(u.training??2)===2){
     const rule=(u.skill_rules??={})[key]??={};
     const selector=(caption,values,property)=>{
      const label=document.createElement('label');label.textContent=caption;
      const select=document.createElement('select');
      for(const [value,text] of Object.entries(values))select.add(new Option(text,value));
      select.value=rule[property]??Object.keys(values)[0];
      select.onchange=()=>{rule[property]=select.value;};label.append(select);row.append(label);
     };
     selector('触发条件',{always:'按技能默认条件',safe:'附近安全',wounded:'有友方伤员',alert:'收到回援命令'},'condition');
     if(key==='guard'||key==='archer')selector('选敌偏好',{default:'按默认威胁排序',nearest:'最近目标',wounded:'优先受伤敌人'},'target');
    }
    skillOrder.append(row);
   }
   if(!u.skills.length){const empty=document.createElement('p');empty.textContent='未装技能，单位只执行基本任务。';skillPanel.append(empty);}
   const addSkill=document.createElement('select');addSkill.id='add-skill';addSkill.setAttribute('aria-label','添加技能');
   addSkill.add(new Option('添加技能…',''));
   for(const [key,skill] of Object.entries(data.skills))if(!u.skills.includes(key))addSkill.add(new Option(skill.label,key));
   addSkill.disabled=locked||u.skills.length===Object.keys(data.skills).length;
   addSkill.onchange=()=>{if(addSkill.value){u.skills.push(addSkill.value);refresh();}};
   skillPanel.append(addSkill);form.append(skillPanel);
   if(u.team==='D'){
    const mission=document.createElement('select');mission.id='piece-mission';
    for(const [key,label] of [['hold','原地守区'],['reserve','机动回援'],['stock','保护粮仓']])mission.add(new Option(label,key));
    mission.value=u.mission??'hold';mission.onchange=()=>{u.mission=mission.value;refresh();};
    mission.disabled=!accepts;field('守方预案',mission);
    const reserveHint=document.createElement('p');
    reserveHint.textContent='机动组按呼援补位。警钟响起后，守区组留岗，粮仓组就近护粮。';
    const response=document.createElement('input');response.type='number';response.id='response-range';
    response.min=0;response.max=32;response.step=1;response.value=u.response_range??10;
    response.onchange=()=>{if(response.value!==''&&response.checkValidity())u.response_range=+response.value;};
    field('呼援响应范围（格，0 关闭接收）',response);
    form.append(reserveHint);
    const rotation=document.createElement('input');rotation.type='checkbox';rotation.id='rotation-reserve';
    rotation.checked=!!u.rotation_reserve;
    rotation.disabled=!accepts||mission.value!=='hold';
    rotation.onchange=()=>{u.rotation_reserve=rotation.checked;};
    field('轮换后备 · 在部署点休整',rotation);
   }
   const armor=document.createElement('input');armor.type='checkbox';armor.id='gear-armor';armor.checked=u.equipment.armor;armor.onchange=()=>{u.equipment.armor=armor.checked;msg('护甲已更新：受到致伤概率降低20个百分点。');};field('护甲 · 致伤概率 −0.20',armor);
   const weapon=document.createElement('select');weapon.id='gear-weapon';for(const [value,text] of Object.entries({default:'兵种默认射程',none:'无武器 · 近身，命中−0.15',melee:'近战武器 · 1.5格',ranged:'远程武器 · 至少6.2格',siege:'攻城武器 · 近战，城门伤害6'})){const option=document.createElement('option');option.value=value;option.textContent=text;weapon.append(option);}weapon.value=u.equipment.weapon;weapon.onchange=()=>{u.equipment.weapon=weapon.value;msg('武器已更新，开战后按装备选择攻击距离。');};field('武器',weapon);
   const banner=document.createElement('input');banner.type='checkbox';banner.id='gear-banner';banner.checked=u.equipment.banner;banner.onchange=()=>{u.equipment.banner=banner.checked;refresh();};field('战旗 · 领袖为本方提供4点士气',banner);
   const threshold=document.createElement('input');threshold.type='number';threshold.id='piece-morale';threshold.min=0;threshold.max=10;threshold.step=.5;threshold.value=u.morale_threshold??5;threshold.onchange=()=>{if(threshold.checkValidity()){u.morale_threshold=+threshold.value;msg('士气属性已更新。');}else threshold.reportValidity();};field('士气属性 · 当前士气低于此值时可能溃逃',threshold);
   const note=document.createElement('p');note.textContent='旗手失能或溃逃后停止加成。战旗不叠加，上限10。装备仅在面板中显示。';form.append(note);container.append(form);
  }else{const open=document.createElement('button');open.id='open-piece';open.textContent='打开棋子';open.onclick=()=>{opened=u.id;refresh();};container.append(open);}
  const del=document.createElement('button');del.id='delete-piece';del.textContent='移除这枚棋子';del.onclick=remove;container.append(del);
 }
 function addPiece(kind,p){
  if(campaign)return;
  if(config.units.length>=32){msg('最多32枚棋子。');return;}
  if(!valid(p)){msg('这里不能落子，请拖到无障碍的空地。');return;}
  const team=$('add-team').value;let n=0;while(config.units.some(u=>u.id===team+n))n++;
  const id=team+n;config.units.push({id,team,kind,pos:p,skills:[kind],name:data.types[kind].label+' '+id,equipment:{armor:false,weapon:'default',banner:false},morale_threshold:5});selected=id;opened=null;msg(`已添加 ${id}。双击配置技能与装备。`);refresh();
 }
 for(const [kind,type] of Object.entries(data.types)){
  const card=document.createElement('button');card.type='button';card.className='piece-card';card.dataset.kind=kind;card.draggable=true;card.textContent=type.label;
  const hint=document.createElement('small');hint.textContent='拖入地图 · 或点击后落子';card.append(hint);
  card.addEventListener('dragstart',e=>{if(!editing||busy){e.preventDefault();return;}e.dataTransfer.setData('application/x-village-piece',kind);e.dataTransfer.setData('text/plain',kind);e.dataTransfer.effectAllowed='copy';});
  card.onclick=()=>{$('add-kind').value=kind;msg(`已选择${type.label}，点击地图空地落子。`);};$('palette').append(card);
 }
 $('map').addEventListener('dragover',e=>{if(editing&&!busy){e.preventDefault();e.dataTransfer.dropEffect='copy';}});
 $('map').addEventListener('drop',e=>{e.preventDefault();if(!editing||busy)return;const kind=e.dataTransfer.getData('application/x-village-piece')||e.dataTransfer.getData('text/plain');if(data.types[kind]){addPiece(kind,cell(e));$('add-kind').value='';}});
 $('map').addEventListener('dblclick',e=>{if(!editing)return;const p=cell(e),u=config.units.find(u=>u.pos.join(',')===p.join(','));if(u){selected=u.id;opened=u.id;refresh();}});
 for(const [id,key] of [['morale-interval','interval'],['morale-chance','chance']])$(id).onchange=()=>{if($(id).checkValidity())config.morale[key]=+$(id).value;};

 function remove(){if(campaign||!editing||!selected)return;config.units=config.units.filter(u=>u.id!==selected);selected=null;msg('已移除；模拟前双方须各有至少一枚。');refresh();}
 $('map').style.touchAction='none';
 $('map').addEventListener('pointerdown',e=>{
  if(!editing||busy||e.button!==0)return;const p=cell(e),u=config.units.find(u=>u.pos.join(',')===p.join(','));
  if(!campaign&&['wall','cover','rough','erase','gate'].includes($('add-kind').value)){painting=true;$('map').setPointerCapture(e.pointerId);paint(p);return;}
  const gate=config.gates.find(g=>g.cells.some(q=>q.join(',')===p.join(',')));if(gate){selectedGate=gate.id;selected=null;refresh();return;}
  if(u){selectedGate=null;if(lastPick.id===u.id&&performance.now()-lastPick.time<400)opened=u.id;lastPick={id:u.id,time:performance.now()};selected=u.id;drag={id:u.id,start:[...u.pos],x:e.clientX,y:e.clientY};$('map').setPointerCapture(e.pointerId);refresh();return;}
  if(campaign||!$('add-kind').value){selected=null;refresh();return;}
  addPiece($('add-kind').value,p);
 });
 $('map').addEventListener('pointermove',e=>{if(painting){paint(cell(e));return;}if(!drag)return;const p=cell(e);if(valid(p,drag.id)){config.units.find(u=>u.id===drag.id).pos=p;refresh();}});
 function end(e){if(!drag)return;const p=cell(e),u=config.units.find(u=>u.id===drag.id);if(!valid(p,u.id)){u.pos=drag.start;msg('落点无效，已回到拖动前的位置。');}else{u.pos=p;msg(`已部署 ${u.id} 至 (${p.join(', ')})。`);}drag=null;refresh();}
 $('map').addEventListener('pointerup',e=>{painting=false;end(e);});$('map').addEventListener('pointercancel',()=>{painting=false;if(drag){config.units.find(u=>u.id===drag.id).pos=drag.start;drag=null;refresh();}});
 document.addEventListener('keydown',e=>{if(e.key==='Delete'&&!['INPUT','SELECT','TEXTAREA'].includes(document.activeElement.tagName))remove();});
 for(const team of ['D','A'])$('intel-'+team).onchange=refresh;
 for(const team of ['D','A'])$('authority-'+team).onchange=()=>{
  const input=$('authority-'+team);if(input.checkValidity()){config.authority[team]=+input.value;refresh();}
 };
 $('minimum-watch').onchange=()=>{if($('minimum-watch').checkValidity())config.minimum_watch=+$('minimum-watch').value;};
 $('alarm-bell').onchange=()=>{config.alarm_bell=$('alarm-bell').checked;};
 const tutorialIds=['authority-D','authority-A','minimum-watch','attack-rally','rally-x','rally-y','alarm-bell','intel-D','intel-A','morale-interval','morale-chance','seed','limit','add-kind','add-team'];
 function tutorialLesson(){
  if(campaign||!editing||busy)return;
  if(!tutorialBackup)tutorialBackup={config,inputs:tutorialIds.map(id=>[$(id).value,$(id).checked])};
  config=defaults();
  config.units=[
   {id:'D0',team:'D',kind:'guard',pos:[16,6],name:'第一班',skills:['guard'],mission:'hold'},
   {id:'D1',team:'D',kind:'guard',pos:[16,9],name:'第二班',skills:['guard'],mission:'hold',rotation_reserve:true},
   {id:'A0',team:'A',kind:'scout',pos:[17,6],name:'练习对手',skills:['guard'],equipment:{armor:true}}
  ];
  config.terrain={blocked:[],cover:[],rough:[]};
  config.gates=[];
  config.stats.guard.hit=.34;config.stats.guard.injury=.35;config.stats.scout.hit=0;
  $('seed').value=7;$('limit').value=28;
  $('authority-D').value=2;$('authority-A').value=2;$('minimum-watch').value=1;
  $('alarm-bell').checked=false;$('attack-rally').checked=false;
  $('intel-D').value=$('intel-A').value='none';
  $('add-kind').value='';$('add-team').value='D';
  $('lesson-restore').hidden=false;
  $('lesson-note').hidden=false;
  selected='D1';opened='D1';selectedGate=null;replay=null;statsUI();
  msg('换防演练已布好。查看第二班的轮换配置，然后开始战斗。');refresh();
 }
 $('lesson-load').onclick=()=>{tutorialLesson();$('tutorial').close();};
 $('lesson-restore').onclick=()=>{
  if(!editing||busy||!tutorialBackup)return;
  config=tutorialBackup.config;
  tutorialIds.forEach((id,i)=>{const [value,checked]=tutorialBackup.inputs[i];$(id).value=value;$(id).checked=checked;});
  tutorialBackup=null;$('lesson-restore').hidden=true;$('lesson-note').hidden=true;
  selected=opened=selectedGate=null;replay=null;statsUI();msg('已回到演练前的布防。');refresh();
 };
 $('tutorial-open').onclick=()=>$('tutorial').showModal();
 $('tutorial-close').onclick=()=>$('tutorial').close();
 $('reset').onclick=()=>{stop();cancelLive();config=defaults();$('authority-D').value=2;$('authority-A').value=2;$('minimum-watch').value=1;$('attack-rally').checked=false;$('rally-x').value=11;$('rally-y').value=6;$('alarm-bell').checked=false;selectedGate=null;opened=null;$('morale-interval').value=5;$('morale-chance').value=.25;statsUI();$('intel-D').value=$('intel-A').value='none';selected=null;editing=true;replay=null;msg('已恢复默认布防、复杂地形和兵种数值。');refresh();};
 $('edit').onclick=()=>{
  if(settlement&&live)return;
  stop();cancelLive();editing=true;
  msg(settlement?(settlement.phase==='safe'?'袭击结束。调整布防后继续推进。':'经营已结算。可在「更换关卡」开始下一局。'):'回到原始布防，可继续修改后重新模拟。');refresh();
 };
 async function post(path,payload){
  const response=await fetch(path,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});
  if(!response.ok){let error;try{error=(await response.json()).error;}catch{}throw Error(error||'本机战斗服务未启动，请使用启动试场打开。');}
  return response.json();
 }
 $('field-order').onclick=async()=>{
  if(!campaign||!live||orderPending||!replay?.summary.order_available)return;
  const current=epoch;
  orderPending=true;draw();
  try{
   const receipt=await post('/api/order',{session,gate:$('order-gate').value});
   if(current!==epoch)return;
   replay.summary.order_available=false;
   msg(`传令已送达。第 ${receipt.starts} 步起，${receipt.count} 名机动守军调往${receipt.gate}。`);
  }catch(error){if(current===epoch)msg(error.message);}
  finally{if(current===epoch){orderPending=false;draw();}}
 };
 function cancelLive(){
  epoch++;clearTimeout(tickTimer);tickTimer=null;live=false;paused=false;inflight=false;orderPending=false;
  const old=session;session=null;if(old)post('/api/stop',{session:old}).catch(()=>{});
 }
 function schedule(){clearTimeout(tickTimer);if(live&&!paused&&!inflight)tickTimer=setTimeout(()=>tick(false),400/+$('speed').value);}
 async function tick(single=false){
  if(!live||inflight||(!single&&paused))return;
  const turn=epoch;inflight=true;
  try{
   const update=await post('/api/tick',{session});if(turn!==epoch)return;
   if(replay.summary.order_available===false)update.summary.order_available=false;
   if(update.settlement)applySettlement(update.settlement);
   replay.frames.push(update.frame);replay.summary=update.summary;
   $('round').max=replay.frames.length-1;
   if(!paused||single)$('round').value=replay.frames.length-1;
   if(update.done){
    live=false;paused=false;stop();$('round').value=replay.frames.length-1;
    msg(settlement?'袭击已结算，城门现状与守军经验已保存。':'战斗结束。可复盘已发生的过程，或返回布防再试。');
   }
   draw();
  }catch(e){if(turn===epoch){paused=true;msg('战斗暂停：'+e.message);draw();}}
  finally{if(turn===epoch){inflight=false;schedule();}}
 }
 function toggleLive(){if(!live)return false;paused=!paused;if(!paused)$('round').value=replay.frames.length-1;msg(paused?'战斗已暂停，单位不再继续演算。':'战斗进行中：持续感知、决策、寻路与交战。');schedule();draw();return true;}
 $('speed').onchange=schedule;
 async function advanceBattle(steps=1){
  if(busy)return;for(const input of document.querySelectorAll('input[type=number]')){if(!input.checkValidity()){input.reportValidity();return;}}
  stop();cancelLive();sync();busy=true;const turn=epoch;msg('正在创建战斗…');draw();
  try{
   const payload=campaign?{level:campaign.id,units:config.units,fortifications:config.fortifications,retry:$('same-attack').checked?retryToken:null}:{...config,rally:$('attack-rally').checked?[+$('rally-x').value,+$('rally-y').value]:null,seed:+$('seed').value,limit:+$('limit').value};
   const start=settlement?await post('/api/settlement',{action:'advance',key:settlementKey,units:config.units,steps}):await post('/api/start',payload);
   if(turn!==epoch)return;
   if(start.settlement){
    const elapsed=start.settlement.clock-settlement.clock;
    applySettlement(start.settlement);
    if(!start.session){msg(`已推进 ${elapsed} 步，查看生产和队列进度。`);return;}
   }
   replay={summary:start.summary,frames:start.frames};session=start.session;if(campaign&&!settlement)retryToken=session;
   editing=false;live=true;paused=false;$('round').value=0;$('view').value=campaign?'D':'all';
   msg(settlement?'敌袭！守军已按预案接战。':'战斗进行中：持续感知、决策、寻路与交战。');
  }catch(e){msg('未能开始战斗：'+e.message);}finally{busy=false;draw();schedule();}
 }
 $('simulate').onclick=()=>advanceBattle();
 $('advance-three').onclick=()=>advanceBattle(3);

 function plannedSites(){
  const [left,top,right,bottom]=campaign.bounds;
  return settlement.sites.map(site=>{
   const staffed=!site.outer||config.units.some(u=>{
    const [x,y]=u.pos;
    return (x<=left||x>=right||y<=top||y>=bottom)&&Math.hypot(x-site.pos[0],y-site.pos[1])<=4;
   });
   return {...site,status:staffed?'预计生产':'缺少守军'};
  });
 }

 setMap();
 return {get campaign(){return campaign;},get live(){return live;},get paused(){return paused;},get limit(){return campaign?.turns??+$('limit').value;},toggleLive,stepLive(){if(!live)return false;if(!paused)return true;tick(true);return true;},get editing(){return editing;},get replay(){return replay;},get selected(){return selected;},get terrain(){return config.terrain;},get structures(){return config.gates;},get gates(){if(campaign)return [];const b=new Set(config.terrain.blocked.map(p=>p.join(',')));return Array.from({length:24},(_,y)=>[14,y]).filter(([x,y])=>!b.has(`${x},${y}`)&&(y===0||b.has(`${x},${y-1}`)));},pick,details,locate,
 renderMorale(frame,view){
  let scores=frame.morale;
  if(editing)scores=Object.fromEntries(['D','A'].map(team=>{const own=config.units.filter(u=>u.team===team),leaders=own.filter(u=>u.equipment?.banner).length;return [team,{alive:own.length,total:own.length,current:own.length?10:0,bonus:leaders?4:0}];}));
  $('morale-summary').textContent=['D','A'].filter(team=>view==='all'||view===team).map(team=>{const m=scores?.[team];return m?`${team==='D'?'守方':'攻方'}士气 ${m.current.toFixed(1)} / 10 · 存活 ${m.alive}/${m.total}${m.bonus?' · 战旗+4':''}`:'';}).join('　 |　 ');
 },
 frame(){return {round:0,units:config.units.map(u=>({...u,active:true,wound:0,cargo:false,heading:u.team==='D'?Math.PI:0})),intel:config.intel,structures:displayedStructures(),sites:settlement?plannedSites():undefined,events:[]};},
 controls(){
  $('campaign-enter').disabled=!editing||busy;
  $('campaign-enter').textContent=campaign?'更换关卡':'守城关卡';
  $('campaign-exit').hidden=!campaign;
  $('campaign-exit').disabled=!editing||busy;
  document.body.classList.toggle('campaign-mode',!!campaign);
  $('retry-control').hidden=!campaign||!editing||!retryToken;
  $('order-controls').hidden=!campaign||editing;
  const mayOrder=!!campaign&&live&&replay?.frames.length>1&&replay.summary.order_available;
  $('field-order').disabled=!mayOrder||orderPending;
  $('order-gate').disabled=!mayOrder||orderPending;
  $('field-order').textContent=replay?.summary.order_available===false?'传令已用':'传令 · 1 次';
  $('campaign-hud').hidden=!campaign;
  $('campaign-hud').textContent=campaign?campaign.title+' · 剩余 '+(campaign.budget-campaignSpend())+' / '+campaign.budget+(settlement?' 装备点':' 点 · 坚守 '+campaign.turns+' 步'):'';
  for(const id of ['play','step','round','view'])$(id).disabled=editing||(id==='view'&&!!campaign); if(live){$('round').disabled=true;$('step').disabled=!paused;$('play').textContent=paused?'继续战斗':'暂停战斗';}for(const id of ['add-kind','add-team','intel-D','intel-A','seed','limit','reset','alarm-bell','authority-D','authority-A','minimum-watch','attack-rally','rally-x','rally-y','morale-interval','morale-chance'])$(id).disabled=!editing||busy;for(const card of document.querySelectorAll('.piece-card')){card.disabled=!editing||busy;card.draggable=editing&&!busy;}for(const input of $('stats').querySelectorAll('input'))input.disabled=!editing||busy;$('lesson-load').disabled=!!campaign||!editing||busy;$('lesson-restore').disabled=!editing||busy;$('simulate').hidden=!editing;$('mode').textContent=editing?(campaign?'布防中 · 战争迷雾':'布防中 · 全部起始位置可见'):live?(paused?'战斗暂停 · 可单步推进':'实时战斗 · 正在自动演算'):'战斗结束 · 可复盘';$('counts').textContent=campaign?`守军 ${config.units.length} / 敌方未知`:`守方 ${config.units.filter(u=>u.team==='D').length} / 攻方 ${config.units.filter(u=>u.team==='A').length}`;
  $('simulate').disabled=busy||!!settlement&&settlement.phase!=='safe';
  $('simulate').textContent=settlement?'推进 1 步':'开始战斗';
  $('advance-three').hidden=!settlement||!editing||settlement.phase!=='safe';
  $('advance-three').disabled=busy;
  $('edit').disabled=editing||busy||!!settlement&&live;
  $('settlement-panel').hidden=!settlement;
  if(settlement){
   const {phase,clock,raids,total,resources,jobs,safe_left}=settlement;
   $('settlement-summary').textContent=`${{safe:'安全期',conflict:'冲突期',won:'守住村庄',lost:'村庄失守'}[phase]} · 时间 ${clock} · 已结算 ${raids}/${total} 次袭击 · 工料 ${resources.materials} · 补给 ${resources.supplies}`;
   const sites=editing&&phase==='safe'?plannedSites():settlement.sites;
   const income=sites.filter(s=>s.status==='预计生产').reduce((sum,s)=>(sum[s.resource]+=s.rate,sum),{materials:0,supplies:0});
   const hint=phase==='safe'?(safe_left?`未来 ${safe_left} 步内无袭击。`:'预警期。下一步可能遇袭，来向未知。')
     +` 当前部署每两步预计 +${income.materials} 工料、+${income.supplies} 补给。`
     :phase==='conflict'?'可暂停查看已发现的敌情，也可以传令一次调派机动组。'
     :'打开战报转折点，查看发现敌情、城门损坏和撤回布防前的结局。';
   $('settlement-tip').textContent=hint;
   $('settlement-jobs').textContent=jobs.length?jobs.map(j=>{
    const target=j.training?config.units.find(u=>u.id===j.target).name:settlement.gates.find(g=>g.id===j.target).name;
    return `${target} · ${j.training?campaignCatalog.skills[j.kind]:settlement.work[j.kind][0]} · 剩 ${j.left} 步${j.paused?'（暂停）':''}`;
   }).join('　|　'):'施工与训练队列为空';
   if($('settlement-sites').parentElement.open||editing)$('settlement-sites').replaceChildren(...sites.map(site=>{
    const node=document.createElement('li'),button=document.createElement('button');
    button.textContent=site.name;button.onclick=()=>locate(site.pos);
    node.append(button,` +${site.rate}${site.resource==='materials'?'工料':'补给'} · ${site.outer?(site.covered?'有掩体 · ':'露天 · '):'城内 · '}${site.status??'待结算'}`);
    return node;
   }));
  }
 },
 summary(){if(!replay)return '';const s=replay.summary;
 if(campaign)return s.result?(s.victory?'守城成功 · 补给未被运出':(s.result==='defender_overrun'?'守城失败 · 守军已无作战单位':'守城失败 · 补给被运走')):'坚守中 · 敌情随侦察更新';if(!s.result)return `自动演算${paused?'已暂停':'进行中'} · 已发生${s.rounds}步 · 种子${s.seed}`;return `${{attacker_extract:'攻方携粮撤离',defender_clear:'攻方已无作战单位',deadline_no_extract:'推演截止：补给尚未运出'}[s.result]} · ${s.rounds}轮 · 失能 守${s.D_disabled}/攻${s.A_disabled} · 种子${s.seed}`;}
 };
};
