import json,pathlib,collections
base=pathlib.Path(r"D:\Projects\CCWBot\reports\event-alert-review-20261016")
pilot=json.loads((base/"ccw16_private/pilot-manifest.json").read_text())
cases=json.loads((base/"v2_private_sanitized.json").read_text())["cases"]
byid={c["id"]:c for c in cases}
selected={c["id"] for c in pilot["cases"]}
owners=json.loads((base/"ccw41_private/owner_reference_candidate_v1_20261022.json").read_text())
truth={c["id"]:c["final"] for c in owners["case_labels"]}
ledger=json.loads((base/"ccw29_private/cloudflare-ledger_PRIVATE.json").read_text())
P=collections.defaultdict(dict)
for r in ledger["attempts"]:
 if r["status"]=="valid":P[r["id"]][r["prompt"]]=r["decision"]["should_alert"]
assert len(P)==20
for key in ("e1","e2"):
 print("PROMPT",key)
 for cid in selected:
  t=truth[cid]
  b=P[cid]["production"];n=P[cid][key]
  if n==b:continue
  m=byid[cid]["input"]["market"]
  recent=byid[cid]["input"].get("recent_event_counts") or {}
  prev=byid[cid]["input"].get("previous_event_alert") or {}
  print("CHANGE",cid,"owner",t,"prod",b,"new",n,
    "symbol",byid[cid]["symbol"],"window_pct",round(float(m["chg_window_percent"]),3),
    "min",m["analysed_window_minutes"],"oneh",m.get("chg1h_percent"),
    "24h",m.get("chg24h_percent"),"prev_age",prev.get("age_minutes"),
    "recent6",recent.get("h6"),
    "since_msg",m.get("chg_since_msg_percent"))
