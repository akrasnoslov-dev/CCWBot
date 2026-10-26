"""Build private, offline A-versus-Reviewer-C disagreement adjudication UI (66 cases)."""
from __future__ import annotations

import hashlib
import json
import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PRIVATE = ROOT / "ccw41_private"
UI = ROOT / "telegram_review"
UI.mkdir(exist_ok=True)
TARGET = UI / "CCWBot_REVIEW_A_vs_GPT6_66.html"

dataset = json.loads((ROOT / "v2_private_sanitized.json").read_text(encoding="utf-8"))
human = json.loads((ROOT / "reviewer_A_significance_for_pr1.json").read_text(encoding="utf-8"))
sealed = json.loads((PRIVATE / "reviewer_c_sealed.json").read_text(encoding="utf-8"))
run = json.loads((PRIVATE / "run_manifest.json").read_text(encoding="utf-8"))
assert dataset["dataset_sha256"] == human["dataset_sha256"] == sealed["dataset_sha256"]
assert hashlib.sha256((PRIVATE / "reviewer_c_sealed.json").read_bytes()).hexdigest() == run["reviewer_c_sha256"]

base = (UI / "CCWBot_Reviewer_A_PHASE1.html").read_text(encoding="utf-8")
before, remain = base.split("const ITEMS=", 1)
embedded, after = remain.split(";\nconst STORE=", 1)
old_cards = json.loads(embedded)
assert len(old_cards) == len(dataset["cases"]) == len(human["labels"]) == len(sealed["results"]) == 200
cards = {card["id"]: card for card in old_cards}
source_by_id = {case["id"]: case for case in dataset["cases"]}
a_by_id = {row["id"]: row["warrant"] for row in human["labels"]}
c_by_id = {row["source_case_id"]: row for row in sealed["results"]}
assert len(cards) == len(source_by_id) == len(a_by_id) == len(c_by_id) == 200
assert set(cards) == set(source_by_id) == set(a_by_id) == set(c_by_id)
assert Counter(a_by_id.values()) == {"alert": 41, "no_alert": 112, "ambiguous": 47}
assert Counter(row["warrant"] for row in c_by_id.values()) == {
    "alert": 31, "no_alert": 167, "ambiguous": 2
}

def evidence_value(context: dict, reference: str):
    if not reference.startswith("input."):
        return "[некорректная ссылка]"
    current = context
    for segment in reference.split(".")[1:]:
        m = re.fullmatch(r"([a-zA-Z_0-9]+)(?:\[([0-9]+)\])?", segment)
        if not m or not isinstance(current, dict) or m[1] not in current:
            return "[недоступно]"
        current = current[m[1]]
        if m[2] is not None:
            if not isinstance(current, list) or int(m[2]) >= len(current):
                return "[недоступно]"
            current = current[int(m[2])]
    if isinstance(current, (dict, list)):
        text = json.dumps(current, ensure_ascii=False)
    elif current is None:
        text = "null"
    else:
        text = str(current)
    return text[:400] + ("…" if len(text) > 400 else "")

def order(row: dict):
    a, c = row["voteA"], row["voteC"]
    priorities = {
        ("alert", "no_alert"): 0,
        ("no_alert", "alert"): 1,
        ("ambiguous", "no_alert"): 2,
        ("alert", "ambiguous"): 3,
        ("ambiguous", "alert"): 4,
        ("no_alert", "ambiguous"): 5,
    }
    return (priorities.get((a, c), 9), row["symbol"], row["time"], row["id"])

out = []
for case_id in cards:
    if a_by_id[case_id] == c_by_id[case_id]["warrant"]:
        continue
    original = source_by_id[case_id]
    result = c_by_id[case_id]
    card = dict(cards[case_id])
    card.update({
        "voteA": a_by_id[case_id],
        "voteC": result["warrant"],
        "confidenceC": result["confidence"],
        "rationaleC": result["rationale"],
        "missingC": result["missing_evidence"],
        "referencesC": [
            {"path": reference, "value": evidence_value(original["input"], reference)}
            for reference in result["evidence_references"]
        ],
        "scenario": original.get("scenario_type"),
    })
    out.append(card)
