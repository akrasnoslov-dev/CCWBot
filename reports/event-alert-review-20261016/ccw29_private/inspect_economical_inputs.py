"""Read-only characterization of frozen source and prior enriched CCW-44 inputs."""
import json, pathlib, subprocess, collections, statistics
base=pathlib.Path(r"D:\Projects\CCWBot\reports\event-alert-review-20261016\ccw29_private")
s=json.loads((base/"fresh200_unseen/fresh200_source_SEALED_PRIVATE.json").read_text(encoding="utf8"))
q=json.loads((base/"quality_first_200/quality_first_results_PRIVATE.json").read_text(encoding="utf8"))
print("SOURCE_CASES",len(s["cases"]),"SHA",s["dataset_sha256"])
for c in s["cases"][:2]:
 i=c["input"]
 print("SOURCE_EXAMPLE",json.dumps({"id":c["id"],"symbol":c["symbol"],"keys":list(i),"market":i["market"],"last_msg":i.get("last_msg"),"previous_alert":i.get("previous_event_alert"),"recent_counts":i.get("recent_event_counts"),"news":i.get("news")},ensure_ascii=False)[:4000])
print("PREVIOUS_METRICS",json.dumps({k:q.get(k) for k in ("cost_upper_usd","quality_first_positive","avg_input_tokens","avg_completion_tokens_including_reasoning","matched_changes")}))
r=subprocess.run(["ssh","-o","BatchMode=yes","-o","ConnectTimeout=8","ccwbot-prod-ops","cat /home/ccwbot_ops/ccw44_quality_first_200/jobs.json"],capture_output=True,timeout=50)
if r.returncode!=0:
 print("REMOTE_NOT_ACCESSIBLE",r.returncode,r.stderr.decode(errors="replace")[:300]);raise SystemExit
d=json.loads(r.stdout)
jobs=d["jobs"]
print("REMOTE_JOB_COUNT",len(jobs),"REMOTE_MANIFEST",d["manifest"])
sizes=[]
for j in jobs:
 prompt,payload=j["body"]["messages"][1]["content"].split("\n\nEVIDENCE JSON:\n",1)
 obj=json.loads(payload)
 sizes.append(len(payload.encode("utf8")))
 if len(sizes)<=2:print("REMOTE_EXAMPLE",json.dumps(obj,ensure_ascii=False)[:9000])
 printfields=None
print("REMOTE_PAYLOAD_SIZES",min(sizes),round(statistics.mean(sizes)),max(sizes))
