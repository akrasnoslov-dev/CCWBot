"""CCW-25: bounded read-only aggregate collection; never exports prompts or IDs."""
import asyncio
import json
import os
from pathlib import Path

OUT = Path('reports/ccw25-20261019')
START = '2026-10-12T00:00:00Z'
END = '2026-10-19T00:00:00Z'
WHERE = f"created_at >= '{START}'::timestamptz AND created_at < '{END}'::timestamptz"
QUERIES = {
 'coverage': f"SELECT min(created_at) first_at,max(created_at) last_at,count(*) rows,count(*) FILTER(WHERE llm_operation_id IS NULL) missing_operation_ids FROM llm_usage_logs WHERE {WHERE}",
 'feature_status': f"SELECT call_type,status,count(*) rows,sum(prompt_tokens) input_tokens,sum(completion_tokens) output_tokens,count(prompt_tokens) input_token_rows,count(completion_tokens) output_token_rows FROM llm_usage_logs WHERE {WHERE} GROUP BY 1,2 ORDER BY 1,2",
 'daily': f"SELECT (created_at AT TIME ZONE 'UTC')::date AS utc_day,call_type,count(*) rows,count(*) FILTER(WHERE status NOT LIKE 'skipped%') attempted_rows,count(DISTINCT llm_operation_id) logical_ops,sum(prompt_tokens) input_tokens,sum(completion_tokens) output_tokens FROM llm_usage_logs WHERE {WHERE} GROUP BY 1,2 ORDER BY 1,2",
 'provider_status': f"SELECT provider,model,status,error_reason,count(*) rows,sum(prompt_tokens) input_tokens,sum(completion_tokens) output_tokens FROM llm_usage_logs WHERE {WHERE} GROUP BY 1,2,3,4 ORDER BY 1,2,3,4",
 'sizes': f"SELECT call_type,count(*) rows,count(input_chars) input_char_rows,percentile_cont(0.5) WITHIN GROUP(ORDER BY input_chars) input_chars_p50,percentile_cont(0.95) WITHIN GROUP(ORDER BY input_chars) input_chars_p95,max(input_chars) input_chars_max,percentile_cont(0.5) WITHIN GROUP(ORDER BY prompt_tokens) input_tokens_p50,percentile_cont(0.95) WITHIN GROUP(ORDER BY prompt_tokens) input_tokens_p95,percentile_cont(0.95) WITHIN GROUP(ORDER BY completion_tokens) output_tokens_p95 FROM llm_usage_logs WHERE {WHERE} AND status NOT LIKE 'skipped%' GROUP BY 1 ORDER BY 1",
 'burst': f"WITH b AS (SELECT date_trunc('minute',created_at) AS minute_bucket,count(*) rows,count(*) FILTER(WHERE status NOT LIKE 'skipped%') attempted_rows,count(DISTINCT llm_operation_id) logical_ops FROM llm_usage_logs WHERE {WHERE} GROUP BY 1) SELECT max(rows) peak_rows_per_minute,max(attempted_rows) peak_attempted_rows_per_minute,max(logical_ops) peak_logical_ops_per_minute FROM b",
 'fallback': f"WITH o AS (SELECT llm_operation_id,count(*) FILTER(WHERE status NOT LIKE 'skipped%') attempts,count(*) FILTER(WHERE status='success') successes,count(DISTINCT provider) provider_entries FROM llm_usage_logs WHERE {WHERE} AND llm_operation_id IS NOT NULL GROUP BY 1) SELECT count(*) correlated_ops,count(*) FILTER(WHERE attempts>1) multi_attempt_ops,count(*) FILTER(WHERE attempts>1 AND successes>0) recovered_multi_attempt_ops,count(*) FILTER(WHERE successes=0) no_success_ops,max(attempts) max_attempts FROM o",
 'analysis_outcomes': f"SELECT analysis_type,status,error_reason,count(*) rows FROM event_ai_analyses WHERE {WHERE} GROUP BY 1,2,3 ORDER BY 1,2,3",
 'heartbeat_outcomes': f"SELECT status,count(*) rows FROM market_heartbeats WHERE {WHERE} GROUP BY 1",
 'report_outcomes': f"SELECT report_type,provider,model,status,count(*) rows FROM market_reports WHERE {WHERE} GROUP BY 1,2,3,4 ORDER BY 1,2,3,4",
 'reuse': f"SELECT decision_stage,decision_reason,count(*) rows FROM alert_delivery_outcomes WHERE {WHERE} AND (decision_reason ILIKE '%reuse%' OR decision_reason ILIKE '%cache%') GROUP BY 1,2 ORDER BY 1,2",
}

async def main():
 import asyncpg
 OUT.mkdir(parents=True,exist_ok=True)
 (OUT/'workload_queries.json').write_text(json.dumps(QUERIES,indent=2),encoding='utf-8')
 c=await asyncpg.connect(host='127.0.0.1',port=15433,database='ccwbot',user='ccwbot_investigator',passfile=str(Path(os.environ['APPDATA'])/'postgresql/pgpass.conf'),timeout=8)
 gate={'role':await c.fetchval('SELECT current_user'),'transaction_read_only':await c.fetchval('SHOW transaction_read_only'),'default_transaction_read_only':await c.fetchval('SHOW default_transaction_read_only')}
 
 if list(gate.values())!=['ccwbot_investigator','on','on']: raise PermissionError('investigator read-only gate failed')
 result={'gate':gate,'start_utc':START,'end_utc':END,'queries':{}}
 for name,sql in QUERIES.items():
  try:
   tx=c.transaction(readonly=True)
   await tx.start()
   try:
    await c.execute("SET LOCAL statement_timeout='15s'")
    rows=await c.fetch(sql)
    result['queries'][name]=[dict(x) for x in rows]
   finally: await tx.rollback()
  except Exception as exc:
   result['queries'][name]={'error_type':type(exc).__name__}
   if type(exc).__name__=='InsufficientPrivilegeError': break
 await c.close()
 (OUT/'workload.json').write_text(json.dumps(result,indent=2,default=str),encoding='utf-8')
 print(json.dumps(result,default=str))

if __name__=='__main__': asyncio.run(main())

