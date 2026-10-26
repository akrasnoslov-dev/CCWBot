"""Private read-only CCWBot market benchmark and independent review CSV exporter."""
import csv, hashlib, io, json, random, re, subprocess
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

OUT=Path(__file__).resolve().parent
PSQL=r"C:\Program Files\PostgreSQL\18\bin\psql.exe"
KEYS=("analysis_id","coin_name","display_symbol","last_msg","market","news",
      "policy","previous_event_alert","recent_event_counts","symbol","timestamp_utc")
SYMS=("BTC","ETH","GRAM","SOL")
TARGET={"delivered":18,"positive_undelivered":7,"no_alert":25}
START="2026-10-06 00:00:00+00"
END="2026-10-16 11:00:00+00"
BANNED={"user_id","chat_id","telegram_id","telegram_chat_id","telegram_user_id",
        "username","email","phone","api_key","secret","token","password","session",
        "payment_id","prompt","raw_output","raw_message"}
CONTACT=re.compile(r"(\b[\w.+-]+@[\w.-]+\.[a-z]{2,}\b|t\.me/|telegram\.me/|"
                   r"(?:bot)?token=|api_key=|(?<!\w)@[A-Za-z0-9_]{4,})",re.I)
def canon(x): return json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(",",":"))
def sha(x): return hashlib.sha256(canon(x).encode()).hexdigest()
def safe(x):
    if isinstance(x,dict):
        for k,v in x.items():
            if k.lower() in BANNED or k.lower().endswith("_api_key") or "telegram" in k.lower():
                raise ValueError("private_field")
            safe(v)
    elif isinstance(x,list):
        for v in x: safe(v)
    elif isinstance(x,str):
        if CONTACT.search(x) or "\x00" in x or len(x)>12000: raise ValueError("private_text")
def run_psql(query,csv_mode=False):
    args=[PSQL,"-X","-w","-v","ON_ERROR_STOP=1","-h","127.0.0.1",
          "-p","15433","-U","ccwbot_investigator","-d","ccwbot","-q"]
    args+=(["-c","COPY ("+query+") TO STDOUT WITH (FORMAT CSV, HEADER TRUE)"]
           if csv_mode else ["-t","-A","-c",query])
    proc=subprocess.run(args,capture_output=True,text=True,encoding="utf-8",
                        errors="replace",timeout=110)
    if proc.returncode:
        raise RuntimeError("Read-only PostgreSQL failed, exit code "+str(proc.returncode))
    return proc.stdout
def source_data():
    identity=run_psql("SELECT current_user, current_setting('transaction_read_only'), "
                      "current_setting('default_transaction_read_only')").strip()
    if identity!="ccwbot_investigator|on|on": raise RuntimeError("Investigator safety check failed")
    properties=", ".join("'"+k+"', j.payload->'"+k+"'" for k in KEYS)
    query=f"""
SELECT to_char(e.created_at AT TIME ZONE 'UTC','YYYY-MM-DD"T"HH24:MI:SS.US"Z"') AS utc,
       e.symbol,e.should_alert::text AS decision,e.provider,e.model,
       jsonb_build_object({properties})::text AS input,
       coalesce(d.sent,0) AS sent,coalesce(d.failed,0) AS failed,
       d.message,coalesce(d.variants,0) AS variants
FROM event_ai_analyses e
CROSS JOIN LATERAL (SELECT e.raw_input_json::jsonb AS payload) j
LEFT JOIN (
 SELECT a.event_ai_analysis_id,
        count(*) FILTER(WHERE a.status='sent') AS sent,
        count(*) FILTER(WHERE a.status='failed') AS failed,
        min(a.message) FILTER(WHERE a.status='sent') AS message,
        count(DISTINCT a.message) FILTER(WHERE a.status='sent') AS variants
 FROM alerts a
 WHERE a.alert_type='event_alert'
   AND a.created_at >= '{START}'::timestamptz
   AND a.created_at < ('{END}'::timestamptz + INTERVAL '1 day')
 GROUP BY a.event_ai_analysis_id
) d ON d.event_ai_analysis_id=e.id
WHERE e.analysis_type='event_analysis'
 AND e.created_at >= '{START}'::timestamptz AND e.created_at < '{END}'::timestamptz
 AND e.symbol IN ('BTC','ETH','GRAM','SOL')
 AND e.raw_input_json IS NOT NULL AND e.should_alert IS NOT NULL
ORDER BY e.created_at,e.symbol,e.id
"""
    return list(csv.DictReader(io.StringIO(run_psql(query,True))))
