"use strict";
const realParts = window.RUINA_PARTS || {};
const realSlots = [["BackHair","后发"],["Eye","眼睛"],["Eyebrow","眉毛"],["Mouth","嘴型"],["FrontHair","前发"]];
const defaultParts = Object.fromEntries(realSlots.map(([key]) => [key,"1-1"]));
const outfitChoices=Object.entries(realParts).filter(([key])=>key.startsWith("Outfit."));
let chosenParts = {...defaultParts,Outfit:outfitChoices[0]?.[0]||""};
let direction = "Front";
let expression = "Normal";
const realInputs = new Map();
const lookGroup = slot => slot.endsWith("Hair") ? "日常造型" : "基础身份";
const available = slot => [...new Set(Object.keys(realParts).filter(key => key.startsWith(slot+".")).map(key => key.split(".").at(-1)))].sort((a,b)=>a.localeCompare(b,"en",{numeric:true}));
function initOriginal(){
 for(const [slot,caption] of realSlots){
   const row=document.createElement("label");
   row.textContent=caption;
   const select=document.createElement("select");
   select.id="original-"+slot;
   if(slot.endsWith("Hair"))select.add(new Option("无","none"));
   const options=available(slot);
   for(const id of options)select.add(new Option(caption+" "+id,id));
   if(!options.includes(defaultParts[slot])&&options.length)defaultParts[slot]=options[0];
   chosenParts[slot]=defaultParts[slot];
   select.onchange=()=>{
     if(!editable(lookGroup(slot)))return;
     chosenParts[slot]=select.value;
     drawOriginal();
   };
   row.append(select);
   $("originalControls").append(row);
   realInputs.set(slot,select);
 }
 const outfitRow=document.createElement("label");
 outfitRow.textContent="服装";
 const outfit=document.createElement("select");
 outfit.id="original-Outfit";
 for(const [key,item] of outfitChoices)outfit.add(new Option(item.name,key));
 outfit.onchange=()=>{
   if(!editable("日常造型"))return;
   chosenParts.Outfit=outfit.value;
   $("originalFraming").value="body";
   drawOriginal();
 };
 outfitRow.append(outfit);
 $("originalControls").prepend(outfitRow);
 $("originalFraming").onchange=drawOriginal;
 $("originalDirection").onchange=e=>{direction=e.target.value;drawOriginal();};
 $("originalExpression").onchange=e=>{expression=e.target.value;drawOriginal();};
}
function importOriginal(parts){
 if(!parts || typeof parts!=="object")return;
 if(editable("日常造型")&&outfitChoices.some(([key])=>key===parts.Outfit))chosenParts.Outfit=parts.Outfit;
 for(const [slot] of realSlots){
   if(!editable(lookGroup(slot)))continue;
   const selected=parts[slot];
   if((selected==="none"&&slot.endsWith("Hair"))||available(slot).includes(selected))chosenParts[slot]=selected;
 }
}
function drawOriginal(){
 const stage=$("originalStage");
 stage.replaceChildren();
 const note=$("originalNote");
 if(!Object.keys(realParts).length){
   note.textContent="本机部件索引未生成。请参阅 README 中的原版捏脸说明。";
   return;
 }
 const unavailable=[], substituted=[];
 const locate=(slot,side,exp,id)=>realParts[[slot,side,exp,id].join(".")];
 const choose=(slot,side,id,optional=false)=>{
   const exact=locate(slot,side,expression,id);
   const normal=locate(slot,side,"Normal",id);
   const alternate=side==="Side"&&["Mouth","Eyebrow"].includes(slot)?locate(slot,side,"Atk",id):null;
   const part=exact||normal||alternate;
   if(!exact&&!normal&&alternate)substituted.push(realSlots.find(([key])=>key===slot)[1]);
   if(!part&&!optional&&id!=="none")unavailable.push(realSlots.find(([key])=>key===slot)?.[1]||slot);
   return part;
 };
 const outfit=realParts[chosenParts.Outfit];
 const full=$("originalFraming").value==="body"&&outfit;
 const span=290;
 const bodyHeight=full?171:0;
 const bodyWidth=full?outfit.w/outfit.h*bodyHeight:0;
 const bodyX=full?span/2-bodyWidth*outfit.neckX:0;
 const bodyY=full?102:0;
 const headScale=full?.56:1;
 const headX=span/2;
 const headY=full?bodyY+bodyHeight*outfit.neckY-70*headScale:span/2;
 function place(item,x,y,w,h){
   const picture=document.createElement("img");
   picture.alt=item.name;
   picture.src=item.path;
   picture.style.left=(x/span*100)+"%";
   picture.style.top=(y/span*100)+"%";
   picture.style.width=(w/span*100)+"%";
   picture.style.height=(h/span*100)+"%";
   picture.onerror=()=>{if(picture.parentElement===stage)note.textContent="缺少本地 PNG："+item.name;};
   stage.append(picture);
 }
 const layers=[
   choose("BackHair",direction,chosenParts.BackHair),
   realParts["Head."+direction],
   choose("BackHair",direction+"Layer",chosenParts.BackHair,true),
   choose("Eye",direction,chosenParts.Eye),
   choose("Eyebrow",direction,chosenParts.Eyebrow),
   choose("Mouth",direction,chosenParts.Mouth),
   choose("FrontHair",direction,chosenParts.FrontHair)
 ];
 for(const [index,item] of layers.entries()){
   if(full&&index===1)place(outfit,bodyX,bodyY,bodyWidth,bodyHeight);
   if(item)place(item,headX+item.x*headScale,headY+item.y*headScale,item.w*headScale,item.h*headScale);
 }
 $("original-Outfit").value=chosenParts.Outfit;
 $("original-Outfit").disabled=!outfitChoices.length||!editable("日常造型");
 for(const [slot,input] of realInputs){
    input.value=chosenParts[slot];
    input.disabled=!editable(lookGroup(slot));
 }
  note.textContent=[
   "本机原版 Sprite",
   unavailable.length?"该朝向缺少："+unavailable.join("、"):"",
   substituted.length?"侧面使用已有攻击件："+substituted.join("、"):""
 ].filter(Boolean).join(" · ");
}



