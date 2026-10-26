"""Versioned private calibration reference from owner's 66 A/C re-decisions. Offline."""
import hashlib, json, csv, sys
from collections import Counter
from pathlib import Path
R=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(R.parents[1]))
from scripts.ccw41_reviewer_c_audit import compare_reviewers
from scripts.event_alert_benchmark import load_frozen, _read_evaluations
P=R/"ccw41_private"
D=R/"v2_private_sanitized.json"
A=R/"reviewer_A_significance_for_pr1.json"
B=R/"reviewer_B_significance_for_pr1.json"
C=P/"reviewer_c_sealed.json"
I=P/"owner_ac_66_answers_20261022.compact.json"
O=P/"owner_reference_candidate_v1_20261022"
SHA="ed126380369014e6522cee49009b880cf0350aa7565269d50641c3f1bbdc3bee"
UPLOAD_SHA="aa0f2fb6a1273d9e08f8f63e768fb5e0acac072af233f0cc9bfd62440a64f53f"
W={"alert","no_alert","ambiguous"}
def write(path,obj):
    content=obj if isinstance(obj,str) else json.dumps(obj,ensure_ascii=False,indent=2)+"\n"
    if path.exists() and path.read_text(encoding="utf-8")!=content:
        raise ValueError("Refusing to overwrite changed versioned file: "+str(path))
    if not path.exists():path.write_text(content,encoding="utf-8",newline="\n")