def candidate(row):
    inp=json.loads(row["input"]);m=inp.get("market") or {}
    if inp.get("symbol")!=row["symbol"] or len(m.get("snapshots") or [])<2: raise ValueError("invalid_market")
    if m.get("price") is None or m.get("chg_window_percent") is None: raise ValueError("no_market_move")
    if len(inp)!=len(KEYS): raise ValueError("incomplete_input")
    safe(inp); message=row["message"]
    if message:safe(message)
    sent=int(row["sent"]);failed=int(row["failed"])
    if int(row["variants"])>1:raise ValueError("message_variants")
    decision=row["decision"]
    if decision not in ("true","false"):raise ValueError("invalid_decision")
    yes=decision=="true"
    if sent and (not yes or not message):raise ValueError("inconsistent_delivery")
    cohort="delivered" if sent else "positive_undelivered" if yes else "no_alert"
    move=float(m["chg_window_percent"]);prev=inp.get("previous_event_alert") or {}
    recent=inp.get("recent_event_counts") or {};news=inp.get("news") or []
    day=inp.get("timestamp_utc",row["utc"])[:10]
    tags={"news_present" if news else "news_absent"}
    if (recent.get("h6") or 0)>0 or (isinstance(prev.get("age_minutes"),(int,float))
                                     and prev["age_minutes"]<=240):tags.add("repeat")
    daymove=m.get("chg24h_percent")
    if isinstance(daymove,(int,float)) and move and daymove:
        tags.add("reversal" if (move>0)!=(daymove>0) else "continuation")
    pctile=m.get("relative_window_percentile_30d")
    if isinstance(pctile,(int,float)) and 35<=pctile<=65:tags.add("borderline")
    fid=sha(inp)
    opaque="ev_"+hashlib.sha256((row["utc"]+"|"+row["symbol"]+"|"+fid).encode()).hexdigest()[:16]
    obs={"should_alert":yes,"delivered_count":sent,"delivery_failures":failed}
    if message:obs["final_message"]=message
    primary=("delivered" if cohort=="delivered" else "no_alert" if cohort=="no_alert"
             else "repeat" if "repeat" in tags else "news_present" if news else "news_absent")
    case={"id":opaque,"symbol":row["symbol"],"scenario_type":primary,
          "tags":sorted(tags),"source_type":"approved_read_only",
          "input":inp,"input_sha256":fid,"observed":obs,
          "source_utc":row["utc"],"baseline_provider":row["provider"],
          "baseline_model":row["model"],"sampling_cohort":cohort}
    safe(case)
    marker=row["symbol"]=="BTC" and day=="2026-10-16" and abs(move-.1602)<.00025
    return case,marker
def variations(c):
    f=c["input"];m=f["market"];v=float(m["chg_window_percent"]);p=f.get("previous_event_alert") or {}
    return {"date:"+c["source_utc"][:10],"news:"+str(bool(f.get("news"))),
            "dir:"+("up" if v>0 else "down" if v<0 else "flat"),
            "size:"+("tiny" if abs(v)<.25 else "small" if abs(v)<.75 else "medium" if abs(v)<2 else "large"),
            "window:"+str(m.get("analysed_window_minutes")),
            "prior:"+str(bool(p)),"tags:"+",".join(c["tags"])}
