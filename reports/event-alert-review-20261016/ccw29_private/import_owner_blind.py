"""Safely import a full independently blinded owner holdout review; immutable private write."""
from __future__ import annotations
import argparse,hashlib,json,pathlib,collections,re
F=pathlib.Path(r"D:\Projects\CCWBot\reports\event-alert-review-20261016\ccw29_private\fresh_holdout")
def main():
 ap=argparse.ArgumentParser()
 ap.add_argument("input",help="JSON exported by CCW29_OWNER_BLIND_REVIEW.html")
 args=ap.parse_args()
 path=pathlib.Path(args.input)
 original=(F/"holdout_20_blind_packet_PRIVATE.json")
 packet=json.loads(original.read_text(encoding="utf-8"))
 allowed={x["id"]:x["input_sha256"] for x in packet["cases"]}
 data=json.loads(path.read_text(encoding="utf-8"))
 assert data.get("dataset_sha256")==packet["dataset_sha256"],"Dataset mismatch"
 assert data.get("reviewer_id")=="independent_owner_review","Expected independent owner review form"
 rows=data.get("labels")
 assert isinstance(rows,list) and len(rows)==len(allowed)==20,"Complete 20-case review required"
 clean=[];ids=set()
 for r in rows:
  assert isinstance(r,dict) and set(r)=={"id","input_sha256","warrant","rationale"},"Malformed label"
  k=r["id"]
  assert k not in ids and allowed.get(k)==r["input_sha256"],"Unknown/duplicate/changed case"
  assert r["warrant"] in ("alert","no_alert","ambiguous"),"Invalid label or unanswered case"
  note=r["rationale"]
  assert isinstance(note,str) and 8<=len(note.strip())<=1200,"Meaningful concise rationale required"
  assert not re.search(r"(?i)(api[_-]?key|token=|password=|t[.]me/|https?://)",note),"Private info in reason"
  ids.add(k);clean.append(r)
 assert ids==set(allowed)
 dest=F/"owner_blind_review_SEALED_PRIVATE.json"
 assert not dest.exists(),"An owner review already exists; do not silently overwrite"
 serialized=json.dumps({"schema_version":1,"dataset_sha256":packet["dataset_sha256"],
      "reviewer_id":"independent_owner_review","source_file_sha256":hashlib.sha256(path.read_bytes()).hexdigest(),
      "labels":clean},ensure_ascii=False,indent=2)+"\n"
 dest.write_text(serialized,encoding="utf-8")
 print(json.dumps({"status":"OWNER_REVIEW_IMPORTED_AND_SEALED","source":str(path),"count":len(clean),
 "labels":dict(collections.Counter(r["warrant"] for r in clean)),
 "sealed_sha256":hashlib.sha256(dest.read_bytes()).hexdigest()}))
if __name__=="__main__":main()
