"""Build two privacy-safe offline Telegram-style human review pages for each reviewer.

All data comes from the frozen private v2 benchmark. Phase 1 strips all original
bot decision/delivery details; Phase 2 shows the exact persisted sent message.
No server, network request, dependencies, secret, or production operation.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "v2_private_sanitized.json"
DATASET = json.loads(SOURCE.read_text(encoding="utf-8"))
assert len(DATASET["cases"]) == 200
SHA = DATASET["dataset_sha256"]
assert hashlib.sha256(
    json.dumps(DATASET["cases"], sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
).hexdigest() == SHA

HTML = r"""<!doctype html>
<html lang="ru">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>
<meta name="color-scheme" content="light"/>
<title>CCWBot — оценка уведомлений · __REVIEWER__ / этап __PHASE__</title>
<style>
:root{font-family:Inter,-apple-system,BlinkMacSystemFont,"Segoe UI",Arial,sans-serif;color:#17212b;background:#eef3f8;font-size:15px}
*{box-sizing:border-box}body{margin:0}.top{display:flex;align-items:center;justify-content:space-between;gap:12px;background:white;padding:15px max(18px,calc((100% - 1140px)/2));border-bottom:1px solid #e0e9f2}
.brand{display:flex;align-items:center;gap:11px;font-size:18px;font-weight:750}.logo{width:39px;height:39px;border-radius:50%;display:grid;place-items:center;background:#3390ec;color:#fff;font-weight:800;letter-spacing:-1px}
.muted{color:#708396;font-size:13px}.stage{background:#eaf4ff;color:#236cb0;padding:8px 13px;border-radius:15px;font-size:12px;font-weight:750}
.layout{max-width:1140px;margin:27px auto;padding:0 20px;display:grid;grid-template-columns:minmax(0,1.25fr) minmax(300px,.8fr);gap:22px;align-items:start}
.viewer{background:#dce9d9;min-height:560px;border:1px solid #ceded0;border-radius:15px;box-shadow:0 10px 30px #738a9a25;overflow:hidden}
.chat-head{background:#fff;display:flex;align-items:center;gap:11px;padding:14px 20px;box-shadow:0 2px 7px #00000008}
.chat-logo{width:40px;height:40px;background:#3390ec;border-radius:50%;display:grid;place-items:center;color:#fff;font-weight:800}
.chat-subtitle{font-size:12px;color:#8091a0}.chat-body{padding:24px 19px 38px;min-height:470px;background:radial-gradient(circle at 8% 30%,#e5f0e1 0,#e5f0e1 2px,transparent 2.2px) 0 0/36px 36px,#dce9d9}
.day{margin:0 auto 20px;width:max-content;background:#7f9ba05c;border-radius:20px;color:#fff;font-size:12px;font-weight:650;padding:7px 13px}
.bubble{background:#fff;max-width:590px;margin:0 15px 0 4px;padding:15px 18px;border-radius:13px 13px 13px 5px;box-shadow:0 3px 6px #18273717;line-height:1.52;font-size:14px;overflow-wrap:anywhere}
.meta{display:flex;align-items:center;gap:9px;margin-bottom:10px}.meta strong{color:#2782d2}.meta span{font-size:11px;color:#92a1ad}
.title{font-weight:800;font-size:19px;margin:8px 0 10px}.change{font-size:25px;font-weight:850;margin:4px 0 6px;letter-spacing:-.5px}.up{color:#168456}.down{color:#c85a48}
.price{font-size:21px;font-weight:740;margin:2px 0 11px}.sub{font-size:13px;color:#506577}
.fact{display:flex;gap:10px;justify-content:space-between;border-top:1px solid #edf0f3;padding:9px 0;font-size:13px}.fact .lab{color:#668092}.fact .val{font-weight:650;text-align:right}
.graph{width:100%;height:120px;margin:10px 0 0;background:#f7fafc;border:1px solid #eaf0f5;border-radius:9px}
.notice{color:#668092;background:#f2f8ff;border-radius:9px;font-size:12px;padding:10px 12px;margin-top:12px}
.news{margin-top:15px;background:#f7fafc;border-left:3px solid #8eb9de;padding:10px 12px;border-radius:4px}
.news strong{font-size:13px;color:#3d6078}.newsline{font-size:13px;margin-top:7px}.newsline span{color:#8193a0;font-size:12px}
.original{white-space:pre-wrap;font-size:14px;line-height:1.55;overflow-wrap:anywhere}
.time{margin-top:12px;font-size:11px;color:#9eaab5;text-align:right}.secondary{margin-top:12px;color:#40586a;font-size:12px}
.review{background:white;border:1px solid #e0e8f0;border-radius:16px;padding:23px 24px;box-shadow:0 12px 30px #a8bac324}
.eyebrow{text-transform:uppercase;color:#2583cc;font-size:11px;font-weight:850;letter-spacing:1px;margin-bottom:9px}
h1{font-size:23px;line-height:1.25;margin:0 0 11px;letter-spacing:-.4px}
.desc{color:#657c90;line-height:1.55;margin:0 0 20px;font-size:13px}
.step{display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;font-size:13px;font-weight:730}
.track{height:8px;background:#e8f0f7;border-radius:9px;overflow:hidden;margin-bottom:20px}
.fill{height:100%;background:#3390ec;transition:width .2s}
.question{font-size:17px;font-weight:770;margin:18px 0 14px;line-height:1.36}
.choice{width:100%;padding:13px 15px;display:flex;align-items:center;gap:12px;background:#fff;border:1.5px solid #dce7ee;border-radius:11px;margin-top:9px;text-align:left;cursor:pointer;font:inherit;font-weight:650;color:#1d354a}
.choice:hover,.choice:focus-visible{border-color:#78b5ec;background:#f7fbff}.choice .circle{width:25px;height:25px;display:grid;place-items:center;border-radius:50%;background:#f0f5fb;color:#2372b7;font-weight:850}
.choice.selected{background:#eaf5ff;border-color:#3390ec;box-shadow:0 0 0 1px #3390ec inset}
.more{border-top:1px solid #eaf0f4;margin-top:17px;padding-top:14px}details{margin-top:12px;background:#f5f8fa;border:1px solid #edf1f5;border-radius:10px;padding:9px 12px}
summary{cursor:pointer;color:#3b6e94;font-weight:660;font-size:12px}
textarea{width:100%;resize:vertical;padding:10px;border:1px solid #dce5ed;border-radius:9px;min-height:60px;font:inherit;font-size:13px;color:#203b50;margin-top:9px}
.actions{display:flex;align-items:center;gap:9px;margin-top:20px;flex-wrap:wrap}button{font:inherit}
.btn{border:0;border-radius:10px;padding:11px 15px;background:#3390ec;color:#fff;font-weight:720;cursor:pointer}
.btn:hover{background:#2479d1}.btn:disabled{opacity:.37;cursor:not-allowed}.btn.secondary{background:#eaf3fb;color:#2777b9}.btn.secondary:hover{background:#d7ecfd}
.privacy{margin:18px 0;color:#6d8394;font-size:12px;line-height:1.5}
.bottom{margin-top:16px;border-top:1px solid #eaf0f3;padding-top:15px;display:flex;gap:10px;flex-wrap:wrap}
.link{border:0;background:none;color:#287ab5;font-size:12px;cursor:pointer;font-weight:730;padding:8px}
.import{display:none}
.complete{display:none;padding:9px 12px;border-radius:10px;background:#f0fbf3;color:#16794e;font-size:13px;margin:11px 0}
.legend{font-size:12px;color:#788b99;margin:5px 0}
.mobilehint{display:none}
@media(max-width:840px){.layout{grid-template-columns:1fr;padding:0 10px;margin:12px auto;gap:12px}.viewer{min-height:auto}.chat-body{min-height:300px;padding:17px 9px 20px}.bubble{margin:0 7px;max-width:unset}.review{padding:17px}.top{padding:11px 14px}.stage{font-size:10px;padding:6px 9px}.brand{font-size:15px}.mobilehint{display:block}}
</style>
</head>
<body>
<header class="top">
 <div class="brand"><div class="logo">CW</div><div>CCWBot <div class="muted">Оценка качества уведомлений</div></div></div>
 <div class="stage" id="stage-label"></div>
</header>
<div class="layout">
 <section class="viewer" aria-label="Предпросмотр в стиле Telegram">
  <div class="chat-head"><div class="chat-logo">CW</div><div><strong>CCWBot</strong><div class="chat-subtitle">Уведомления о рынке криптовалют</div></div></div>
  <div class="chat-body"><div class="day" id="date-label"></div><article class="bubble"><div class="meta"><strong>CCWBot</strong><span id="bubble-tag"></span></div><div id="message"></div><div class="time" id="msg-time"></div></article></div>
 </section>
 <aside class="review">
  <div class="eyebrow" id="eyebrow"></div>
  <h1 id="heading"></h1>
  <p class="desc" id="guide"></p>
  <div class="step"><span id="counter"></span><span id="done-count"></span></div>
  <div class="track"><div class="fill" id="bar"></div></div>
  <div id="questions"></div>
  <details class="more" id="details"><summary>Дополнительные рыночные факты (необязательно)</summary><div id="extra" class="secondary"></div></details>
  <div class="actions">
    <button class="btn secondary" id="prev">← Назад</button>
    <button class="btn" id="next">Дальше →</button>
    <button class="link" id="next-unrated">Найти без оценки</button>
  </div>
  <div class="complete" id="completed">Все оценки заполнены. Скачайте ответы и передайте владельцу проекта.</div>
  <div class="bottom">
    <button class="btn secondary" id="export">↓ Скачать мои ответы</button>
    <button class="link" id="import-button">Загрузить сохранённые ответы</button>
    <input class="import" type="file" accept=".json,application/json" id="import"/>
  </div>
  <p class="privacy">Работает без интернета. Ответы сохраняются только в браузере; кнопка «Скачать» создаёт JSON-файл для передачи владельцу. Данные не отправляются на сервер.</p>
  <p class="legend" id="dataset-label"></p>
 </aside>
</div>
<script>
"use strict";
const PHASE=__PHASE__, REVIEWER=__REVIEWER__, HASH=__HASH__;
const ITEMS=__ITEMS__;
const STORE="ccwbot-review-v2-"+HASH+"-"+REVIEWER+"-"+PHASE;
const $=id=>document.getElementById(id);
const responses=(()=>{try{return JSON.parse(localStorage.getItem(STORE)||"{}")}catch{return {}}})();
let current=0;
const coinNames={BTC:"Bitcoin",ETH:"Ethereum",GRAM:"Gram",SOL:"Solana"};
const e=s=>String(s===null||s===undefined?"":s).replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
const display=v=>v===null||v===undefined||v===""?"—":String(v);
const signed=(x,d=2)=>{if(!Number.isFinite(Number(x)))return "—";let v=Number(x);return (v>0?"+":"")+v.toLocaleString("ru-RU",{maximumFractionDigits:d,minimumFractionDigits:d})+"%";};
const num=x=>{if(x===null||x===undefined||!Number.isFinite(Number(x)))return "—";let v=Number(x);let digs=Math.abs(v)<1?6:Math.abs(v)<100?4:2;return "$"+v.toLocaleString("en-US",{minimumFractionDigits:Math.min(digs,2),maximumFractionDigits:digs});};
const minutes=n=>{let x=Number(n);if(!Number.isFinite(x)||x<0)return "";if(x<60)return Math.round(x)+" мин";if(x<1440)return Math.floor(x/60)+" ч "+Math.round(x%60)+" мин";return Math.floor(x/1440)+" дн "+Math.round((x%1440)/60)+" ч";};
function store(){try{localStorage.setItem(STORE,JSON.stringify(responses))}catch{}}
function get(i){return responses[ITEMS[i].id]||{}}
function done(i){const a=get(i);return PHASE===1?["alert","no_alert","ambiguous"].includes(a.warrant):(typeof a.useful==="boolean");}
function progress(){return ITEMS.filter((_,i)=>done(i)).length}
function tags(markup){$("message").innerHTML=markup}
function infoRow(label,value){return '<div class="fact"><span class="lab">'+e(label)+'</span><span class="val">'+e(display(value))+'</span></div>'}
function drawSparkline(snapshots){let vals=(snapshots||[]).filter(x=>typeof x.p==="number"&&typeof x.m==="number").sort((a,b)=>a.m-b.m);if(vals.length<2)return "";
 const min=Math.min(...vals.map(x=>x.p)),max=Math.max(...vals.map(x=>x.p));
 const range=max-min||1, first=vals[0].m,last=vals[vals.length-1].m,span=last-first||1;
 const pts=vals.map(x=>(16+((x.m-first)/span)*324).toFixed(1)+","+(105-((x.p-min)/range)*90).toFixed(1)).join(" ");
 const rising=vals[vals.length-1].p>=vals[0].p;
 return '<svg class="graph" viewBox="0 0 356 120" role="img" aria-label="Траектория сохранённых ценовых снимков"><line x1="10" y1="105" x2="346" y2="105" stroke="#e0eaf2"/><polyline points="'+pts+'" fill="none" stroke="'+(rising?"#299e79":"#e17a66")+'" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/></svg><div class="muted">Сохранённые точки цены, слева направо по времени</div>';
}
function renderFacts(m,prev,last,news){
 let s=infoRow("Цена",num(m.price))
       +infoRow("Изменение за "+(minutes(m.analysed_window_minutes)||"окно анализа"),signed(m.chg_window_percent))
       +infoRow("За последние 24 часа",signed(m.chg24h_percent));
 if(last&&last.price!==null&&last.price!==undefined)
    s+=infoRow("После прошлого уведомления",m.chg_since_msg_percent===null||m.chg_since_msg_percent===undefined?"нет данных":signed(m.chg_since_msg_percent));
 if(prev&&Number.isFinite(Number(prev.age_minutes)))
    s+=infoRow("Предыдущее событие BTC/монеты",minutes(prev.age_minutes)+" назад");
 s+=drawSparkline(m.snapshots);
 if(Array.isArray(news)&&news.length) {
   s+='<div class="news"><strong>Новости рядом с событием (не обязательно причина):</strong>';
   for(const n of news.slice(0,3))s+='<div class="newsline">'+e(n.title||n.summary||"Новость")+(n.source?' <span>· '+e(n.source)+'</span>':'')+'</div>';
   s+='</div>';
 }else s+='<div class="notice">Связанных новостей в исходном анализе не было.</div>';
 return s;
}
function answer(key,val){const id=ITEMS[current].id;responses[id]??={};responses[id][key]=val;store();renderQuestion();renderProgress();}
function renderQuestion(){
 let a=get(current),html='';
 if(PHASE===1){
  html='<div class="question">Вы хотели бы получить такое уведомление?</div>';
  [["alert","Да, это важно","✓"],["no_alert","Нет, обычное движение рынка","×"],["ambiguous","Не уверен / мало контекста","?"]].forEach(([v,t,ic])=>{
    html+='<button class="choice '+(a.warrant===v?"selected":"")+'" data-key="warrant" data-value="'+v+'"><span class="circle">'+ic+'</span><span>'+e(t)+'</span></button>';
  });
 }else{
  html='<div class="question">Есть ли в сообщении реальная польза?</div>';
  html+='<div class="muted">Что-то кроме повторения цены и процента изменения.</div>';
  html+='<button class="choice '+(a.useful===true?"selected":"")+'" data-key="useful" data-value="true"><span class="circle">✓</span> Да, полезно</button>';
  html+='<button class="choice '+(a.useful===false?"selected":"")+'" data-key="useful" data-value="false"><span class="circle">×</span> Нет, бесполезно</button>';
  html+='<div class="question">Нашли ли вы очевидную фактическую ошибку?</div>';
  html+='<div class="muted">Это НЕ обязательная проверка. Без независимых данных нельзя подтвердить достоверность. Если вы не сверяли цифры и описание с рыночными фактами, оставьте «Не могу проверить». Для этого раскрывать дополнительные сведения необязательно.</div>';
  html+='<button class="choice '+(a.factual===false?"selected":"")+'" data-key="factual" data-value="false"><span class="circle">×</span> Да, могу указать конкретную ошибку</button>';
  html+='<button class="choice '+(a.factual===true?"selected":"")+'" data-key="factual" data-value="true"><span class="circle">✓</span> Проверил по данным — факты верны</button>';
  html+='<button class="choice '+(a.factual===undefined||a.factual===null?"selected":"")+'" data-key="factual" data-value="unknown"><span class="circle">?</span> Не могу проверить (по умолчанию)</button>';
 }
 html+='<div class="more"><div class="muted">'+(PHASE===1?"Комментарий — по желанию":"Если вы обнаружили ошибку, укажите конкретное утверждение. Если не проверяли — комментарий не нужен.")+'</div><textarea id="note" placeholder="Ваш комментарий..."></textarea></div>';
 $("questions").innerHTML=html;
 $("note").value=a.note||"";
 $("note").addEventListener("input",ev=>{responses[ITEMS[current].id]??={};responses[ITEMS[current].id].note=ev.target.value;store()});
 $("questions").querySelectorAll(".choice").forEach(btn=>btn.addEventListener("click",()=>answer(btn.dataset.key,btn.dataset.value==="true"?true:btn.dataset.value==="false"?false:btn.dataset.value==="unknown"?null:btn.dataset.value)));
}
function renderProgress(){
 const n=progress();
 $("counter").textContent="Ситуация "+(current+1)+" из "+ITEMS.length;
 $("done-count").textContent="Оценено: "+n+"/"+ITEMS.length;
 $("bar").style.width=100*n/ITEMS.length+"%";
 $("prev").disabled=current===0;
 $("next").disabled=current===ITEMS.length-1;
 $("completed").style.display=n===ITEMS.length?"block":"none";
}
function render(){
 const c=ITEMS[current],m=c.market||{},prev=c.previous||{},last=c.last_msg||{};
 $("date-label").textContent=display(c.time).slice(0,16).replace("T"," · ")+" UTC";
 $("msg-time").textContent=display(c.time).slice(11,16)+" UTC";
 $("bubble-tag").textContent=PHASE===1?"рыночный пример":"историческое сообщение";
 $("details").open=false;
 if(PHASE===1){
    const v=Number(m.chg_window_percent);const direction=v>0?"выросла":v<0?"снизилась":"не изменилась";
    $("message").innerHTML='<div class="title">'+e(coinNames[c.symbol]||c.symbol)+' · '+e(c.symbol)+'</div>'
      +'<div class="sub">Движение рынка за '+e(minutes(m.analysed_window_minutes))+'</div>'
      +'<div class="change '+(v>=0?"up":"down")+'">'+e(signed(v))+'</div>'
      +'<div class="sub">Цена '+e(c.symbol)+' '+direction+' за указанный период</div>'
      +renderFacts(m,prev,last,c.news)
      +'<div class="notice">Это нейтральный пример из реальных рыночных данных, <b>не копия отправленного ботом сообщения</b>. Оригинальное решение скрыто.</div>';
 }else{
    $("message").innerHTML='<div class="original"></div><div class="notice">Это точный сохранённый текст действительно отправленного уведомления.</div>';
    $("message").querySelector(".original").textContent=c.final_message;
 }
 $("extra").innerHTML='<p>'+infoRow("30 минут",signed(m.chg30m_percent))+infoRow("1 час",signed(m.chg1h_percent))+infoRow("Сравнение с историей, процентиль",display(m.relative_window_percentile_30d))+'</p>'
    +'<div class="muted">Точки цены и новости помогают оценить контекст, но не доказывают правдивость всех утверждений. Процентиль не является автоматическим порогом значимости.</div>'
    +(PHASE===2?renderFacts(m,prev,last,c.news):"");
 renderQuestion();renderProgress();
}
function goto(i){if(i<0||i>=ITEMS.length)return;current=i;render();window.scrollTo({top:0,behavior:"smooth"})}
$("prev").addEventListener("click",()=>goto(current-1));
$("next").addEventListener("click",()=>goto(current+1));
$("next-unrated").addEventListener("click",()=>{for(let offset=1;offset<=ITEMS.length;offset++){let i=(current+offset)%ITEMS.length;if(!done(i)){goto(i);return}}alert("Все случаи оценены. Скачайте ответы.")});
function saveFile(name,data){const blob=new Blob([JSON.stringify(data,null,2)],{type:"application/json;charset=utf-8"}),url=URL.createObjectURL(blob);
 const anchor=document.createElement("a");anchor.href=url;anchor.download=name;document.body.append(anchor);anchor.click();anchor.remove();setTimeout(()=>URL.revokeObjectURL(url),1000)}
$("export").addEventListener("click",()=>{
 const answers=ITEMS.filter((c,i)=>done(i)).map(c=>({id:c.id,...responses[c.id],...(PHASE===2?{factual:typeof responses[c.id]?.factual==="boolean"?responses[c.id].factual:null}:{})}));
 const doc={schema_version:1,dataset_sha256:HASH,reviewer_id:REVIEWER,phase:PHASE===1?"significance":"message",
   export_utc:new Date().toISOString(),expected_cases:ITEMS.length,completed_cases:answers.length,answers};
 if(answers.length<ITEMS.length&&!confirm("Оценены не все случаи ("+answers.length+"/"+ITEMS.length+"). Всё равно скачать промежуточный результат?"))return;
 saveFile("CCWBot_"+REVIEWER+"_PHASE"+PHASE+"_answers.json",doc);
});
$("import-button").addEventListener("click",()=>$("import").click());
$("import").addEventListener("change",async ev=>{
 const file=ev.target.files&&ev.target.files[0];if(!file)return;
 try {
   const doc=JSON.parse(await file.text()),phase=PHASE===1?"significance":"message";
   if(doc.dataset_sha256!==HASH||doc.reviewer_id!==REVIEWER||doc.phase!==phase||!Array.isArray(doc.answers))
     throw Error("Другой набор данных, оценщик или этап");
   const ids=new Set(ITEMS.map(x=>x.id));
   for(const a of doc.answers){if(ids.has(a.id))responses[a.id]={...a,id:undefined}}
   store();render();alert("Ответы загружены: "+doc.answers.length);
 }catch(err){alert("Не удалось загрузить: "+err.message)}
 ev.target.value="";
});
$("stage-label").textContent="Оценщик "+(REVIEWER==="A"?"A · вы":"B · друг")+" • этап "+PHASE+"/2";
$("eyebrow").textContent=PHASE===1?"Этап 1 · значимость":"Этап 2 · качество текста";
$("heading").textContent=PHASE===1?"Нужен ли такой алерт?":"Хорошее ли это сообщение?";
$("guide").textContent=PHASE===1
?"Перед вами реальные рыночные ситуации, оформленные как Telegram-уведомления. Это НЕ обязательно отправленные алерты: ответ бота скрыт. Просто решите, хотели бы вы получить уведомление о таком движении."
:"Перед вами реальные сообщения, которые бот действительно отправлял. Оцените пользу текста. Проверка фактов необязательна: выбирайте «Не могу проверить», если не сверяли утверждения с независимыми рыночными данными. Этот этап открывайте после завершения первого этапа ОБОИМИ оценщиками.";
$("dataset-label").textContent="Набор "+HASH.slice(0,12)+" · "+ITEMS.length+" случаев";
render();
</script></body></html>
"""

def trim(c):
    f=c["input"]
    m=f["market"]
    market_fields=("price","chg_window_percent","chg24h_percent","chg30m_percent","chg1h_percent",
                   "chg_since_msg_percent","analysed_window_minutes","relative_window_percentile_30d",
                   "snapshots")
    return {
        "id":c["id"],"symbol":c["symbol"],"time":f.get("timestamp_utc"),
        "market":{k:m.get(k) for k in market_fields},
        "news":[{"title":n.get("title"),"summary":n.get("summary"),"source":n.get("source")}
                for n in (f.get("news") or [])[:4] if isinstance(n,dict)],
        "previous":{"age_minutes":(f.get("previous_event_alert") or {}).get("age_minutes")},
        "last_msg":{"price":(f.get("last_msg") or {}).get("price")},
    }
for reviewer in ("A","B"):
    for phase in (1,2):
        cases=DATASET["cases"] if phase==1 else [
            c for c in DATASET["cases"] if c.get("observed",{}).get("final_message")
        ]
        assert (len(cases)==200 if phase==1 else len(cases)==72)
        cards=[{
           **trim(c),
           **({"final_message":c["observed"]["final_message"]} if phase==2 else {})
        } for c in cases]
        assert all("should_alert" not in json.dumps(card) and
                   "delivered_count" not in json.dumps(card) and
                   "sampling_cohort" not in json.dumps(card) for card in cards)
        page=HTML.replace("__PHASE__",str(phase))
        page=page.replace("__REVIEWER__",json.dumps(reviewer))
        page=page.replace("__HASH__",json.dumps(SHA))
        page=page.replace("__ITEMS__",json.dumps(cards,ensure_ascii=False).replace("</","<\\/"))
        target=ROOT / f"CCWBot_Reviewer_{reviewer}_PHASE{phase}.html"
        target.write_text(page,encoding="utf-8")
        print(target.name,"cases",len(cards),"bytes",target.stat().st_size)
print("SHA",SHA)