def select(items):
    groups=defaultdict(list)
    for c,marker in items:groups[(c["symbol"],c["sampling_cohort"])].append((c,marker))
    result=[]
    for sym in SYMS:
        for cohort,n in TARGET.items():
            pool=list(groups[(sym,cohort)])
            if len(pool)<n:raise ValueError("insufficient "+sym+"/"+cohort+" "+str(len(pool)))
            random.Random(20261016+len(result)+sum(map(ord,sym+cohort))).shuffle(pool)
            out=[];special=next((x for x in pool if x[1]),None)
            if special:out.append(special);pool.remove(special)
            seen=set()
            for x,_ in out:seen|=variations(x)
            while len(out)<n:
                i=max(range(len(pool)),key=lambda k:(len(variations(pool[k][0])-seen),
                            -sum(x["source_utc"][:10]==pool[k][0]["source_utc"][:10] for x,_ in out),-k))
                o=pool.pop(i);out.append(o);seen|=variations(o[0])
            result.extend(c for c,_ in out)
    result.sort(key=lambda c:(c["symbol"],c["source_utc"],c["id"]))
    if len(result)!=200 or len({c["id"] for c in result})!=200:raise AssertionError("selection")
    return result,{a+"/"+b:len(groups[(a,b)]) for a in SYMS for b in TARGET}
def context(c):
    f=c["input"];m=f["market"];p=f.get("recent_event_counts") or {}
    return {"case_id":c["id"],"symbol":c["symbol"],"time_utc":f.get("timestamp_utc",""),
            "price":m.get("price",""),"window_minutes":m.get("analysed_window_minutes",""),
            "window_move_pct":m.get("chg_window_percent",""),"24h_move_pct":m.get("chg24h_percent",""),
            "30m_move_pct":m.get("chg30m_percent",""),"1h_move_pct":m.get("chg1h_percent",""),
            "30d_window_percentile":m.get("relative_window_percentile_30d",""),
            "snapshots_minutes_price":canon(m.get("snapshots")),
            "last_message_info":canon(f.get("last_msg")),
            "previous_event_info":canon(f.get("previous_event_alert")),
            "events_6h":p.get("h6",""),"events_24h":p.get("h24",""),
            "selected_news":canon(f.get("news"))}
def csvwrite(path,rows):
    with path.open("w",encoding="utf-8-sig",newline="") as file:
        writer=csv.DictWriter(file,list(rows[0]),extrasaction="ignore")
        writer.writeheader();writer.writerows(rows)
