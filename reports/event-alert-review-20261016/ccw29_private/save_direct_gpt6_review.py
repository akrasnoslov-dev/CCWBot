"""CCW-29 direct model adjudication. Nonblinded exploratory, NOT a human reference."""
import collections,hashlib,json,pathlib,datetime
F=pathlib.Path(r"D:\Projects\CCWBot\reports\event-alert-review-20261016\ccw29_private\fresh200_unseen")
cases=json.loads((F/"fresh200_source_SEALED_PRIVATE.json").read_text(encoding="utf-8"))
led=json.loads((F/"openai-luna-fresh200-ledger_PRIVATE.json").read_text(encoding="utf-8"))
assert cases["dataset_sha256"]==led["dataset_sha256"]=="ad06de5fac921c8d0db46f9ab086bed470733df62670bcda5c96d0479c837f7d"
outputs=collections.defaultdict(dict)
for r in led["attempts"]:
 if r["status"]=="valid":outputs[r["id"]][r["prompt"]]=r["decision"]["should_alert"]
assert len(outputs)==200 and all(len(o)==3 for o in outputs.values())
def high_risk(c):
 m=c["input"]["market"]
 return any(outputs[c["id"]].values()) or abs(m["chg_window_percent"])>=1.5
risks=sorted([c for c in cases["cases"] if high_risk(c)],key=lambda x:(x["symbol"],x["source_utc"][5:16],x["id"][:9]))
assert len(risks)==55
# A = alert, N = no_alert, ? = ambiguous; assigned by direct GPT-6 review
# of the actual chronological snapshot prices and notification context.
marks=[
 "?","A","N","?","A","A","?","N","A",
 "?","N","A","?","?","N","N","A","?","A","A","N","A","N",
 "A","?","A","A","N","N","N","A","N","N","N","A","?","N",
 "A","N","A","A","A","?","A","N","?","N","A","?","?","N","A","A","A","N"
]
assert len(marks)==55
strong={c["id"]:{"warrant":{"A":"alert","N":"no_alert","?":"ambiguous"}[mk],"packet":"full_snapshot","review_index":i} for i,(c,mk) in enumerate(zip(risks,marks))}
flagged_ambiguities={"ev_c4f80d","ev_929478","ev_7d71da","ev_59528f"}
rows=[]
for c in cases["cases"]:
 id=c["id"];o=strong.get(id)
 if o is None:
  val="ambiguous" if id[:9] in flagged_ambiguities else "no_alert"
  o={"warrant":val,"packet":"compact_all-snapshots_pct_and-context","review_index":None}
 rows.append({"id":id,"input_sha256":c["input_sha256"],"symbol":c["symbol"],"warrant":o["warrant"],
  "evidence_packet":o["packet"],"risk_review_index":o["review_index"]})
assert len(rows)==200 and len({r["id"] for r in rows})==200
doc={"dataset_sha256":cases["dataset_sha256"],"reviewer":"GPT-6_direct_model_reasoned_pass",
 "authority":"AI_SELF_REVIEW_NOT_HUMAN_NOT_BLIND",
 "label_status":"PROVISIONAL_DIAGNOSTIC_ONLY","reliability":"subjective_judgment_not_authoritative_human_reference",
 "selection":"55 highest-risk full-snapshot cases, 145 agreement-negative compact cases; no hard numeric significance thresholds",
 "repeated_episode_limitation":"Frozen replay uses original production last_msg even when candidate would have altered prior alerts",
 "case_labels":rows}
(F/"gpt6_direct_review_200_PROVISIONAL_PRIVATE.json").write_text(json.dumps(doc,indent=2)+"\n",encoding="utf-8")
truth={r["id"]:r["warrant"] for r in rows}
def calc(prompt,subset=None):
 c=collections.Counter()
 for row in rows:
  id=row["id"]
  if subset=="55" and id not in strong:continue
  if subset=="145" and id in strong:continue
  t=truth[id]
  if t=="ambiguous":c["ambiguous"]+=1;continue
  x=outputs[id][prompt];yes=t=="alert"
  c["TP" if yes and x else "FP" if x else "FN" if yes else "TN"]+=1
 tp,fp,fn,tn=(c[x] for x in ("TP","FP","FN","TN"))
 return {**{x:c[x] for x in ("TP","FP","FN","TN","ambiguous")},
  "precision_provisional":round(tp/(tp+fp),3) if tp+fp else None,
  "recall_provisional":round(tp/(tp+fn),3) if tp+fn else None,
  "accuracy_provisional":round((tp+tn)/(tp+fp+fn+tn),3) if tp+fp+fn+tn else None}
results={"source_dataset_sha256":cases["dataset_sha256"],"authority":doc["authority"],
 "model_adjudicated_counts":dict(collections.Counter(truth.values())),
 "source_risk_selected":55,"quality_claim":"exploratory paired comparison only; posthoc not independent",
 "all_200":{p:calc(p) for p in ("production","balanced","refined")},
 "high_risk_55":{p:calc(p,"55") for p in ("production","balanced","refined")},
 "agreement_negative_145":{p:calc(p,"145") for p in ("production","balanced","refined")}}
(F/"gpt6_direct_review_metrics_PROVISIONAL_PRIVATE.json").write_text(json.dumps(results,indent=2)+"\n",encoding="utf-8")
print(json.dumps(results,indent=2))
