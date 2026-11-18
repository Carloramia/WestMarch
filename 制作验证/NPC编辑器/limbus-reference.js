"use strict";
const limbusReferences = {
  rodion: {
    name:"罗佳 · 待机小人",
    image:"https://static.wikia.nocookie.net/limbuscompany/images/e/e6/LCB_Sinner_Rodion_Idle_Sprite.png/revision/latest?cb=20230805022332",
    url:"https://limbuscompany.fandom.com/wiki/LCB_Sinner_Rodion",
    note:"观察头身比例、外套剪影和武器所占画幅。"
  },
  faust: {
    name:"浮士德 · 待机小人",
    image:"https://static.wikia.nocookie.net/limbuscompany/images/9/9d/The_One_Who_Grips_Faust_Idle_Sprite.png/revision/latest?cb=20231021233345",
    url:"https://limbuscompany.fandom.com/wiki/The_One_Who_Grips_Faust",
    note:"观察肩甲、外衣和武器作为一套战斗造型的轮廓。"
  },
  camille: {
    name:"卡米尔 · 部件参考",
    image:"https://i.imgur.com/9AQ1Sqo.png",
    url:"https://www.reddit.com/r/limbuscompany/comments/1goes22/an_idea_most_not_ingenous_about_camille/",
    note:"观察头、手臂、腿、躯干和武器的拆分。公开样本没有骨骼和挂点数据。"
  },
  ishmael: {
    name:"以实玛利 · 动作表",
    image:"https://www.spriters-resource.com/media/assets/267/269697.png?updated=1755494940",
    url:"https://www.spriters-resource.com/mobile/limbuscompany/asset/269697/",
    note:"观察待机到攻击的轮廓变化及专用动作图。打开来源可查看大图。"
  }
};
const limbusSelect = document.getElementById("limbusSample");
for (const [id, item] of Object.entries(limbusReferences)) limbusSelect.add(new Option(item.name, id));
function drawLimbus(){
  const item=limbusReferences[limbusSelect.value];
  const frame=document.getElementById("limbusStage");
  const status=document.getElementById("limbusStatus");
  const link=document.getElementById("limbusSource");
  link.href=item.url;
  frame.replaceChildren();
  status.textContent=item.note;
  const preview=document.createElement("img");
  preview.alt=item.name;
  preview.referrerPolicy="no-referrer";
  preview.onerror=()=>{
    if(preview.parentNode===frame)status.textContent=item.note+" 当前图片无法载入，可打开来源查看。";
  };
  preview.src=item.image;
  frame.append(preview);
}
limbusSelect.onchange=drawLimbus;

