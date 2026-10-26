"""CCW-45 offline diagnostic; prints only privacy-safe event summaries, no provider requests."""
from __future__ import annotations
import collections,json,pathlib,datetime
B=pathlib.Path(r"D:\Projects\CCWBot\reports\event-alert-review-20261016\ccw29_private")
F=B/"fresh200_unseen";E=B/"economical_200"
data=json.loads((F/"fresh200_source_SEALED_PRIVATE.json").read_text(encoding="utf8"))
source={c["id"]:c for c in data["cases"]}
ledger=json.loads((E/"economical_luna_ledger_PRIVATE.json").read_text(encoding="utf8"))
dec={x["id"]:x["decision"] for x in ledger["attempts"] if x["status"]=="valid"}
ref=json.loads((F/"gpt6_direct_review_200_PROVISIONAL_PRIVATE.json").read_text(encoding="utf8"))
labels={x["id"]:x["warrant"] for x in ref["case_labels"]}
print("STATUS",len(dec),"LABELS",collections.Counter(labels.values()))
for sym in ("BTC","ETH","GRAM","SOL"):
 subs=[i for i,c in source.items() if c["symbol"]==sym]
 print("SYM",sym,"alerts",sum(dec[i]["should_alert"] for i in subs),
 "positive_decisions",collections.Counter((labels[i],dec[i]["should_alert"]) for i in subs))
for category in ("FN","FP","AMBIGUOUS_POS"):
 rows=[]
 for i,d in dec.items():
  label=labels[i]
  hit=(category=="FN" and label=="alert" and not d["should_alert"]) or (category=="FP" and label=="no_alert" and d["should_alert"]) or (category=="AMBIGUOUS_POS" and label=="ambiguous" and d["should_alert"])
  if not hit:continue
  case=source[i]; market=case["input"]["market"];prev=case["input"].get("previous_event_alert") or {}
  rows.append({"id":i,"symbol":case["symbol"],"timestamp":case["input"]["timestamp_utc"][:16],
   "nominal_window_source_pct":round(market.get("chg_window_percent",0),3),
   "24h_pct":round(market.get("chg24h_percent",0),3),
   "last30m_pct":round(market["chg30m_percent"],3) if market.get("chg30m_percent") is not None else None,
   "historical_window_pctile":market.get("relative_window_percentile_30d"),
   "previous_event_m":prev.get("age_minutes"),
   "prior_move_pct":prev.get("analysed_window_move"),
   "reason":d["reason_code"],"confidence":d["confidence"]})
 print(category,"N=",len(rows))
 print(json.dumps(rows[:26],ensure_ascii=False,separators=(",",":")))
for kind,path in [
 ("production",F/"openai-luna-fresh200-ledger_PRIVATE.json"),
 ("balanced",F/"openai-luna-fresh200-ledger_PRIVATE.json"),
 ("refined",F/"openai-luna-fresh200-ledger_PRIVATE.json"),
 ("v3",F/"openai-luna-v3-ledger_PRIVATE.json"),
 ("quality_first",B/"quality_first_200/quality_first_luna_ledger_PRIVATE.json"),
 ("economical",E/"economical_luna_ledger_PRIVATE.json")]:
 l=json.loads(path.read_text(encoding="utf8"))
 sub=[x for x in l["attempts"] if x["prompt"]==kind]
 cost=sum(x.get("estimated_charged_usd",0) for x in sub)
 inp=sum(x.get("prompt_tokens") or 0 for x in sub)
 out=sum(x.get("completion_tokens") or 0 for x in sub)
 print("COST",kind,{"requests":len(sub),"valid":sum(x["status"]=="valid" for x in sub),"input":inp,"output":out,"cost":round(cost,6),"mean_in":round(inp/len(sub),1) if sub else None,"mean_out":round(out/len(sub),1) if sub else None})
