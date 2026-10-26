"""CCW-29: score independent AI reviewers only on consensus; never call it human truth."""
import collections,hashlib,io,json,pathlib,subprocess,sys,tarfile
B=pathlib.Path(r"D:\Projects\CCWBot\reports\event-alert-review-20261016\ccw29_private")
F=B/"fresh200_unseen"
DS="ad06de5fac921c8d0db46f9ab086bed470733df62670bcda5c96d0479c837f7d"
f=json.loads((F/"fresh200_blind_packet_PRIVATE.json").read_text(encoding="utf8"))
assert f["dataset_sha256"]==DS and len(f["cases"])==200
cases={c["id"]:c for c in f["cases"]}
remote="/home/ccwbot_ops/ccw29_review_fresh200"
ssh=["ssh","-o","BatchMode=yes","-o","ConnectTimeout=8","ccwbot-prod-ops"]
cmd=f"cd {remote}; tar -cf - "+ " ".join(m+"-"+str(s)+"-ledger.json" for m in ("llama","qwen") for s in range(4))
p=subprocess.run(ssh+[cmd],capture_output=True,timeout=35)
assert p.returncode==0,"Review ledgers not complete or absent"
by_model={m:{} for m in ("llama","qwen")}
status={}
with tarfile.open(fileobj=io.BytesIO(p.stdout),mode="r:") as tf:
 for entry in tf:
  source=entry.name
  model,shard=source.split("-")[0:2]
  data=tf.extractfile(entry).read()
  doc=json.loads(data)
  assert doc["dataset_sha256"]==DS and doc["reviewer"]==model and int(shard)==doc["shard"] if "shard" in doc else doc["model"].startswith("@cf/")
  (F/(model+"-"+shard+"-blind_ledger_PRIVATE.json")).write_bytes(data)
  status[model+"-"+shard]=dict(collections.Counter(r["status"] for r in doc["attempts"]))
  for r in doc["attempts"]:
   assert r["id"] in cases and r["input_sha256"]==cases[r["id"]]["input_sha256"]
   if r["status"]!="valid":continue
   assert r["id"] not in by_model[model]
   val=r["decision"]
   assert val["warrant"] in ("alert","no_alert","ambiguous")
   by_model[model][r["id"]]=val
paired={};cnt=collections.Counter();queue=[]
for id,c in cases.items():
 a=by_model["llama"].get(id);b=by_model["qwen"].get(id)
 if not a or not b:cnt["missing"]+=1;continue
 if a["warrant"]!=b["warrant"]:
  cnt["disagreement"]+=1;queue.append({"id":id,"symbol":c["symbol"],"a":a,"b":b});continue
 if a["warrant"]=="ambiguous":
  cnt["both_ambiguous"]+=1;queue.append({"id":id,"symbol":c["symbol"],"a":a,"b":b});continue
 paired[id]=a["warrant"]
 cnt["agreed_"+a["warrant"]]+=1
lad=json.loads((F/"openai-luna-fresh200-ledger_PRIVATE.json").read_text(encoding="utf8"))
assert lad["model"]=="gpt-6-luna" and lad["dataset_sha256"]==DS
candidates={m:{} for m in ("production","balanced","refined")}
for row in lad["attempts"]:
 if row["status"]!="valid":continue
 assert row["id"] in cases and row["input_sha256"]==cases[row["id"]]["input_sha256"]
 candidates[row["prompt"]][row["id"]]=row["decision"]["should_alert"]
def metrics(scores):
 o=collections.Counter()
 for id,truth in paired.items():
  if id not in scores:o["missing"]+=1;continue
  yes=scores[id]
  o["TP" if truth=="alert" and yes else "FP" if truth=="no_alert" and yes else "FN" if truth=="alert" else "TN"]+=1
 tp,fp,fn,tn=(o[k] for k in ("TP","FP","FN","TN"))
 return {**{k:o[k] for k in ("TP","FP","FN","TN","missing")},"precision_provisional":round(tp/(tp+fp),4) if tp+fp else None,
 "recall_provisional":round(tp/(tp+fn),4) if tp+fn else None,
 "accuracy_provisional":round((tp+tn)/(tp+fp+fn+tn),4) if tp+fp+fn+tn else None}
result={"dataset_sha256":DS,"reviewer_type":"TWO_DISTINCT_AI_MODELS_NOT_INDEPENDENT_HUMANS",
 "human_labels":False,"matched_cases":len(paired),"reviewer_valid":{m:len(v) for m,v in by_model.items()},
 "agreement_counts":dict(cnt),"status_counts":status,
 "candidate_scores_ai_consensus_only":{m:metrics(v) for m,v in candidates.items()},
 "disagreement_queue_count":len(queue)}
(F/"ai_review_consensus_scores_PRIVATE.json").write_text(json.dumps(result,indent=2)+"\n",encoding="utf8")
(F/"ai_review_disagreement_queue_PRIVATE.json").write_text(json.dumps({"dataset_sha256":DS,"queue":queue},indent=2)+"\n",encoding="utf8")
print(json.dumps({k:v for k,v in result.items() if k!="status_counts"},indent=2))
