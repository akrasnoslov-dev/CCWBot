"""Detailed nonsecret error audit for 200 frozen historical events on Luna."""
import collections,json,pathlib,math
base=pathlib.Path(r"D:\Projects\CCWBot\reports\event-alert-review-20261016")
cases=json.loads((base/"v2_private_sanitized.json").read_text(encoding="utf8"))["cases"]
truth={r["id"]:r["final"] for r in json.loads((base/"ccw41_private/owner_reference_candidate_v1_20261022.json").read_text(encoding="utf8"))["case_labels"]}
rows=json.loads((base/"ccw29_private/full_200_v2/openai-luna-ledger_PRIVATE.json").read_text(encoding="utf8"))["attempts"]
pred=collections.defaultdict(dict)
for r in rows:
 if r["status"]=="valid":pred[r["id"]][r["prompt"]]=r["decision"]
def feat(c,p):
 m=c["input"]["market"];recent=c["input"].get("recent_event_counts") or {};prev=c["input"].get("previous_event_alert") or {}
 return dict(id=c["id"],symbol=c["symbol"],case_day=c["source_utc"][:10],truth=truth[c["id"]],
   prod=c["observed"]["should_alert"],balanced=p["balanced"]["should_alert"],leg=p["fresh_leg"]["should_alert"],
   reason=p["balanced"]["reason_code"],materiality=p["balanced"]["materiality"],novelty=p["balanced"]["novelty"],
   window=round(m["chg_window_percent"],3),p24=round(m["chg24h_percent"],3) if m.get("chg24h_percent") is not None else None,
   since=round(m["chg_since_msg_percent"],3) if m.get("chg_since_msg_percent") is not None else None,
   p30=round(m["relative_window_percentile_30d"],1) if isinstance(m.get("relative_window_percentile_30d"),(int,float)) else None,
   prev_age=prev.get("age_minutes"),recent6=recent.get("h6"),news=bool(c["input"].get("news")))
problem=[]
for c in cases:
 t=truth[c["id"]]
 if t=="ambiguous":continue
 p=pred[c["id"]];a=p["balanced"]["should_alert"]
 if (t=="alert")!=a:problem.append(feat(c,p))
print("ERRORS_11")
for x in problem:print(json.dumps(x))
print("BY_SYMBOL",dict(collections.Counter(x["symbol"]+"/"+("FN" if x["truth"]=="alert" else "FP") for x in problem)))
print("OPINION_OWNER_DISTRIBUTION",dict(collections.Counter(truth.values())))