def main():
    source=source_data();valid=[];excluded=Counter();hashes=set()
    for row in source:
        try:
            c,marker=candidate(row)
            if c["input_sha256"] in hashes:excluded["duplicate_input"]+=1;continue
            valid.append((c,marker));hashes.add(c["input_sha256"])
        except Exception as e:excluded[str(e)[:60]]+=1
    cases,pools=select(valid);data_hash=sha(cases)
    manifest={"schema_version":1,"version":"v2-2026-10-16-private-human-review",
              "provenance":"real_market_sanitized",
              "extraction":{"source":"ccwbot_investigator SELECT-only over SSH tunnel",
                "created_utc":datetime.now(timezone.utc).isoformat(),
                "source_window_start":START,"source_window_end_exclusive":END,
                "sampling":"18 delivered / 7 positive but undelivered / 25 no-alert per symbol",
                "candidate_count":len(source),"excluded":dict(excluded),
                "positive_render_mutation":"Remove post-significance render/identity keys; preserve 11 original significance input fields",
                "source_revision":"unknown if production deployment changed within window",
                "population_estimates":"Do not extrapolate this intentionally stratified sample",
                "eligible_recipients_on_no_alert":"not_available"},
              "cases":cases,"dataset_sha256":data_hash}
    (OUT/"v2_private_sanitized.json").write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    for reviewer in ("A","B"):
        phase1=[{**context(c),"warrant (alert/no_alert/ambiguous)":"","warrant_reason":""} for c in cases]
        phase2=[{**context(c),"final_delivered_message":c["observed"]["final_message"],
                "useful (yes/no)":"","factual (yes/no)":"","reason_if_no":""}
                for c in cases if c["observed"].get("final_message")]
        csvwrite(OUT/("reviewer_"+reviewer+"_phase1_significance.csv"),phase1)
        csvwrite(OUT/("reviewer_"+reviewer+"_phase2_final_message.csv"),phase2)
        for phase in ("significance","message"):
            cards=[{"id":c["id"],"symbol":c["symbol"],"input":c["input"],
                    **({"final_message":c["observed"].get("final_message")} if phase=="message" else {})}
                   for c in cases]
            packet={"schema_version":1,"dataset_sha256":data_hash,"phase":phase,"cases":cards}
            (OUT/("reviewer_"+reviewer+"_"+phase+"_blind.json")).write_text(
                json.dumps(packet,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    summary={"selected":len(cases),"per_symbol_cohort":dict(Counter(
              c["symbol"]+"/"+c["sampling_cohort"] for c in cases)),
             "selected_tags":dict(Counter(t for c in cases for t in c["tags"])),
             "final_messages":sum(bool(c["observed"].get("final_message")) for c in cases),
             "original_candidate_count":len(source),"privacy_valid_candidates":len(valid),
             "excluded":dict(excluded),"available_pools":pools,
             "dataset_sha256":data_hash,"unlabelled":True,"private":True,
             "case_with_btc_small_move":sum(
              c["symbol"]=="BTC" and c["source_utc"][:10]=="2026-10-16"
              and abs(float(c["input"]["market"]["chg_window_percent"])-.1602)<.00025
              for c in cases)}
    (OUT/"sampling_summary.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    readme="""# CCWBot Event Alert: two independent human reviewers

Private real-market sample, 200 contexts (50 each BTC/ETH/GRAM/SOL).
Never commit or publicly post this folder.
Reviewers must NOT see each other's answers or discuss cases until both finish.

Phase 1: each reviewer opens their own reviewer_A/B_phase1_significance.csv.
Fill the column warrant (alert/no_alert/ambiguous) for all 200 rows:
alert = one new alert deserved, no_alert = noise, ambiguous = insufficient or unclear.
Base decisions on actual market snapshots, 24h context and selected news.
News alone must not cause alert; do not apply any fixed percentage threshold.
Write a short warrant_reason for ambiguous or interesting cases.
No original bot decisions are displayed in the phase 1 file.

Both phase-1 files must be saved and locked BEFORE phase-2 work.

Phase 2: each reviewer opens their own reviewer_A/B_phase2_final_message.csv.
Only actually delivered alerts appear; inspect their final Telegram text.
For each message mark useful (yes/no), factual (yes/no).
Useful = adds a grounded market relationship or useful next market observation.
Factual = no invented number, direction, period, catalyst or trajectory.
Explain any no in reason_if_no.

Return your two completed CSVs privately to project owner, in UTF-8.
Keep case_id and all evidence columns unchanged.
Do not share the unblinded v2_private_sanitized.json with evaluators.

Sampling is intentionally stratified: 18 delivered, 7 positive/undelivered,
25 no-alert cases per symbol. It is NOT a natural-frequency population sample.
The sampled baseline decision and any delivered message remain hidden until evaluation.
No correctness/quality metrics can be computed until two humans independently label.
Full significance-stage inputs retain exactly 11 whitelisted original market fields;
positive stored inputs have subsequent render-stage output stripped.
"""
    (OUT/"README_HUMAN_REVIEW.md").write_text(readme,encoding="utf-8")
    print(json.dumps(summary,ensure_ascii=False,indent=2))
    print("REVIEW_FOLDER="+str(OUT))
if __name__=="__main__":main()
