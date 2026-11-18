"use strict";
const limbusPacks=window.LIMBUS_PARTS||{};
const limbusKeys=[...new Set(["10201","10401","10204","10901",...Object.keys(limbusPacks)])].filter(id=>limbusPacks[id]);
const limbusDefaults={outfit:limbusKeys[0]||"",head:limbusKeys[0]||"",hair:"head",scar:"无",weapon:"显示",coat:"显示"};
let limbusLook={...limbusDefaults};
const limbusFields=[
 ["outfit","服装","日常造型",limbusKeys],
 ["head","头部","基础身份",limbusKeys],
 ["hair","活动发层","日常造型",["head","none",...limbusKeys.filter(id=>limbusPacks[id].layers.some(x=>isHair(x.slot)))]],
 ["coat","外衣层","日常造型",["显示","隐藏"]],
 ["weapon","武器","日常造型",["显示","隐藏"]],
 ["scar","面部疤痕","途径附加件",["无","斜疤","短疤"]]
];
const limbusInputs=new Map();
const optionLabels={head:"随所选头部",none:"隐藏独立发层"};
function isHair(slot){return /^hair/i.test(slot);}
function isOuter(slot){return /^(coat|cape)/i.test(slot);}
function createLimbusControls(){
 for(const [key,label,group,options] of limbusFields){
    const row=document.createElement("label");
    row.textContent=label;
    const select=document.createElement("select");
    select.id="limbus-"+key;
    for(const option of options)select.add(new Option(limbusPacks[option]?.name||optionLabels[option]||option,option));
    select.onchange=()=>{
      if(!editable(group))return;
      limbusLook[key]=select.value;
      renderLimbusEditor();
    };
    row.append(select);
    $("limbusControls").append(row);
    limbusInputs.set(key,select);
 }
 $("limbusZoom").onchange=renderLimbusEditor;
 $("limbusPng").onclick=exportLimbusPng;
}
function importLimbusLook(data){
 if(!data||typeof data!=="object")return;
 for(const [key,,group,options] of limbusFields){
    if(editable(group)&&options.includes(data[key]))limbusLook[key]=data[key];
 }
}
function renderLimbusEditor(){
 const stage=$("limbusEditorStage");
 stage.replaceChildren();
 const host=limbusPacks[limbusLook.outfit], donor=limbusPacks[limbusLook.head];
 if(!host||!donor){
   $("limbusEditorNote").textContent="本机分层资源索引缺失。见 README 的重建说明。";
   return;
 }
 const headOf=pack=>pack.layers.find(x=>x.slot==="head");
 const hostHead=headOf(host), donorHead=headOf(donor);
 const close=$("limbusZoom").value==="head";
 const zoom=close?Math.min(360/hostHead.w,350/hostHead.h):1;
 const originX=close?280-(hostHead.x+hostHead.w/2)*zoom:0;
 const originY=close?240-(hostHead.y+hostHead.h/2)*zoom:0;
 const proportions=layer=>({
   left:(originX+layer.x*zoom)/5.6+"%",top:(originY+layer.y*zoom)/5.6+"%",
   width:layer.w*zoom/5.6+"%",height:layer.h*zoom/5.6+"%"
 });
 const snapped=(layer,anchor)=>{
    const scale=hostHead.h/anchor.h;
    return {...layer,x:hostHead.x+hostHead.w*.5+(layer.x-anchor.x-anchor.w*.5)*scale,
            y:hostHead.y+(layer.y-anchor.y)*scale,w:layer.w*scale,h:layer.h*scale};
 };
 const append=(layer,role)=>{
    const image=document.createElement("img");
    image.src=layer.image;
    image.alt=layer.slot;
    image.dataset.role=role;
    Object.assign(image.style,proportions(layer));
    stage.append(image);
 };
 const hair=limbusLook.hair==="head"?donor:limbusPacks[limbusLook.hair];
 const hairLayers=hair?hair.layers.filter(x=>isHair(x.slot)):[];
 for(const layer of hairLayers.filter(x=>/back/i.test(x.slot)))append(snapped(layer,headOf(hair)),"rear-hair");
 for(const layer of host.layers){
    if(isHair(layer.slot))continue;
    if(limbusLook.weapon==="隐藏"&&/weapon/i.test(layer.slot))continue;
    if(limbusLook.coat==="隐藏"&&isOuter(layer.slot))continue;
    if(layer.slot==="head")append(snapped(donorHead,donorHead),"head");
    else if(!close)append(layer,"outfit");
 }
 for(const layer of hairLayers.filter(x=>!/back/i.test(x.slot)))append(snapped(layer,headOf(hair)),"front-hair");
 if(limbusLook.scar!=="无"){
   const scar=document.createElement("i");
   scar.className="limbus-scar "+(limbusLook.scar==="短疤"?"short":"");
   scar.dataset.role="scar";
   Object.assign(scar.style,proportions({x:hostHead.x+hostHead.w*.52,y:hostHead.y+hostHead.h*.64,w:hostHead.w*.17,h:Math.max(2,hostHead.h*.019)}));
   stage.append(scar);
 }
 for(const [key,,group] of limbusFields){
    const input=limbusInputs.get(key);
    input.value=limbusLook[key];
    input.disabled=!editable(group)||(key==="coat"&&!host.layers.some(x=>isOuter(x.slot)));
 }
 $("limbusEditorNote").textContent="本机战斗素材 · 静态站姿 · 基础五官随整头切换";
}

