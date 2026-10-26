"""Private analysis of uploaded human responses; no external calls."""
from pathlib import Path
from collections import Counter
import json
import importlib.util

root=Path(__file__).resolve().parent
a="NNNNNNYYNNNNNYYNNNNNNNNNNNNNNNNNNNN?NNNNN?NYYNNN?NNNNNNNNNN???NN??YN?NNNNNNNNYNN??NNNYYY?NNNY????NN?NNNNNNNY?N??N??????N?YNYYNNY?NNYYYYYNNNYNY??YYYNNYNNYNYNNNN?NN?YYNYY??YN?NNNNYNYY?Y??Y?NNN??N?Y?????"
b=(
"NNNNNNYY??N??YYN?N?NNNNNNNNNNNNNYYY?NNN??YYYY???NN"
"NNNNNNNNYYYYYYYYYYYYYNN?NNNY?????Y?YYYYYNNYYYYYN?Y"
"N?NNN?NYYYYYYYYNYYYYYYYY?NYYYNNYYYYYYYYY?YYYYYY??Y"
"YNYN?NNYY????YYYYYYY??Y??NNYYYYY??YYYN?YYY??YYYYYY"
)
D={"Y":"alert","N":"no_alert","?":"ambiguous"}
spec=importlib.util.spec_from_file_location("pr1",root/"validation/scripts/event_alert_benchmark.py")
pr1=importlib.util.module_from_spec(spec)
spec.loader.exec_module(pr1)
data=pr1.load_frozen(root/"v2_private_sanitized.json")
cases=data["cases"]
assert len(cases)==len(a)==len(b)==200
assert data["dataset_sha256"]=="ed126380369014e6522cee49009b880cf0350aa7565269d50641c3f1bbdc3bee"
assert cases[0]["id"]=="ev_da40ee965d9857fe" and cases[-1]["id"]=="ev_bc7ddfa4599baa09"
sent={c["id"] for c in cases if c["observed"].get("final_message")}
assert len(sent)==72 and "ev_7bc9f5986fce346f" in sent
def save(name,x):
 (root/name).write_text(json.dumps(x,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
for who,votes in (("A",a),("B",b)):
 doc={"dataset_sha256":data["dataset_sha256"],
      "evaluator_id":"human_owner" if who=="A" else "human_friend",
      "labels":[{"id":c["id"],"warrant":D[votes[i]],"useful":None,"factual":None}
                for i,c in enumerate(cases)]}
 save("reviewer_"+who+"_significance_for_pr1.json",doc)
merged,agreement=pr1.reconcile(
 data,root/"reviewer_A_significance_for_pr1.json",
 root/"reviewer_B_significance_for_pr1.json")
result=pr1.report(data,merged,agreement)
ev=result["overall"]["event_level"]
assert agreement["reviewed_by_both"]==200 and agreement["unresolved_disagreements"]==99
assert (ev["tp"],ev["fp"],ev["fn"],ev["tn"])==(20,30,17,27)
save("baseline_consensus_private.json",result)
conflicts=[{"id":c["id"],"symbol":c["symbol"],
            "observed_utc":c["source_utc"],
            "window_move_percent":c["input"]["market"]["chg_window_percent"],
            "reviewer_A":D[a[i]],"reviewer_B":D[b[i]],"resolution":None}
           for i,c in enumerate(cases) if a[i]!=b[i]]
assert len(conflicts)==99
save("unresolved_human_disagreements_private.json",{
 "dataset_sha256":data["dataset_sha256"],"conflicts":conflicts})
bycoin=[]
for sym in ("BTC","ETH","GRAM","SOL"):
 c=result["by_symbol"][sym]["event_level"]
 bycoin.append([sym,c["scored_cases"],c["tp"],c["fp"],c["fn"],c["tn"],
                c["precision"],c["recall"]])
print("SUMMARY",{"cases":200,"agreed_definite":ev["scored_cases"],
 "both_ambiguous":ev["ambiguous_cases"],
 "different_verdicts":len(conflicts),
 "confusion":{k:ev[k] for k in ("tp","fp","fn","tn")},
 "precision":ev["precision"],"recall":ev["recall"],
 "weighted":result["overall"]["delivered_weighted_precision"],
 "bycoin":bycoin})
