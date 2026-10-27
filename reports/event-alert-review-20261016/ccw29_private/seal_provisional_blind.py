"""Seal a GPT-6 provisional blind significance review of fresh cases before provider inference.

WARNING: GPT-6 was involved in prompt design, so this is NOT an independent owner
or external-reviewer ground truth. It is blind only to current provider decisions.
"""
import json,pathlib,hashlib,collections
root=pathlib.Path(r"D:\Projects\CCWBot\reports\event-alert-review-20261016\ccw29_private\fresh_holdout")
packet=json.loads((root/"holdout_20_blind_packet_PRIVATE.json").read_text(encoding="utf-8"))
labels={
"ev_72cd3db99c134e42":("ambiguous","A fresh SOL down leg since a previously delivered up alert is visible, but current three-hour displacement is moderate; significance needs judgment."),
"ev_544477d235fbf661":("no_alert","GRAM has an ordinary small three-hour drift and partial recovery; days-old comparison is not current materiality."),
"ev_8b8b87e751079825":("ambiguous","BTC decline is meaningful in the three-hour view, but overlaps a same-direction alert 148 minutes earlier and fresh change is smaller."),
"ev_a3ab11595080a841":("no_alert","SOL three-hour decline largely overlaps earlier down alert, and its current price is slightly higher than last delivered price."),
"ev_49f6b1c0c9db82b2":("no_alert","ETH modest down move, nearly unchanged since old same-direction alert; news does not establish fresh move."),
"ev_8d4e92992898e191":("no_alert","BTC modest decline with no compelling new price-path displacement."),
"ev_d8f9a8e4eadaa72c":("no_alert","ETH down window substantially overlaps recent lower-price alert; current price rebounded slightly."),
"ev_3506c242b8186a8e":("ambiguous","ETH strong three-hour rise, but an up alert was delivered 29 minutes earlier; fresh 30-minute gain may or may not warrant second alert."),
"ev_b983dc5bcb5f5e35":("no_alert","GRAM near-flat three-hour path; days-old lower comparison is not current materiality."),
"ev_c46fa7dacd0047da":("no_alert","SOL current three-hour bounce is modest, not substantial reversal on available market path."),
"ev_5f3b346f5a08510a":("no_alert","BTC large three-hour rise fully discussed 29 minutes ago; price since delivery slightly declined."),
"ev_8b05eb6c15b1a67d":("no_alert","GRAM nearly flat three hours and no meaningful reversal; broad altcoin news insufficient."),
"ev_64d6c8ab2d814257":("no_alert","GRAM near-zero three-hour displacement, small latest rebound not a material event."),
"ev_8ecaa26b75fcdb66":("no_alert","GRAM small three-hour down change, routine despite preceding upwards move."),
"ev_892b39ac0c5d9692":("no_alert","SOL flat three-hour move, no new episode since prior alert."),
"ev_efba2ebdf7d341bc":("no_alert","BTC steady but modest move partly overlapping recent up alert; fresh price increase is small."),
"ev_ba0487d20e4f1d69":("alert","ETH new sustained decline across current window, substantial additional drop since same-direction alert six hours earlier."),
"ev_6d02b017020d73a3":("no_alert","SOL near-flat three-hour move; larger price drift since prior alert is not current-window materiality."),
"ev_2350f56c1233f023":("no_alert","BTC preceding large up window overlaps an hour-old up alert; current price nearly unchanged."),
"ev_0c0ba772d3e480b8":("ambiguous","ETH three-hour rally is moderate and follows a same-direction alert five hours earlier; distinct new material leg uncertain.")
}
ids={c["id"] for c in packet["cases"]}
assert len(ids)==len(labels)==20 and set(labels)==ids
assert not (root/"reviewer_gpt6_provisional_blind.json").exists()
doc={"schema_version":1,"dataset_sha256":packet["dataset_sha256"],
 "reviewer_id":"gpt6_provisional_blind_to_candidate_predictions_NOT_independent_of_design",
 "limitations":"This model participated in prior prompt drafting. These labels are exploratory and cannot replace independently blinded external/owner review.",
 "model_id":"GPT-6 ChatGPT; interface non-reproducible; no API run","owner_adjudicated":False,
 "reference_for_release":False,
 "labels":[{"id":c["id"],"input_sha256":c["input_sha256"],"warrant":labels[c["id"]][0],
 "confidence":"medium" if labels[c["id"]][0]=="ambiguous" else "medium",
 "rationale":labels[c["id"]][1]} for c in packet["cases"]]}
dest=root/"reviewer_gpt6_provisional_blind.json"
dest.write_text(json.dumps(doc,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
print(json.dumps({"reviewer_type":"PROVISIONAL_NOT_INDEPENDENT","labels":dict(collections.Counter(x["warrant"] for x in doc["labels"])),"sha256":hashlib.sha256(dest.read_bytes()).hexdigest(),"dataset_sha256":doc["dataset_sha256"]}))
