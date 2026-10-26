"""Converts agreed reviewer reconciliation decisions to PR1 human resolution JSON."""
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parent
data=json.loads((ROOT/"v2_private_sanitized.json").read_text(encoding="utf-8"))
ids={x["id"] for x in json.loads((ROOT/"unresolved_human_disagreements_private.json").read_text(encoding="utf-8"))["conflicts"]}
p=ROOT/"CCWBot_R_PHASE1_answers.json"
doc=json.loads(p.read_text(encoding="utf-8"))
assert doc["dataset_sha256"]==data["dataset_sha256"] and doc["reviewer_id"]=="R" and doc["phase"]=="significance"
labels=doc["answers"]
assert len(labels)==len(ids)==99 and {x["id"] for x in labels}==ids
assert all(x.get("warrant") in {"alert","no_alert","ambiguous"} for x in labels)
result={"dataset_sha256":data["dataset_sha256"],"evaluator_id":"human_joint_adjudication",
        "labels":[{"id":x["id"],"warrant":x["warrant"],"useful":None,"factual":None} for x in labels]}
(ROOT/"human_joint_reconciled_for_pr1.json").write_text(
 json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print("Converted 99 HUMAN disputes, no AI substitution")
