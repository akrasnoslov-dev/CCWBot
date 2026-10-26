"""Design two fully versioned offline prompt candidates; no inference, runtime edits or provider calls."""
from pathlib import Path
import sys,json,hashlib,collections
HERE=Path(__file__).resolve().parent; ROOT=HERE.parents[2]; DATA=HERE.parent
sys.path.insert(0,str(ROOT))
from bot.services.ai_agent_groq import _EVENT_SIGNIFICANCE_INSTRUCTIONS, _event_significance_prompt_payload
from bot.alerting.event_identity import _json_dumps
from scripts.event_alert_benchmark import load_frozen
baseline=(ROOT/"benchmarks/ccw15-v1/production.txt").read_bytes()
assert baseline.endswith(b"\n") and baseline.decode()[:-1]==_EVENT_SIGNIFICANCE_INSTRUCTIONS
base=_EVENT_SIGNIFICANCE_INSTRUCTIONS
ADDITIONS={
"ccw43_incremental_market_leg_v1":"""CCW-43 E1, evidence of the NEW leg (revised after paired Groq/Cloudflare error audit):
A current event can be the newly observed MATERIAL EXTENSION of a direction already mentioned by prev. Compare the actual s price path up to m=0, cw over w, and observed cl/c30/c60 against prev.min, prev.cw and cnt. Ask two separate questions: is the current movement significant for this asset, and what actually changed after the prior alert? New lower lows/higher highs, a substantial fresh segment after prev, or a genuinely new sharp reversal can be novel even when the direction, semantic family, or prior 24-hour trend remains the same. A recently delivered prev or many cnt events is not proof that these new snapshots were already communicated. Do not count elapsed time or headlines as proof of novelty, however.
Conversely, a historically large cw may largely repeat the same old segment. If cl is tiny, recent s has flattened, and prev already described the same development, reject the event as continuation/repeated even when pw or c24 is large. Missing cl/prev does not prove newness; require affirmative visible novelty. An isolated c30 jump cannot turn an otherwise routine cw into an important reversal without substantive current-path change.
When c30/c60 are missing, use genuinely available cw and time-ordered s; never infer absent intervals. A partial rebound does not erase a materially important new current-window loss, and a quiet most-recent interval does not erase a clear prior current-window displacement.
Do not use rigid numeric cutoffs. Retain materiality then novelty then should_alert; reject news-only alerts. Six output fields only, as specified above.""",
"ccw43_two_sided_counterfactual_v1":"""CCW-43 E2, two-sided evidence audit (revised after provider-separated FP/FN audit):
Before setting should_alert=true, challenge the decision with BOTH contrasts:
(A) Ignore news, c24 and prev temporarily. Does cw plus observed s, with sound c30/c60 and same-asset pw when available, independently establish a materially notable CURRENT change? A striking daily headline, historical ranking, small one-interval bounce or opposing c24 direction cannot supply missing current materiality.
(B) Restore prev, cl and cnt. Is there affirmative evidence of an incremental episode not already described? Compare current price and trajectory with the time and window of prev; overlapping cw, rising historical percentile and another headline are not independent new legs. Re-alert only when actual supplied post-alert movement or a substantive new observed turn establishes novelty. High event counts alone cannot veto genuinely new evidence.
Before setting should_alert=false, challenge the denial: is the latest observed segment clearly a new large extension, deeper low/higher high or material counter-move after the earlier alert, even though the broad episode is still in the same direction? Do not dismiss real price displacement solely because prev is recent or c30/c60 are absent; do not confuse per-recipient cooldown with this global decision.
Judge magnitude contextually by this asset, not fixed percentage/percentile limits. If materiality or novelty is unsupported, default no alert, selecting routine_move or unclear as appropriate. News may corroborate established market significance but not create it. Keep six-field JSON schema and allowed enum combinations unchanged.""",
}
old_texts={(ROOT/"benchmarks/ccw15-v1"/name).read_text().rstrip("\n") for name in ("production.txt","materiality-evidence.txt","novelty-independent.txt")}
cases=load_frozen(DATA/"v2_private_sanitized.json")["cases"]
manifest={"task":"CCW-43","artifact_version":"20261023-v1","model_visible_system_message":"You are a careful crypto monitoring assistant.","baseline_instruction_sha256":hashlib.sha256(base.encode()).hexdigest(),"baseline_file_sha256":hashlib.sha256(baseline).hexdigest(),"dataset_sha256":"ed126380369014e6522cee49009b880cf0350aa7565269d50641c3f1bbdc3bee","prompts":{},"test_scope":"UNTESTED_OFFLINE_DESIGN; no API calls or production change"}
for key,append in ADDITIONS.items():
    text=base+"\n"+append+"\n"
    assert len(text)>len(base)+500 and text.rstrip("\n") not in old_texts
    f=HERE/(key+".txt");f.write_bytes(text.encode())
    prompt=text[:-1]
    fingerprints=[]
    lengths=[]
    for case in cases:
        formatted=prompt+"\nInput JSON:\n"+_json_dumps(_event_significance_prompt_payload(case["input"]))
        fingerprints.append(hashlib.sha256(formatted.encode()).hexdigest())
        lengths.append(len(formatted.encode()))
    manifest["prompts"][key]={
        "file":f.name,
        "file_sha256":hashlib.sha256(f.read_bytes()).hexdigest(),
        "instruction_sha256":hashlib.sha256(prompt.encode()).hexdigest(),
        "rendered_200_sha256":hashlib.sha256("\n".join(fingerprints).encode("ascii")).hexdigest(),
        "max_user_message_bytes":max(lengths),
        "all_cases_covered":len(fingerprints),
        "output_fields":["symbol","materiality","novelty","should_alert","reason_code","confidence"],
        "schema_contract":"materiality=material|routine|unclear; novelty=new|continuation|repeated|unclear; confidence=low|medium|high; should_alert=true iff materiality=material, novelty=new, reason_code in unusual_move|fast_move|reversal|trend_acceleration|market_news_alignment; false reason_code=routine_move|news_only|unclear",
    }
(HERE/"candidate_manifest.json").write_text(json.dumps(manifest,indent=2)+"\n",encoding="utf-8")
print(json.dumps(manifest,indent=2))
