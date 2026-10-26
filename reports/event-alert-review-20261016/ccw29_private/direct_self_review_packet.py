"""CCW-29 direct reasoned audit packet, no external calls or artificial labels."""
import collections,json,pathlib,sys,math
F=pathlib.Path(r"D:\Projects\CCWBot\reports\event-alert-review-20261016\ccw29_private\fresh200_unseen")
source=json.loads((F/"fresh200_source_SEALED_PRIVATE.json").read_text(encoding="utf-8"))
replay=json.loads((F/"openai-luna-fresh200-ledger_PRIVATE.json").read_text(encoding="utf-8"))
assert source["dataset_sha256"]==replay["dataset_sha256"]=="ad06de5fac921c8d0db46f9ab086bed470733df62670bcda5c96d0479c837f7d"
votes=collections.defaultdict(dict)
for r in replay["attempts"]:
 if r["status"]=="valid":votes[r["id"]][r["prompt"]]=r["decision"]
assert len(votes)==200
rows=[]
for c in source["cases"]:
 v=votes[c["id"]];f=c["input"];m=f["market"];pr=f.get("previous_event_alert") or {};recent=f.get("recent_event_counts") or {}
 pred="".join("Y" if v[name]["should_alert"] else "-" for name in ("production","balanced","refined"))
 def ff(k):
  val=m.get(k);return (round(val,2) if isinstance(val,(int,float)) else None)
 snaps=m.get("snapshots") or []
 sn=[]
 for q in snaps:
  if isinstance(q,dict):
   sn.append((q.get("m"),q.get("p")))
  else:sn.append(str(q)[:70])
 news=f.get("news") or []
 heads=[(n.get("title") or n.get("headline") or "")[:90] for n in news if isinstance(n,dict)]
 row={"id":c["id"][:9],"sym":c["symbol"],"day":c["source_utc"][5:16],
 "ch3":ff("chg_window_percent"),"ch30":ff("chg30m_percent"),"ch1":ff("chg1h_percent"),"ch24":ff("chg24h_percent"),
 "since":ff("chg_since_msg_percent"),"pctile":ff("relative_window_percentile_30d"),
 "previous_age":pr.get("age_minutes"),"count6":recent.get("h6"),"nnews":len(news),
 "pred_PBR":pred,"prod_old":bool(c["observed"]["should_alert"]),
 "why_B":v["balanced"]["reason_code"],"why_R":v["refined"]["reason_code"],
 "snap":sn,"headlines":heads}
 row["review"]=pred!="---" or (isinstance(m.get("chg_window_percent"),(int,float)) and abs(m["chg_window_percent"])>=1.5)
 rows.append(row)
print("REVIEW_COUNTS",json.dumps({"all":len(rows),"any_positive_or_large_window":sum(x["review"] for x in rows),
 "prediction_sets":dict(collections.Counter(x["pred_PBR"] for x in rows)),
 "per_coin":{s:dict(collections.Counter(x["pred_PBR"] for x in rows if x["sym"]==s)) for s in ("BTC","ETH","GRAM","SOL")}}))
selection=[x for x in rows if x["review"]]
selection.sort(key=lambda x:(x["sym"],x["day"],x["id"]))
part=int(sys.argv[1]) if len(sys.argv)>1 else 1
parts=4
each=(len(selection)+parts-1)//parts
for i,r in enumerate(selection[(part-1)*each:part*each],start=(part-1)*each):
 print("%03d "%i+json.dumps(r,ensure_ascii=False,separators=(",",":")))
