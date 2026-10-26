"""Convert two completed independent reviewer CSV sets to PR1 benchmark labels.

Never populates judgments itself. All 200 warrants and 72 message reviews must be
provided by real humans. Reconciliation requires an explicit human decision.
"""
import csv, json, sys
from collections import defaultdict
from pathlib import Path
HERE=Path(__file__).resolve().parent

def rows(path):
    with path.open("r",encoding="utf-8-sig",newline="") as f:
        return list(csv.DictReader(f))

def validate_phase(input_rows,expected_ids,name):
    ids=[r.get("case_id","") for r in input_rows]
    if len(ids)!=len(set(ids)) or set(ids)!=set(expected_ids):
        raise ValueError(name+": missing, altered or duplicate case IDs")
    return {r["case_id"]:r for r in input_rows}

def normalize_yes_no(value,field,case_id):
    v=str(value or "").strip().lower()
    if v not in {"yes","no"}:
        raise ValueError("Missing "+field+" for "+case_id)
    return v=="yes"

def labels_for(reviewer,manifest):
    cases=manifest["cases"]
    all_ids={c["id"] for c in cases}
    message_ids={c["id"] for c in cases if c.get("observed",{}).get("final_message")}
    first=validate_phase(rows(HERE/("reviewer_"+reviewer+"_phase1_significance.csv")),
                         all_ids,"phase1/"+reviewer)
    second=validate_phase(rows(HERE/("reviewer_"+reviewer+"_phase2_final_message.csv")),
                          message_ids,"phase2/"+reviewer)
    out=[]
    for c in cases:
        case_id=c["id"]
        warrant=str(first[case_id].get("warrant (alert/no_alert/ambiguous)","")).strip().lower()
        if warrant not in {"alert","no_alert","ambiguous"}:
            raise ValueError("Missing phase-1 human verdict for "+case_id+" reviewer "+reviewer)
        label={"id":case_id,"warrant":warrant,"useful":None,"factual":None}
        if case_id in message_ids:
            for key in ("useful","factual"):
                label[key]=normalize_yes_no(
                   second[case_id].get(key+" (yes/no)"),key,case_id)
        out.append(label)
    return {"dataset_sha256":manifest["dataset_sha256"],
            "evaluator_id":"human_owner" if reviewer=="A" else "human_friend",
            "labels":out}

def score_disagreements(first,second,manifest):
    a={x["id"]:x for x in first["labels"]}
    b={x["id"]:x for x in second["labels"]}
    pending=[]
    for c in manifest["cases"]:
        ident=c["id"]
        for key in ("warrant","useful","factual"):
            if a[ident][key]!=b[ident][key]:
                pending.append({"case_id":ident,"field":key,
                                "reviewer_A":a[ident][key],
                                "reviewer_B":b[ident][key],
                                "human_resolution":""})
    if pending:
        with (HERE/"human_disagreements_to_reconcile.csv").open(
                "w",encoding="utf-8-sig",newline="") as f:
            writer=csv.DictWriter(f,fieldnames=list(pending[0]))
            writer.writeheader();writer.writerows(pending)
    print("DISAGREEMENTS="+str(len(pending)))
    if not pending:
        print("NO_ADJUDICATION_NEEDED")
    return pending

def finalize_reconciled(manifest,first,second):
    path=HERE/"human_disagreements_to_reconcile.csv"
    if not path.exists():
        print("No disagreement file yet")
        return
    decisions=rows(path)
    allowed={"warrant":{"alert","no_alert","ambiguous"},
             "useful":{"yes","no"},"factual":{"yes","no"}}
    by_id=defaultdict(dict)
    for row in decisions:
        case_id=row["case_id"];field=row["field"]
        v=str(row.get("human_resolution","")).strip().lower()
        if v not in allowed[field]:
            raise ValueError("Disagreement unresolved: "+case_id+"/"+field)
        by_id[case_id][field] = (v=="yes" if field!="warrant" else v)
    fst={x["id"]:x for x in first["labels"]}
    for case_id,parts in by_id.items():
        base=fst[case_id]
        by_id[case_id]={"id":case_id, "warrant":parts.get("warrant",base["warrant"]),
                        "useful":parts.get("useful"),"factual":parts.get("factual")}
    doc={"dataset_sha256":manifest["dataset_sha256"],
         "evaluator_id":"human_reconciliation",
         "labels":list(by_id.values())}
    (HERE/"human_reconciled.json").write_text(json.dumps(doc,indent=2)+"\n",encoding="utf-8")
    print("RECONCILIATION_JSON=CREATED")

def main():
    m=json.loads((HERE/"v2_private_sanitized.json").read_text(encoding="utf-8"))
    if len(m["cases"])!=200:raise ValueError("Wrong dataset version")
    mode=(sys.argv[1] if len(sys.argv)>1 else "convert")
    if mode not in {"convert","finalize"}:raise ValueError("Use convert or finalize")
    a=labels_for("A",m);b=labels_for("B",m)
    if mode=="convert":
        for reviewer,doc in (("A",a),("B",b)):
            (HERE/("human_"+reviewer+"_review.json")).write_text(
                json.dumps(doc,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
        score_disagreements(a,b,m)
        print("BOTH_HUMAN_REVIEWS=VALID")
    else:finalize_reconciled(m,a,b)
if __name__=="__main__":
    main()