out.sort(key=order)
assert len(out) == 66, len(out)
assert all(c["voteA"] != c["voteC"] for c in out)
counts = Counter((c["voteA"], c["voteC"]) for c in out)

extra_css = r"""
.comparegrid{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin:12px 0}
.judge{border:1px solid #d7e4ef;border-radius:12px;padding:13px;background:#f7fbff}
.judge.c{background:#f6f2ff;border-color:#e3d6fa}
.judge .who{font-size:12px;color:#5a6f85;font-weight:800;margin-bottom:9px}
.judge .decision{font-size:16px;font-weight:820;line-height:1.3}
.judge .decision.alert{color:#16794e}
.judge .decision.no_alert{color:#b5573a}
.judge .decision.ambiguous{color:#92712f}
.judge .desc2{font-size:12px;color:#455c70;margin-top:9px;line-height:1.5}
.judge details{border:0;background:transparent;padding:0;margin:9px 0 0}
.judge details summary{font-size:12px}
.review-filter{display:flex;gap:9px;flex-wrap:wrap;margin:4px 0 16px}
.review-filter select{font-size:12px;border-radius:8px;border:1px solid #d4e1ed;padding:8px;max-width:100%;background:#f6faff;color:#234b69}
.notice.warn{background:#fff6e8;color:#775b30}
@media(max-width:1100px){.comparegrid{grid-template-columns:1fr}}
"""
before = before.replace("</style>", extra_css + "\n</style>")
before = before.replace(
    "<title>CCWBot — оценка уведомлений · A / этап 1</title>",
    "<title>CCWBot — разногласия Reviewer A и GPT-6 · 66 случаев</title>",
)
before = before.replace(
    '<div id="questions"></div>',
    '<div class="review-filter"><select id="pair-filter" aria-label="Тип расхождения"><option value="">Все типы расхождений</option></select>'
    '<select id="coin-filter" aria-label="Монета"><option value="">Все монеты</option>'
    '<option value="BTC">BTC</option><option value="ETH">ETH</option><option value="GRAM">GRAM</option><option value="SOL">SOL</option></select></div>'
    '<div id="questions"></div>',
)
before = before.replace(
    "Все оценки заполнены. Скачайте ответы и передайте владельцу проекта.",
    "Все 66 расхождений разобраны. Скачайте итоговые решения в JSON.",
)
before = before.replace(
    "Работает без интернета. Ответы сохраняются только в браузере; кнопка «Скачать» создаёт JSON-файл для передачи владельцу. Данные не отправляются на сервер.",
    "Локальный офлайн-опрос. Решения сохраняются в этом браузере; скачайте JSON для резервной копии. Никакой отправки данных в сеть.",
)
before = before.replace("const PHASE=1, REVIEWER=\"A\", HASH=", "const PHASE=1, REVIEWER=\"AC\", HASH=")
before = before.replace("const ITEMS=", "let ITEMS=")
before += "let ITEMS=" + json.dumps(out, ensure_ascii=False).replace("</", "<\\/") + ";\nconst STORE="
whole = before + after

