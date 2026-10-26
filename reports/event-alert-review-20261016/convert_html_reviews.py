"""Convert complete HTML human reviews to PR1 pinned independent labels.

Place four downloaded answer JSON files alongside this script:
CCWBot_A_PHASE1_answers.json, CCWBot_A_PHASE2_answers.json,
CCWBot_B_PHASE1_answers.json, CCWBot_B_PHASE2_answers.json.
Strictly rejects missing answers, dataset drift and mixed reviewer files.
"""
import csv, json
from pathlib import Path

ROOT=Path(__file__).resolve().parent
DATA=json.loads((ROOT/"v2_private_sanitized.json").read_text(encoding="utf-8"))
HASH=DATA["dataset_sha256"]
ALL={c["id"] for c in DATA["cases"]}
SENT={c["id"] for c in DATA["cases"] if c.get("observed",{}).get("final_message")}

def review(reviewer,phase):
    filepath=ROOT/f"CCWBot_{reviewer}_PHASE{phase}_answers.json"
    doc=json.loads(filepath.read_text(encoding="utf-8"))
    tag="significance" if phase==1 else "message"
    assert (doc["dataset_sha256"]==HASH and doc["reviewer_id"]==reviewer
            and doc["phase"]==tag),"Reviewer, phase or dataset mismatch"
    expected=ALL if phase==1 else SENT
    answers=doc["answers"]
    by_id={v["id"]:v for v in answers}
    assert len(by_id)==len(answers) and set(by_id)==expected, "Review incomplete or duplicated"
    for item in answers:
        if phase==1:
            assert item["warrant"] in {"alert","no_alert","ambiguous"},"Invalid human verdict"
        else:
            assert type(item.get("useful")) is bool and (item.get("factual") is None or type(item.get("factual")) is bool), "Missing usefulness score or invalid factuality status"
    return by_id

def main():
    all_reviews=[]
    for reviewer in ("A","B"):
        significance=review(reviewer,1)
        messages=review(reviewer,2)
        labels=[]
        for c in DATA["cases"]:
            i=c["id"]; m=messages.get(i,{})
            labels.append({"id":i,"warrant":significance[i]["warrant"],
                           "useful":m.get("useful"),"factual":m.get("factual")})
        doc={"dataset_sha256":HASH,
             "evaluator_id":"human_owner" if reviewer=="A" else "human_friend",
             "labels":labels}
        path=ROOT/f"human_{reviewer}_review.json"
        path.write_text(json.dumps(doc,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
        all_reviews.append(doc)
        print(path.name,"written with",len(labels),"human verdicts")
    first={x["id"]:x for x in all_reviews[0]["labels"]}
    other={x["id"]:x for x in all_reviews[1]["labels"]}
    discrepancies=[]
    for case_id in sorted(ALL):
        for field in ("warrant","useful","factual"):
            if first[case_id][field]!=other[case_id][field]:
                discrepancies.append({"case_id":case_id,"field":field,
                      "A_answer":first[case_id][field],"B_answer":other[case_id][field],
                      "human_resolution":""})
    if discrepancies:
        with (ROOT/"human_disagreements_to_reconcile.csv").open("w",encoding="utf-8-sig",newline="") as f:
            writer=csv.DictWriter(f,fieldnames=list(discrepancies[0]))
            writer.writeheader();writer.writerows(discrepancies)
    print("HUMAN_DISAGREEMENTS",len(discrepancies))
    print("Next: explicitly reconcile disagreements; do not auto-resolve")
if __name__=="__main__":main()
