"""CCW-43 offline source verification, paired scoring, and restricted case error audit."""
from __future__ import annotations
import sys,json,hashlib,collections,statistics
from pathlib import Path
HERE=Path(__file__).resolve().parent; DATA=HERE.parent; ROOT=DATA.parents[1]
sys.path.insert(0,str(ROOT))
from scripts.event_alert_benchmark import load_frozen,_read_evaluations,digest
from scripts.ccw15_prompt_pack import build_prompt, instruction
def read(relative): return json.loads((DATA/relative).read_text(encoding="utf-8"))
def sha(relative): return hashlib.sha256((DATA/relative).read_bytes()).hexdigest()
EXPECTED="ed126380369014e6522cee49009b880cf0350aa7565269d50641c3f1bbdc3bee"
PILOT_SHA="2512e4e340f3074fafc1ee07e497be7b71014e6c2c9b38a6cff2f21c32623ab4"
FROZEN=load_frozen(DATA/"v2_private_sanitized.json")
assert FROZEN["dataset_sha256"]==EXPECTED and len(FROZEN["cases"])==200
cases={x["id"]:x for x in FROZEN["cases"]}
assert len(cases)==200 and collections.Counter(x["symbol"] for x in cases.values())==dict.fromkeys(["BTC","ETH","GRAM","SOL"],50)
a_name,A=_read_evaluations(DATA/"reviewer_A_significance_for_pr1.json",FROZEN)
b_name,B=_read_evaluations(DATA/"reviewer_B_significance_for_pr1.json",FROZEN)
assert len(A)==len(B)==200 and collections.Counter(v["warrant"] for v in A.values())=={"alert":41,"no_alert":112,"ambiguous":47}
Cdoc=read("ccw41_private/reviewer_c_sealed.json")
C={x["source_case_id"]:x for x in Cdoc["results"]}
assert Cdoc["result_count"]==len(C)==200 and set(C)==set(cases)
owner_doc=read("ccw41_private/owner_reference_candidate_v1_20261022.json")
owner={x["id"]:x for x in owner_doc["case_labels"]}
assert len(owner)==200 and set(owner)==set(cases)
assert owner_doc["dataset_sha256"]==EXPECTED
assert all(row["input_sha256"]==cases[id]["input_sha256"] and row["A"]==A[id]["warrant"] and row["B"]==B[id]["warrant"] and row["C"]==C[id]["warrant"] for id,row in owner.items())
assert collections.Counter(x["final"] for x in owner.values())=={"alert":31,"no_alert":159,"ambiguous":10}
assert sum(x["owner_reviewed"] for x in owner.values())==66
assert sum(x["changed_from_A"] for x in owner.values())==53
for label, path in [("dataset","v2_private_sanitized.json"),("A","reviewer_A_significance_for_pr1.json"),("B","reviewer_B_significance_for_pr1.json"),("C","ccw41_private/reviewer_c_sealed.json")]:
    assert owner_doc["source_sha256"][label]==sha(path),label
owner_source=owner_doc["source_sha256"]["owner_66_upload"]
assert owner_source==sha("ccw41_private/owner_ac_66_answers_20261022.original.json")
ledger_path="ccw16_private/pilot-ledger-complete_20261023_120.json"
assert sha(ledger_path)==PILOT_SHA
ledger=read(ledger_path)
previous=read("ccw16_private/pilot-ledger-stopped_20261022_86.json")
manifest=read("ccw16_private/pilot-manifest.json")
assert len(previous["attempts"])==86 and len(ledger["attempts"])==120 and len(manifest["cases"])==20
pilot_ids=[x["id"] for x in manifest["cases"]]
assert len(set(pilot_ids))==20 and all(cases[x["id"]]["input_sha256"]==x["input_sha256"] and cases[x["id"]]["input"]==x["input"] for x in manifest["cases"])
assert all(d.get("dataset_sha256")==EXPECTED for d in (ledger,previous,manifest))
PREV_KEYS={(x["id"],x["prompt"],x["provider"]):x for x in previous["attempts"]}
all_keys={(x["id"],x["prompt"],x["provider"]):x for x in ledger["attempts"]}
assert len(all_keys)==120 and len(PREV_KEYS)==86 and PREV_KEYS.keys()<=all_keys.keys()
assert all(all_keys[k]["decision"]==v["decision"] and all_keys[k]["input_sha256"]==v["input_sha256"] for k,v in PREV_KEYS.items())
PROMPTS=("production","ccw15_materiality_evidence_v1","ccw15_novelty_independent_v1")
for p in PROMPTS:
    assert instruction(p)
