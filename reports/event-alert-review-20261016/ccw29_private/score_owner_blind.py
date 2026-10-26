"""CCW-29 post-owner-review scorer. Never treat current GPT-6 provisional labels as independent reference."""
from __future__ import annotations
import json,pathlib,collections
F=pathlib.Path(r"D:\Projects\CCWBot\reports\event-alert-review-20261016\ccw29_private\fresh_holdout")
blind=json.loads((F/"holdout_20_blind_packet_PRIVATE.json").read_text(encoding="utf-8"))
review_path=F/"owner_blind_review_SEALED_PRIVATE.json"
if not review_path.exists():raise RuntimeError("Independent owner's sealed blind-label JSON not yet imported")
labels=json.loads(review_path.read_text(encoding="utf-8"))
assert labels["dataset_sha256"]==blind["dataset_sha256"]
by_id={r["id"]:r["warrant"] for r in labels["labels"]}
assert len(by_id)==20 and set(by_id)=={c["id"] for c in blind["cases"]}
comp=json.loads((F/"fresh_holdout_predictions_PRIVATE.json").read_text(encoding="utf-8"))
assert comp["dataset_sha256"]==blind["dataset_sha256"]
output={"status":"INDEPENDENT_OWNER_REVIEW_SCORED_NOT_AUTO_APPROVED","dataset_sha256":blind["dataset_sha256"],
        "label_counts":dict(collections.Counter(by_id.values())),"providers":{}}
for provider in ("groq","cloudflare"):
 output["providers"][provider]={}
 for prompt in ("e1","e2"):
  rows={r["case_id"]:r for r in comp["matches"] if r["provider"]==provider and r["prompt"]==prompt}
  counts=collections.Counter()
  for id,truth in by_id.items():
   if id not in rows:counts["unmeasured"]+=1;continue
   if truth=="ambiguous":counts["ambiguous"]+=1;continue
   pred=rows[id]["decision"]["should_alert"]
   counts["TP" if truth=="alert" and pred else "FP" if truth=="no_alert" and pred else "FN" if truth=="alert" else "TN"]+=1
  tp,fp,fn=counts["TP"],counts["FP"],counts["FN"]
  output["providers"][provider][prompt]={
      **{k:counts[k] for k in ("TP","FP","FN","TN","ambiguous","unmeasured")},
      "precision":round(tp/(tp+fp),4) if tp+fp else None,"recall":round(tp/(tp+fn),4) if tp+fn else None}
(F/"owner_evaluated_metrics_PRIVATE.json").write_text(json.dumps(output,indent=2)+"\n",encoding="utf-8")
print(json.dumps(output,indent=2))
