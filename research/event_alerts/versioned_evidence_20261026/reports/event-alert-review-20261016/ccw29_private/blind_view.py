"""Summarize sealed CCW29 blind packet only; never expose bot or provider decisions."""
import json,pathlib
p=pathlib.Path(r"D:\Projects\CCWBot\reports\event-alert-review-20261016\ccw29_private\fresh_holdout\holdout_20_blind_packet_PRIVATE.json")
doc=json.loads(p.read_text(encoding="utf-8"))
print("BLIND_PACKET",doc["dataset_sha256"],"COUNT",len(doc["cases"]))
for n,c in enumerate(doc["cases"],1):
 f=c["input"];m=f["market"];snap=m.get("snapshots") or []
 src={
 "id":c["id"],"coin":c["symbol"],"time":f.get("timestamp_utc"),
 "market":{key:m.get(key) for key in ("price","chg_window_percent","analysed_window_minutes","chg30m_percent","chg1h_percent","chg24h_percent","relative_window_percentile_30d","chg_since_msg_percent")},
 "snapshots":snap[-16:],"last_msg":f.get("last_msg"),"previous_event_alert":f.get("previous_event_alert"),"recent_event_counts":f.get("recent_event_counts"),"news":f.get("news"),"policy":f.get("policy")}
 print(n,json.dumps(src,ensure_ascii=False,separators=(",",":")))
