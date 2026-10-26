"""CCW-29: print private market-only evidence for 19 v3-disabled events; no user data."""
import json,pathlib,collections
ROOT=pathlib.Path(r"D:\Projects\CCWBot\reports\event-alert-review-20261016\ccw29_private\fresh200_unseen")
source=json.loads((ROOT/"fresh200_source_SEALED_PRIVATE.json").read_text(encoding="utf8"))
comp=json.loads((ROOT/"v3_luna_comparison_PRIVATE.json").read_text(encoding="utf8"))
old=json.loads((ROOT/"openai-luna-fresh200-ledger_PRIVATE.json").read_text(encoding="utf8"))
new=json.loads((ROOT/"openai-luna-v3-ledger_PRIVATE.json").read_text(encoding="utf8"))
cs={c["id"]:c for c in source["cases"]}
votes=collections.defaultdict(dict)
for entry in old["attempts"]+new["attempts"]:
 if entry["status"]=="valid": votes[entry["id"]][entry["prompt"]]=entry["decision"]
for n,x in enumerate(comp["v3_vs_refined"]["disagreement_details"],1):
 if x["to_v3"]:continue
 c=cs[x["id"]]; f=c["input"];m=f["market"]
 item={"number":n,"id":c["id"],"symbol":c["symbol"],"UTC":c["source_utc"],
 "market":m, "last_msg":f.get("last_msg"),"previous_event_alert":f.get("previous_event_alert"),
 "recent_event_counts":f.get("recent_event_counts"),
 "news":f.get("news"), "policy":f.get("policy"),
 "decision_v2":votes[c["id"]]["refined"],"decision_v3":votes[c["id"]]["v3"]}
 print("CASE_START",n,flush=True)
 print(json.dumps(item,ensure_ascii=False,separators=(",",":")),flush=True)
 print("CASE_END",n,flush=True)