def hashfile(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def metrics(rows,key):
    labels=Counter(x[key] for x in rows)
    scores=Counter()
    for row in rows:
        t=row[key];obs=row["observed_should_alert"]
        if t not in ("alert","no_alert") or type(obs)!=bool:continue
        scores[{(True,"alert"):"TP",(True,"no_alert"):"FP",
                (False,"alert"):"FN",(False,"no_alert"):"TN"}[(obs,t)]]+=1
    tp,fp,fn,tn=[scores[x] for x in ("TP","FP","FN","TN")]
    return {"total":len(rows),"alert":labels["alert"],"no_alert":labels["no_alert"],
            "ambiguous":labels["ambiguous"],"scored":tp+fp+fn+tn,
            "tp":tp,"fp":fp,"fn":fn,"tn":tn,
            "precision":tp/(tp+fp) if tp+fp else None,
            "recall":tp/(tp+fn) if tp+fn else None}
def main():
    audit=compare_reviewers(P)
    assert audit["case_count"]==200 and audit["pairwise"]["A-C"]["disagreement"]==66
    data=load_frozen(D)
    assert data["dataset_sha256"]==SHA and len(data["cases"])==200
    _,a=_read_evaluations(A,data);_,b=_read_evaluations(B,data)
    sealed=json.loads(C.read_text(encoding="utf-8"))
    c={x["source_case_id"]:x for x in sealed["results"]}
    ids={x["id"] for x in data["cases"]}
    assert len(ids)==len(a)==len(b)==len(c)==200
    assert set(a)==set(b)==set(c)==ids
    owner=json.loads(I.read_text(encoding="utf-8"))
    expected={"schema_version":1,"dataset_sha256":SHA,"reviewer_id":"AC",
              "phase":"significance","expected_cases":66,"completed_cases":66,
              "export_utc":"2026-10-22T12:01:16.693Z"}
    assert all(owner.get(k)==v for k,v in expected.items())
    votes=owner["answers"]
    assert isinstance(votes,dict) and len(votes)==66 and all(v in W for v in votes.values())
    diff={k for k in ids if a[k]["warrant"]!=c[k]["warrant"]}
    assert len(diff)==66 and diff==set(votes),"Owner export must cover exactly A/C disagreements"
    source_format={key:owner[key] for key in
       ("schema_version","dataset_sha256","reviewer_id","phase","export_utc",
        "expected_cases","completed_cases")}
    source_format["answers"]=[{"id":k,"warrant":v} for k,v in votes.items()]
    reconstructed=json.dumps(source_format,ensure_ascii=False,indent=2)
    assert hashlib.sha256(reconstructed.encode("utf-8")).hexdigest()==UPLOAD_SHA
    write(P/"owner_ac_66_answers_20261022.original.json",reconstructed)
    rows=[];align=Counter();transition=Counter()
    for case in data["cases"]:
        key=case["id"];va=a[key]["warrant"];vb=b[key]["warrant"];vc=c[key]["warrant"]
        reviewed=key in diff;final=votes[key] if reviewed else va
        if reviewed:
            align["kept_A" if final==va else "agreed_C" if final==vc else "third_option"]+=1
            transition[(va,vc,final)]+=1
        rows.append({"id":key,"symbol":case["symbol"],"scenario_type":case["scenario_type"],
            "tags":case.get("tags",[]),"input_sha256":case["input_sha256"],
            "A":va,"B":vb,"C":vc,"owner_reviewed":reviewed,
            "owner_vote":votes.get(key),"final":final,
            "source":"owner_20261022" if reviewed else "unchanged_A",
            "changed_from_A":final!=va,
            "observed_should_alert":case.get("observed",{}).get("should_alert")})
    assert len(rows)==200 and sum(align.values())==66
    assert Counter(votes.values())=={"no_alert":50,"ambiguous":9,"alert":7}
    base=metrics(rows,"A");combined=metrics(rows,"final")
    assert (combined["alert"],combined["no_alert"],combined["ambiguous"])==(31,159,10)
    by_coin={sym:metrics([r for r in rows if r["symbol"]==sym],"final")
             for sym in ("BTC","ETH","GRAM","SOL")}
    ref={"schema_version":1,"dataset_sha256":SHA,
      "reference_version":"owner_A_C_re_review_v1_20261022",
      "status":"private_prompt_calibration_candidate_not_official_ground_truth",
      "source_sha256":{"dataset":hashfile(D),"A":hashfile(A),"B":hashfile(B),
                       "C":hashfile(C),"owner_66_upload":UPLOAD_SHA},
      "policy":"Apply owner votes to exactly 66 A/C disagreements; retain A on 134 agreements.",
      "limitations":["Owner saw C explanations on reviewed cases, so labels are not blinded",
                     "134 retained A labels were not re-reviewed",
                     "No written reasons supplied for owner votes",
                     "Ambiguous remains unscored, not a negative",
                     "Repeatedly inspected, stratified calibration set is not an independent holdout"],
      "case_labels":rows}
    scorer={"dataset_sha256":SHA,"evaluator_id":"owner_AC_calibration_20261022",
        "labels":[{"id":r["id"],"warrant":r["final"],"useful":None,"factual":None} for r in rows]}
    main_path=Path(str(O)+".json");score_path=Path(str(O)+".scorer.json")
    changes_path=Path(str(O)+".changes_66.csv");report_path=Path(str(O)+".summary.md")
    write(main_path,ref);write(score_path,scorer)
    import io
    sink=io.StringIO(newline="")
    writer=csv.writer(sink,lineterminator="\n")
    writer.writerow(("id","symbol","scenario_type","A","B","C","owner_final",
                     "changed_from_A","observed_should_alert"))
    for r in rows:
        if r["owner_reviewed"]:
            writer.writerow([r[k] for k in ("id","symbol","scenario_type","A","B","C",
                                            "final","changed_from_A","observed_should_alert")])
    write(changes_path,sink.getvalue())
    def pct(v):return "N/A" if v is None else f"{v:.1%}"
    report=[
      "# CCW-41 owner-reviewed significance reference v1",
      "",
      "Status: PRIVATE PROMPT CALIBRATION CANDIDATE. Not officially promoted as ground truth.",
      "Frozen 200-case dataset SHA: "+SHA,
      "Owner 66-response original SHA: "+UPLOAD_SHA,
      "66 re-reviewed A/C disagreements + 134 original A labels on A/C agreements.",
      "",
      "## Warrant distributions",
      "| Source | Alert | No alert | Ambiguous |","|---|---:|---:|---:|",
      f"| Original A (200) | {base['alert']} | {base['no_alert']} | {base['ambiguous']} |",
      "| Owner new decisions (66) | 7 | 50 | 9 |",
      f"| Combined candidate (200) | {combined['alert']} | {combined['no_alert']} | {combined['ambiguous']} |",
      "",
      f"Owner retained A on {align['kept_A']} disputed cases, agreed with C on {align['agreed_C']}, "
      f"chose neither on {align['third_option']}.",
      f"Changed original A in {66-align['kept_A']} cases.",
      "",
      "## How disputed labels changed",
      "| A | C | Owner | Cases |","|---|---|---|---:|"
    ]
    for (va,vc,vf),n in sorted(transition.items()):
        report.append(f"| {va} | {vc} | {vf} | {n} |")
    report+=["","## Historical bot against reference (selected benchmark only)",
       "| Reference | Scored | Ambiguous | TP | FP | FN | TN | Precision | Recall |",
       "|---|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for title,record in (("Original A",base),("Owner candidate",combined)):
        report.append(f"| {title} | {record['scored']} | {record['ambiguous']} | "
        f"{record['tp']} | {record['fp']} | {record['fn']} | {record['tn']} | "
        f"{pct(record['precision'])} | {pct(record['recall'])} |")
    report+=["","## Asset-specific labels"]
    for sym,v in by_coin.items():
        report.append(f"- {sym}: alert {v['alert']}, no_alert {v['no_alert']}, ambiguous {v['ambiguous']}")
    report+=["","## Using this reference for future model prompts",
      "1. Compare pinned model decisions against the scorer JSON on the original frozen inputs.",
      "2. Use the 66 changed decisions and historical FP/FN to diagnose materiality and novelty separately.",
      "3. Ambiguous is excluded from binary scoring. Never silently turn ambiguous into no_alert.",
      "4. Do not invent owner's reasoning: their uploaded responses only contain labels.",
      "5. Avoid fixed percentage cutoffs; assess movement in asset-specific context, prior alerts and news-support only.",
      "6. Repeated tuning on these 200 cases is calibration, not independent validation. Collect a separate blind holdout before claiming improvement.",
      "7. Neither the original A/B/C files, official CCW-16 baseline, production prompts nor the bot runtime were modified.",
      "",
      "Private output files: "+", ".join(p.name for p in
             (main_path,score_path,changes_path,report_path)),""]
    write(report_path,"\n".join(report))
    _,roundtrip=_read_evaluations(score_path,data)
    assert len(roundtrip)==200 and all(roundtrip[x["id"]]["warrant"]==x["final"] for x in rows)
    print("COMBINED",json.dumps(combined))
    print("BASE_A",json.dumps(base))
    print("ALIGN",dict(align),"OWNER_CHANGES",66-align["kept_A"])
    print("PAIR_TRANSITIONS",str(dict(transition)))
    print("PER_COIN",json.dumps(by_coin))
    print("OUTPUTS",str(main_path),str(score_path),str(changes_path),str(report_path),sep="\n")

if __name__=="__main__":main()
