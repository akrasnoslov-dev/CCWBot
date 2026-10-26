"""Generate a fully offline, source-only owner review form for CCW-29 unseen holdout.
No production bot outputs or model predictions go into the review page.
"""
from pathlib import Path
import json,hashlib,html
F=Path(r"D:\Projects\CCWBot\reports\event-alert-review-20261016\ccw29_private\fresh_holdout")
packet=json.loads((F/"holdout_20_blind_packet_PRIVATE.json").read_text(encoding="utf-8"))
assert len(packet["cases"])==20 and packet["dataset_sha256"]=="cb087b1a52e32b48f96dabda9d9dbf72744fcdb37c273a906572567005fef873"
data=json.dumps(packet,ensure_ascii=False,separators=(",",":")).replace("<","\\u003c").replace(">","\\u003e").replace("&","\\u0026")
template=r'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>CCW-29 — Blind Owner Review (20 New Market Cases)</title>
<style>
:root{font-family:system-ui,sans-serif;color-scheme:light;--ink:#202630;--light:#64748b;--line:#dbe1eb}
body{max-width:1100px;margin:28px auto;padding:0 18px;color:var(--ink);background:#f8fafc;font-size:15px}
header,.panel{background:white;border:1px solid var(--line);border-radius:12px;padding:18px 22px;margin-bottom:16px}
h1{font-size:23px;margin:0 0 6px}h2{font-size:18px}.muted{color:var(--light)}
.grid{display:grid;grid-template-columns:1fr 1fr;gap:12px}.value{font-size:20px;font-weight:700}
.metric{background:#f4f7fb;padding:11px;border-radius:8px}.metric small{display:block;color:var(--light);margin-bottom:6px}
button{cursor:pointer;border:1px solid #b9c4d5;padding:10px 14px;border-radius:8px;background:white;font-size:14px}
button.primary{background:#1d4ed8;color:white;border-color:#1d4ed8}button:hover{filter:brightness(.96)}
nav{display:flex;align-items:center;justify-content:space-between;gap:8px}
.radiobar{display:flex;flex-wrap:wrap;gap:18px;margin:12px 0}
textarea{width:100%;box-sizing:border-box;min-height:86px;padding:10px;border-radius:8px;border:1px solid var(--line)}
pre{white-space:pre-wrap;overflow-wrap:anywhere;background:#f5f8fd;padding:14px;border-radius:8px;font-size:13px}
details{margin-top:12px}.note{background:#fffbea;border:1px solid #f1e5b8;padding:12px;border-radius:8px}
@media(max-width:640px){.grid{grid-template-columns:1fr}}
</style></head><body><header>
<h1>CCW-29: New Event Alert Blind Review</h1><p class="muted">20 fresh real-market cases, 17–22 October 2026. No E1/E2 predictions, old production decisions, or previous reviewer labels are included.</p>
<p class="note">For every case judge whether the CURRENT observed price movement is materially significant and genuinely new compared with previous alerts, considering market evidence first. News alone must not trigger an alert. Choose Ambiguous when evidence cannot support a decisive judgment. Numeric values are context, not hard thresholds.</p>
<div id="progress" class="muted"></div></header>
<main class="panel"><nav><button id="prev">Previous</button><strong id="position"></strong><button id="next">Next</button></nav>
<h2 id="heading"></h2><div class="grid" id="metrics"></div>
<h3>Observed price snapshots</h3><pre id="snaps"></pre>
<h3>Earlier notification / event context</h3><pre id="prior"></pre>
<h3>News context (supporting only)</h3><pre id="news"></pre>
<details><summary>Complete original model-visible market input (source only)</summary><pre id="raw"></pre></details>
<h3>Your independent judgement</h3>
<div class="radiobar">
<label><input type="radio" name="warrant" value="alert"> Alert</label>
<label><input type="radio" name="warrant" value="no_alert"> No alert</label>
<label><input type="radio" name="warrant" value="ambiguous"> Ambiguous</label>
</div>
<label for="reason"><strong>Brief evidence-based reason</strong></label><textarea id="reason" placeholder="What in the observed current path makes this materially new or routine?"></textarea>
</main><div class="panel"><nav><span class="muted">Completely offline. Save labels before closing this tab.</span><button id="export" class="primary">Export blind review JSON</button></nav></div>
<script id="packet" type="application/json">__PACKET__</script>
<script>
"use strict";
const source=JSON.parse(document.getElementById("packet").textContent); const answers={}; let index=0;
const el=id=>document.getElementById(id);
function text(id,str){el(id).textContent=str}
function metric(label,v){const q=document.createElement("div");q.className="metric";const s=document.createElement("small");s.textContent=label;const b=document.createElement("div");b.className="value";b.textContent=v===null||v===undefined?"not supplied":String(v);q.append(s,b);return q}
function view(){
 const c=source.cases[index],f=c.input,m=f.market||{};
 text("position",(index+1)+" / "+source.cases.length);text("heading",c.symbol+" · "+(f.timestamp_utc||"")+"\n"+c.id);
 const box=el("metrics");box.replaceChildren();
 for(const [name,v] of [["Current price",m.price],["Observed window (min)",m.analysed_window_minutes],["Window change (%)",m.chg_window_percent],["30 min (%)",m.chg30m_percent],["1 hour (%)",m.chg1h_percent],["24 hour (%)",m.chg24h_percent],["Historical percentile (context)",m.relative_window_percentile_30d],["Since previous message (%)",m.chg_since_msg_percent]])box.append(metric(name,v));
 text("snaps",JSON.stringify(m.snapshots||[],null,2));
 text("prior",JSON.stringify({last_msg:f.last_msg,previous_event_alert:f.previous_event_alert,recent_event_counts:f.recent_event_counts},null,2));
 text("news",JSON.stringify(f.news||[],null,2));
 text("raw",JSON.stringify(f,null,2));
 const a=answers[c.id]||{};document.querySelectorAll("input[name=warrant]").forEach(x=>x.checked===false?null:null);
 document.querySelectorAll("input[name=warrant]").forEach(x=>{x.checked=x.value===a.warrant});
 el("reason").value=a.rationale||"";
 text("progress",Object.values(answers).filter(v=>v.warrant&&v.rationale&&v.rationale.trim()).length+" of "+source.cases.length+" complete (decision + reason)");
 el("prev").disabled=index===0;el("next").disabled=index===source.cases.length-1;
}
function store(){const c=source.cases[index];const a=answers[c.id]||{};const checked=document.querySelector("input[name=warrant]:checked");a.warrant=checked?.value||null;a.rationale=el("reason").value;answers[c.id]=a;text("progress",Object.values(answers).filter(v=>v.warrant&&v.rationale&&v.rationale.trim()).length+" of "+source.cases.length+" complete (decision + reason)")}
el("prev").onclick=()=>{store();if(index>0)index--;view()};
el("next").onclick=()=>{store();if(index<source.cases.length-1)index++;view()};
el("reason").addEventListener("input",store);document.querySelectorAll("input[name=warrant]").forEach(x=>x.addEventListener("change",store));
el("export").onclick=()=>{
 store();const incomplete=source.cases.filter(c=>!answers[c.id]?.warrant||!answers[c.id]?.rationale?.trim()).length;
 if(incomplete&&!confirm(incomplete+" cases are incomplete. Export partial review anyway?"))return;
 const record={schema_version:1,dataset_sha256:source.dataset_sha256,reviewer_id:"independent_owner_review",review_completed_at_utc:new Date().toISOString(),labels:source.cases.map(c=>({id:c.id,input_sha256:c.input_sha256,warrant:answers[c.id]?.warrant||null,rationale:answers[c.id]?.rationale||""}))};
 const blob=new Blob([JSON.stringify(record,null,2)],{type:"application/json"});const url=URL.createObjectURL(blob);
 const a=document.createElement("a");a.href=url;a.download="ccw29_owner_blind_review_20.json";a.click();URL.revokeObjectURL(url);
};
view();
</script></body></html>'''
assert '"observed"' not in data and '"should_alert"' not in data and '"decision"' not in data and '"provider"' not in data
htmltext=template.replace("__PACKET__",data)
out=F/"CCW29_OWNER_BLIND_REVIEW.html"
out.write_text(htmltext,encoding="utf-8")
print(json.dumps({"file":str(out),"bytes":out.stat().st_size,"sha256":hashlib.sha256(out.read_bytes()).hexdigest(),"cases":len(packet["cases"]),"provider_outputs_included":False,"production_labels_included":False}))