# Globally retain original 66 for filtering and for export even when showing a subset.
store_line = 'const STORE="ccwbot-review-v2-"+HASH+"-"+REVIEWER+"-"+PHASE;'
assert whole.count(store_line) == 1
whole = whole.replace(
    store_line,
    store_line + "\nconst ALL_ITEMS=ITEMS.slice();\n"
)
start = whole.index("function renderQuestion(){")
end = whole.index("function renderProgress(){", start)
review_question = r"""const W_LABEL={
  alert:"Отправить алерт",no_alert:"Не отправлять",ambiguous:"Неоднозначно"
};
const E_CONFI={high:"Высокая",medium:"Средняя",low:"Низкая"};
function renderQuestion(){
 const c=ITEMS[current],a=get(current);
 const ca=W_LABEL[c.voteA]||c.voteA, cc=W_LABEL[c.voteC]||c.voteC;
 let html='<div class="question">Они оценили одно и то же событие по-разному</div>';
 html+='<div class="comparegrid">';
 html+='<div class="judge a"><div class="who">Reviewer A · ваша первая оценка</div>'
     +'<div class="decision '+e(c.voteA)+'">'+e(ca)+'</div>'
     +'<div class="desc2">Первоначальный ответ человека. Обоснование в финальном файле A не сохранялось.</div></div>';
 html+='<div class="judge c"><div class="who">Reviewer C · ChatGPT / GPT-6</div>'
     +'<div class="decision '+e(c.voteC)+'">'+e(cc)+'</div>'
     +'<div class="desc2">Уверенность: '+e(E_CONFI[c.confidenceC]||c.confidenceC)+'</div>'
     +'<details open><summary>Почему ChatGPT решил так (оригинальный текст)</summary>'
     +'<div class="desc2">'+e(c.rationaleC)+'</div></details></div></div>';
 html+='<details><summary>На какие факты опирался ChatGPT ('+c.referencesC.length+')</summary>';
 for(const r of c.referencesC){
    html+='<div class="fact"><span class="lab">'+e(r.path)+'</span>'
      +'<span class="val">'+e(r.value)+'</span></div>';
 }
 if(c.missingC.length){
    html+='<div class="notice warn"><b>Недостающие данные по оценке C:</b> '
       +c.missingC.map(e).join('; ')+'</div>';
 }
 html+='</details>';
 html+='<div class="question">Какое решение вы считаете правильным сейчас?</div>';
 for(const [v,t,ic] of [
    ["alert","Да, нужен алерт","✓"],
    ["no_alert","Нет, не нужен алерт","×"],
    ["ambiguous","Данных недостаточно / спорно","?"]
 ]) {
   let also=[];
   if(c.voteA===v)also.push("A");
   if(c.voteC===v)also.push("GPT-6");
   html+='<button class="choice '+(a.warrant===v?"selected":"")
       +'" data-key="warrant" data-value="'+v+'"><span class="circle">'+ic+'</span>'
       +'<span>'+e(t)+(also.length?' <span class="muted">· '+e(also.join(" + "))+'</span>':'')+'</span></button>';
 }
 html+='<div class="more"><div class="muted">Ваше объяснение / чего не хватает (необязательно)</div>'
     +'<textarea id="note" placeholder="Почему вы подтверждаете или меняете первую оценку?"></textarea></div>';
 $("questions").innerHTML=html;
 $("note").value=a.note||"";
 $("note").addEventListener("input",ev=>{
   responses[c.id]??={};responses[c.id].note=ev.target.value;store();
 });
 $("questions").querySelectorAll(".choice").forEach(btn=>
    btn.addEventListener("click",()=>answer(btn.dataset.key,btn.dataset.value)));
}
"""
whole = whole[:start] + review_question + "\n" + whole[end:]
start = whole.index("function renderProgress(){")
end = whole.index("function render(){", start)
new_progress = r"""function renderProgress(){
 const n=ALL_ITEMS.filter(c=>["alert","no_alert","ambiguous"].includes((responses[c.id]||{}).warrant)).length;
 $("counter").textContent="Ситуация "+(ITEMS.length?current+1:0)+" из "+ITEMS.length;
 $("done-count").textContent="Оценено всего: "+n+"/"+ALL_ITEMS.length;
 $("bar").style.width=100*n/ALL_ITEMS.length+"%";
 $("prev").disabled=current===0;
 $("next").disabled=current===ITEMS.length-1;
 $("completed").style.display=n===ALL_ITEMS.length?"block":"none";
}
"""
whole = whole[:start] + new_progress + "\n" + whole[end:]
whole = whole.replace(
    "function render(){\n const c=ITEMS[current]",
    "function render(){\n if(!ITEMS.length){$(\"message\").innerHTML='<div class=\"notice\">Нет случаев для выбранного фильтра.</div>';$(\"questions\").innerHTML='Выберите другой фильтр.';renderProgress();return;}\n const c=ITEMS[current]"
)
# Old compare copy insists original bot output is hidden, which is accurate.
# Export all 66, not only the visible filter.
whole = whole.replace(
    "const answers=ITEMS.filter((c,i)=>done(i)).map",
    "const answers=ALL_ITEMS.filter(c=>[\"alert\",\"no_alert\",\"ambiguous\"].includes((responses[c.id]||{}).warrant)).map",
)
whole = whole.replace("expected_cases:ITEMS.length,completed_cases:answers.length", "expected_cases:ALL_ITEMS.length,completed_cases:answers.length")
whole = whole.replace('if(answers.length<ITEMS.length&&!confirm(', 'if(answers.length<ALL_ITEMS.length&&!confirm(')
whole = whole.replace('answers.length+"/"+ITEMS.length', 'answers.length+"/"+ALL_ITEMS.length')
whole = whole.replace('new Set(ITEMS.map(x=>x.id))', 'new Set(ALL_ITEMS.map(x=>x.id))')
whole = whole.replace(
    '"CCWBot_"+REVIEWER+"_PHASE"+PHASE+"_answers.json"',
    '"CCWBot_A_vs_GPT6_66_answers.json"',
)
# Restrict imported answers to valid labels, preserve separate AC identity.
whole = whole.replace(
    'if(ids.has(a.id))responses[a.id]={...a,id:undefined}',
    'if(ids.has(a.id)&&["alert","no_alert","ambiguous"].includes(a.warrant))responses[a.id]={warrant:a.warrant,note:typeof a.note==="string"?a.note:""}',
)
# Rewrite end startup text, inject filters, keep offline auto-save and import/export.
end_marker = 'render();\n</script></body></html>'
assert whole.count(end_marker)==1
whole = whole.replace(end_marker, r"""
$("stage-label").textContent="A vs GPT-6 · 66 расхождений";
$("eyebrow").textContent="Дополнительный этап · разбор расхождений";
$("heading").textContent="Кто прав: вы или ChatGPT?";
$("guide").textContent="Только случаи, в которых ваша первая оценка (A) и независимая оценка GPT-6 (C) не совпали. Слева — исходный рыночный контекст, справа — оба ответа и аргументы C. Выберите собственный итоговый ответ; он не изменяет старую оценку A и benchmark автоматически.";
$("dataset-label").textContent="Набор "+HASH.slice(0,12)+" · "+ALL_ITEMS.length+" разных оценок A/C";
const pairCounts={};
for(const c of ALL_ITEMS){const p=c.voteA+"|"+c.voteC;pairCounts[p]=(pairCounts[p]||0)+1}
for(const pair of Object.keys(pairCounts)){
 const [a,c]=pair.split("|");
 const option=document.createElement("option");
 option.value=pair;option.textContent="A: "+W_LABEL[a]+" / GPT-6: "+W_LABEL[c]+" ("+pairCounts[pair]+")";
 $("pair-filter").appendChild(option);
}
function applyFilter(){
 const pair=$("pair-filter").value,coin=$("coin-filter").value;
 ITEMS=ALL_ITEMS.filter(c=>(!pair||(c.voteA+"|"+c.voteC)===pair)&&(!coin||c.symbol===coin));
 current=0;render();
}
$("pair-filter").addEventListener("change",applyFilter);
$("coin-filter").addEventListener("change",applyFilter);
render();
</script></body></html>""")
# Basic structural checks and prohibited-source checks.
assert 'const ALL_ITEMS=ITEMS.slice();' in whole
assert whole.count('function renderQuestion(){')==1
assert whole.count('<html')==1
assert "const PHASE=1, REVIEWER=\"AC\"" in whole
assert 'window.fetch' not in whole and 'XMLHttpRequest' not in whole
TARGET.write_text(whole,encoding="utf-8")
print("CREATED:",TARGET)
print("CASE_COUNT:",len(out))
print("TYPES:",dict(sorted((f"{a}->{c}",count) for (a,c),count in counts.items())))
print("BY_SYMBOL:",dict(sorted(Counter(c["symbol"] for c in out).items())))
print("BYTES:",TARGET.stat().st_size)
print("PARSER_OK:",'function renderQuestion(){' in whole)