for k,row in all_keys.items():
    case_id,prompt,provider=k
    assert case_id in pilot_ids and prompt in PROMPTS and provider in ("groq","cloudflare")
    assert row["status"]=="valid" and row["state"]=="finished" and row["http_status"]==200
    assert row["input_sha256"]==cases[case_id]["input_sha256"]
    assert row["prompt_sha256"]==hashlib.sha256(build_prompt(cases[case_id]["input"],prompt).encode()).hexdigest()
    assert row["decision"]["symbol"]==cases[case_id]["symbol"]
assert collections.Counter((x["prompt"],x["provider"]) for x in ledger["attempts"])=={(p,v):20 for p in PROMPTS for v in ("groq","cloudflare")}
def score(keys,ref):
    ids=list(pilot_ids)
    c=collections.Counter()
    for id in ids:
        truth=ref[id]
        if truth=="ambiguous": c["ambiguous"]+=1;continue
        pred=keys[id]["decision"]["should_alert"]
        c["TP" if truth=="alert" and pred else "FP" if truth=="no_alert" and pred else "FN" if truth=="alert" else "TN"]+=1
    tp,fp,fn=c["TP"],c["FP"],c["FN"]
    return {**{k:c[k] for k in ("TP","FP","FN","TN","ambiguous")},"scored":20-c["ambiguous"],"precision":tp/(tp+fp) if tp+fp else None,"recall":tp/(tp+fn) if tp+fn else None}
Aref={id:x["warrant"] for id,x in A.items()}
Oref={id:x["final"] for id,x in owner.items()}
scores={ref:{v:{p:score({id:all_keys[(id,p,v)] for id in pilot_ids},labs) for p in PROMPTS} for v in ("groq","cloudflare")} for ref,labs in (("original_A",Aref),("owner_20261022",Oref))}
assert all(scores[ref][v][p]["scored"]==(16 if ref=="original_A" else 20) for ref in scores for v in scores[ref] for p in PROMPTS)
def redacted_signals(case):
    i=case["input"];m=i.get("market") or {};old=i.get("previous_event_alert") or {};last=i.get("last_msg") or {}
    snaps=m.get("snapshots") or [];news=i.get("news") or []
    return dict(symbol=case["symbol"],scenario_type=case["scenario_type"],tags=case.get("tags",[]),
      window_minutes=m.get("analysed_window_minutes"),window_pct=m.get("chg_window_percent"),
      pct_1h=m.get("chg1h_percent"),pct_30m=m.get("chg30m_percent"),
      pct_24h=m.get("chg24h_percent"),relative_window_percentile=m.get("relative_window_percentile_30d"),
      since_last_pct=m.get("chg_since_msg_percent"),prior_alert_age_mins=old.get("age_minutes"),
      prior_alert_move_pct=old.get("analysed_window_move"),prior_family=old.get("semantic_family"),
      last_msg_type=last.get("type"),recent_counts=i.get("recent_event_counts"),
      snapshot_count=len(snaps),news_count=len(news),material_news_count=sum(bool(n.get("material")) for n in news))
audit=[]
for id in pilot_ids:
    c=cases[id];e={"id":id,"input_sha256":c["input_sha256"],"original_A":Aref[id],"reviewer_B":B[id]["warrant"],"reviewer_C":C[id]["warrant"],"C_rationale":C[id].get("rationale"),"C_missing_evidence":C[id].get("missing_evidence"),"owner":Oref[id],"owner_reviewed":owner[id]["owner_reviewed"],"signals":redacted_signals(c),"original_context_private":c["input"],"decisions":{}}
    for v in ("groq","cloudflare"):
        e["decisions"][v]={p:all_keys[(id,p,v)]["decision"] for p in PROMPTS}
    audit.append(e)