const embeddedLimbus = new Map();
function loadLimbusImageData(packs){
 const paths=[...new Set(packs.map(pack=>pack?.exportData).filter(Boolean))];
 return Promise.all(paths.map(path=>{
   if(embeddedLimbus.has(path))return embeddedLimbus.get(path);
   const pending=new Promise((resolve,reject)=>{
     const script=document.createElement("script");
     script.src=path;
     script.onload=()=>{script.remove();resolve();};
     script.onerror=()=>{script.remove();reject(Error("无法加载本机导出数据"));};
     document.head.append(script);
   }).catch(error=>{embeddedLimbus.delete(path);throw error;});
   embeddedLimbus.set(path,pending);
   return pending;
 }));
}
async function exportLimbusPng(){
 const button=$("limbusPng");
 button.disabled=true;
 const stage=$("limbusEditorStage");
 const current={...limbusLook};
 const pixel=value=>parseFloat(value)*5.6;
 const items=[...stage.children].map(node=>({
   path:node.getAttribute("src"),scar:node.dataset.role==="scar",short:node.classList.contains("short"),
   x:pixel(node.style.left),y:pixel(node.style.top),w:pixel(node.style.width),h:pixel(node.style.height)
 }));
 try{
   if(!items.length)throw Error("当前预览没有可导出的部件");
   await loadLimbusImageData([limbusPacks[current.outfit],limbusPacks[current.head],limbusPacks[current.hair]]);
   const canvas=document.createElement("canvas");
   canvas.width=canvas.height=560;
   const pen=canvas.getContext("2d");
   for(const item of items){
     if(item.scar){
       pen.save();
       pen.translate(item.x+item.w/2,item.y+item.h/2);
       pen.rotate((item.short?65:-35)*Math.PI/180);
       pen.fillStyle="rgba(139,53,46,.78)";
       pen.beginPath();
       pen.ellipse(0,0,item.w*(item.short?.31:.5),item.h/2,0,0,Math.PI*2);
       pen.fill();
       pen.restore();
     }else{
       const payload=window.LIMBUS_EXPORT_IMAGES?.[item.path];
       if(!payload)throw Error("缺少原版部件的本机导出数据");
       const image=new Image();
       image.src="data:image/png;base64,"+payload;
       await image.decode();
       pen.drawImage(image,item.x,item.y,item.w,item.h);
     }
   }
   const blob=await new Promise(resolve=>canvas.toBlob(resolve,"image/png"));
   if(!blob)throw Error("PNG 编码失败");
   download(blob,"外境-边狱小人.png");
   message("已导出透明 PNG。");
 }catch(error){message(error.message);}
 finally{button.disabled=false;}
}
