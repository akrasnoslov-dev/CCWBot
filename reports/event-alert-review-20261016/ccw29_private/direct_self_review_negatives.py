"""Direct GPT-6 review of 145 cases where three Luna prompts all reject."""
import collections,json,pathlib,sys,math
F=pathlib.Path(r"D:\Projects\CCWBot\reports\event-alert-review-20261016\ccw29_private\fresh200_unseen")
s=json.loads((F/"fresh200_source_SEALED_PRIVATE.json").read_text(encoding="utf-8"))
l=json.loads((F/"openai-luna-fresh200-ledger_PRIVATE.json").read_text(encoding="utf-8"))
v=collections.defaultdict(dict)
for r in l["attempts"]:
 if r["status"]=="valid":v[r["id"]][r["prompt"]]=r["decision"]["should_alert"]
rows=[]
for c in s["cases"]:
 q=v[c["id"]]
 if any(q.values()):continue
 f=c["input"];m=f["market"];pr=f.get("previous_event_alert") or {};counts=f.get("recent_event_counts") or {}
 prices=[x.get("p") for x in m.get("snapshots",[]) if isinstance(x,dict)]
 rel=[round(100*(p/prices[1]-1),2) for p in prices] if len(prices)==6 and isinstance(prices[1],(int,float)) else []
 def r(k):
  a=m.get(k);return round(a,2) if isinstance(a,(int,float)) else None
 rows.append({"id":c["id"][:9],"sym":c["symbol"],"day":c["source_utc"][5:16],
  "w":r("chg_window_percent"),"m30":r("chg30m_percent"),"h1":r("chg1h_percent"),"d24":r("chg24h_percent"),
  "since":r("chg_since_msg_percent"),"pct":r("relative_window_percentile_30d"),"age":pr.get("age_minutes"),"cnt":counts.get("h6"),
  "series_from_3h_pct":rel,"news":len(f.get("news") or [])})
rows.sort(key=lambda r:(r["sym"],r["day"],r["id"]))
print("CONCORDANT_NEGATIVES",len(rows), "PER_COIN",dict(collections.Counter(x["sym"] for x in rows)))
part=int(sys.argv[1]) if len(sys.argv)>1 else 1
for i,x in enumerate(rows[(part-1)*50:part*50],start=(part-1)*50):
 print("%03d "%i+json.dumps(x,separators=(",",":")))