(HERE/"pilot_case_audit_PRIVATE.json").write_text(json.dumps({"dataset_sha256":EXPECTED,"cases":audit},indent=2),encoding="utf-8")
# 200-case original market context and reviewer provenance; private inspection only
longaudit=[]
for id,c in cases.items():
    longaudit.append({"id":id,"input_sha256":c["input_sha256"],"original_A":Aref[id],"reviewer_B":B[id]["warrant"],"reviewer_C":C[id]["warrant"],"C_rationale":C[id].get("rationale"),"owner":Oref[id],"owner_changed":owner[id]["changed_from_A"],"observed_should_alert":owner[id]["observed_should_alert"],"signals":redacted_signals(c),"original_context_private":c["input"]})
(HERE/"owner_200_case_audit_PRIVATE.json").write_text(json.dumps({"dataset_sha256":EXPECTED,"cases":longaudit},indent=2),encoding="utf-8")
summary={"dataset_sha256":EXPECTED,"ledger_sha256":PILOT_SHA,"immutable_source_sha256":{"dataset":sha("v2_private_sanitized.json"),"reviewer_A":sha("reviewer_A_significance_for_pr1.json"),"reviewer_B":sha("reviewer_B_significance_for_pr1.json"),"reviewer_C":sha("ccw41_private/reviewer_c_sealed.json"),"owner_reference":sha("ccw41_private/owner_reference_candidate_v1_20261022.json"),"owner_votes":owner_source,"pre_restart_86":sha("ccw16_private/pilot-ledger-stopped_20261022_86.json")},"coverage":{"dataset":200,"by_symbol":dict(collections.Counter(x["symbol"] for x in cases.values())),"reviewer_A":dict(collections.Counter(Aref.values())),"reviewer_B":dict(collections.Counter(x["warrant"] for x in B.values())),"reviewer_C":dict(collections.Counter(x["warrant"] for x in C.values())),"owner":dict(collections.Counter(Oref.values())),"owner_reviewed":66,"owner_changed":53,"pilot_distinct_cases":20,"pilot_calls":120,"valid":120,"restarted_preserved":86,"providers":{"groq":60,"cloudflare":60}},"scores":scores}
summary["pilot_groups"]={}
for v in ("groq","cloudflare"):
    for p in PROMPTS:
        rows=[a for a in audit]
        keys=[a["decisions"][v][p] for a in rows]
        pos=[a for a,d in zip(rows,keys) if a["owner"]=="alert" and not d["should_alert"]]
        neg=[a for a,d in zip(rows,keys) if a["owner"]=="no_alert" and d["should_alert"]]
        key=v+"/"+p
        summary["pilot_groups"][key]={"owner_FN_categories":dict(collections.Counter("materiality_not_material" if d["materiality"]!="material" else "novelty_not_new" for a,d in zip(rows,keys) if a["owner"]=="alert" and not d["should_alert"])),"owner_FN_ids":[a["id"] for a in pos],"owner_FP_ids":[a["id"] for a in neg],"owner_FP_by_symbol":dict(collections.Counter(a["signals"]["symbol"] for a in neg)),"total_tokens":sum(all_keys[(a["id"],p,v)].get("total_tokens",0) for a in rows),"latency_ms_median":statistics.median(all_keys[(a["id"],p,v)]["duration_ms"] for a in rows),"longer_than_1h_pct_window_on_fn":sum(abs(a["signals"]["window_pct"] or 0)>=1 for a in pos)}
summary["owner_historical_baseline"]={}
for symbol in ["BTC","ETH","GRAM","SOL"]:
    group=[x for x in longaudit if x["signals"]["symbol"]==symbol and x["owner"]!="ambiguous"]
    c=collections.Counter("TP" if x["owner"]=="alert" and x["observed_should_alert"] else "FP" if x["owner"]=="no_alert" and x["observed_should_alert"] else "FN" if x["owner"]=="alert" else "TN" for x in group)
    summary["owner_historical_baseline"][symbol]={k:c[k] for k in ("TP","FP","FN","TN")}
(HERE/"evidence_summary.json").write_text(json.dumps(summary,indent=2),encoding="utf-8")
print(json.dumps({"verification":"PASS","coverage":summary["coverage"],"scores":scores,"pilot_groups":summary["pilot_groups"],"owner_historical_baseline":summary["owner_historical_baseline"]},indent=2))
