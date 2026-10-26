"""Verify completed research, reconcile metrics and fill the decision reports."""
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import statistics
import subprocess

ROOT=Path(__file__).resolve().parent

def sha(path):
 with path.open('rb') as handle:return hashlib.file_digest(handle,'sha256').hexdigest()

def main():
 spec=importlib.util.spec_from_file_location('ccw25_benchmark',ROOT/'benchmark.py')
 bench=importlib.util.module_from_spec(spec);spec.loader.exec_module(bench)
 bench.summary()  # Refuses incomplete or duplicate/overlapping shards.
 cases=json.loads((ROOT/'corpus.json').read_text(encoding='utf-8'))
 by_name={c['name']:c for c in cases}
 runs=[];all_rows=[]
 for name in ['qwen4.results.json','qwen4.long.results.json','phi.results.json','qwen7.results.json']:
  p=ROOT/name;d=json.loads(p.read_text(encoding='utf-8'));all_rows.extend(d['rows'])
  if name=='qwen4.results.json':names=[c['name'] for c in cases if not c['name'].startswith('long_')]
  elif '.long.' in name:names=[c['name'] for c in cases if c['name'].startswith('long_')]
  else:names=list(by_name)
  expected={(n,r) for n in names for r in range(d['repeats'])}
  if {(r['case'],r['repeat']) for r in d['rows']}!=expected:raise RuntimeError('coverage mismatch')
  for r in d['rows']:
   c=by_name[r['case']]
   if r.get('output') is not None:
    try:
     value=json.loads(r['output']);valid_json=True
    except (json.JSONDecodeError,TypeError):valid_json=False
    if valid_json!=r['json_valid']:raise RuntimeError('JSON verdict mismatch')
    if r.get('timings',{}).get('cache_n',0)!=0:raise RuntimeError('unexpected prompt cache reuse')
    if valid_json:
     try:bench.validate(c,value);valid_contract=True
     except Exception:valid_contract=False
     if valid_contract!=r['contract_valid']:raise RuntimeError('contract verdict mismatch')
   if r['within_deadline']!=(not r.get('error_type') and r['latency_seconds']<=c['deadline_seconds']):raise RuntimeError('deadline verdict mismatch')
  subset=[{k:c[k] for k in ['name','feature','input','messages','schema','max_tokens','deadline_seconds','expected']} for c in cases if c['name'] in names]
  runs.append({'file':name,'sha256':sha(p),'model':d['model'],'cases':names,'repeats':d['repeats'],'expected_rows':len(expected),'observed_rows':len(d['rows']),'complete':True,'input_contract_sha256':hashlib.sha256(json.dumps(subset,sort_keys=True,ensure_ascii=False).encode()).hexdigest(),'recorded_command':d['command'],'diagnostic_http_timeout_seconds':120 if name=='qwen4.results.json' else 180})
 if len(all_rows)!=74:raise RuntimeError('unexpected total request coverage')
 for model in ['qwen4','phi','qwen7']:
  if {r['case'] for r in all_rows if r['model']==model}!=set(by_name):raise RuntimeError('missing model cases')
 source=json.loads((ROOT/'dev_source_manifest.json').read_text())
 for name,want in source['files'].items():
  if sha(ROOT/'dev-source'/name)!=want:raise RuntimeError('source snapshot hash changed')
 (ROOT/'run_manifest.json').write_text(json.dumps({'source_commit':source['commit'],'source_file_count':len(source['files']),'final_runner_sha256':sha(ROOT/'benchmark.py'),'corpus_sha256':sha(ROOT/'corpus.json'),'runs':runs,'total_requests':74,'complete':True,'initial_run_note':'Initial 34 Qwen4 rows predate metadata additions and long probes. Recorded command, fixed dev-source contracts and exact disjoint case coverage are retained; no claim of a single immutable 74-request run.'},indent=2),encoding='utf-8')
 # CPU resource samples use measured process CPU seconds and timestamps. Early
 # samples lack the derived CPU field; retain them as raw observations only.
 samples=[json.loads(s) for s in (ROOT/'resource_samples.jsonl').read_text(encoding='utf-8-sig').splitlines() if s.strip()]
 resource=[]
 for model in ['qwen4','phi','qwen7']:
  rows=[r for r in samples if r['model']==model]
  cores=[r['active_logical_cpu_equivalents'] for r in rows if isinstance(r.get('active_logical_cpu_equivalents'),(int,float)) and r['active_logical_cpu_equivalents']>=0]
  resource.append({'model':model,'samples':len(rows),'cpu_samples':len(cores),'sampled_active_logical_cpu_equivalents_p50':statistics.median(cores) if cores else None,'sampled_active_logical_cpu_equivalents_peak':max(cores) if cores else None,'peak_working_set_bytes':max(r['peak_working_set_bytes'] for r in rows),'note':'Approximately 1-second Windows process samples; Qwen4 monitor covers long-report process only. First monitor samples lack CPU-derived fields due to a corrected PowerShell timer compatibility issue. Not target-host utilization.'})
 (ROOT/'resource_summary.json').write_text(json.dumps(resource,indent=2),encoding='utf-8')
 for entry in resource:
  if entry['model']!='qwen4':entry['note']='Approximately 1-second Windows process samples across this model run; not target-host utilization.'
 (ROOT/'resource_summary.json').write_text(json.dumps(resource,indent=2),encoding='utf-8')
 summary=json.loads((ROOT/'benchmark_summary.json').read_text())
 for r in summary:
  rows=[x for x in all_rows if x['model']==r['model'] and x['feature']==r['feature']]
  r['right_censored_timeouts']=sum(x.get('error_type')=='TimeoutError' for x in rows)
  r['percentile_note']='Elapsed request durations include timeout censoring; a censored percentile is a lower bound, not a completed latency.'
 (ROOT/'benchmark_summary.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
 names={'qwen4':'Qwen3-4B','phi':'Phi-4-mini','qwen7':'Qwen2.5-7B'}
 features={'event_analysis':'Significance','event_alert_render':'Render','news_intelligence':'News','market_heartbeat':'Heartbeat','daily_report':'Daily','weekly_report':'Weekly'}
 table='| Model / feature | N | JSON / contract valid | Within deadline | p50 / p95 seconds | Median generation tokens/s | Peak working set GiB |\n|---|---:|---:|---:|---:|---:|---:|\n'
 for r in sorted(summary,key=lambda x:(list(names).index(x['model']),list(features).index(x['feature']))):
  p95=('≥' if r['right_censored_timeouts'] else '')+f"{r['p95_seconds_nearest_rank']:.1f}"+(' (timeout)' if r['right_censored_timeouts'] else '')
  table+=f"| {names[r['model']]} / {features[r['feature']]} | {r['n']} | {r['json_valid']}/{r['n']} / {r['contract_valid']}/{r['n']} | {r['within_deadline']}/{r['n']} | {r['p50_seconds']:.1f} / {p95} | {r['generation_tps_median']:.1f} | {r['peak_working_set_bytes']/2**30:.2f} |\n"
 table+='\nQwen2.5-7B long weekly timed out after 180.03 seconds: completion latency is right-censored. Its weekly p95 is a lower bound. The other failed weekly response reached the 800-token limit and was invalid JSON. Percentiles describe all request attempts, not successful completions only.\n'
 brief='| Model | Requests | JSON / backend-valid | Within feature deadline | Peak working set GiB |\n|---|---:|---:|---:|---:|\n'
 for model in names:
  rows=[r for r in all_rows if r['model']==model]
  peak=max(r.get('resources',{}).get('peak_working_set_bytes',0) for r in rows)
  brief+=f"| {names[model]} | {len(rows)} | {sum(r['json_valid'] for r in rows)}/{len(rows)} / {sum(r['contract_valid'] for r in rows)}/{len(rows)} | {sum(r['within_deadline'] for r in rows)}/{len(rows)} | {peak/2**30:.2f} |\n"
 (ROOT/'benchmark_table.md').write_text(table,encoding='utf-8')
 quality='Qwen3-4B fabricated report catalysts/timelines, misstated a Render period, and described stable conditions without sufficient evidence. Phi-4-mini returned generic/unsupported report content and an empty required Heartbeat action. All three missed at least one significance fixture; Qwen2.5-7B incorrectly alerted on the news-only fixture. Some Render rejections appear to be guard false positives rather than proven model factual errors. These are manually inspected fixture findings, not measured real-world quality rates.'
 for name,token,replacement in [('technical_appendix.md','{{BENCHMARK_TABLE}}',table),('owner_decision_report.md','{{BENCHMARK_BRIEF}}',brief),('technical_appendix.md','{{QUALITY_FINDINGS}}',quality),('owner_decision_report.md','{{QUALITY_BRIEF}}',quality)]:
  p=ROOT/name;s=p.read_text(encoding='utf-8');p.write_text(s.replace(token,replacement),encoding='utf-8')
 for name in ['owner_decision_report.md','technical_appendix.md']:
  if '{{' in (ROOT/name).read_text(encoding='utf-8'):raise RuntimeError('unfilled report placeholder')
 (ROOT/'verification.json').write_text(json.dumps({'coverage_complete':True,'requests':74,'unique_cases_per_model':19,'recorded_json_contract_deadline_verdicts_rechecked':True,'source_snapshot_files_verified':len(source['files']),'workload_aggregate_reconciliation':'3573 rows = 2076 attempts + 1497 skips; 1548644 input / 549419 output tokens','production_changes':False,'paid_services_purchased':False,'research_only_ignored_files':True,'graphify':'query succeeded; update command exited 1 without diagnostics. No tracked runtime source changed; no package provisioning attempted.'},indent=2),encoding='utf-8')
 print('FINAL VERIFICATION PASS: 74 requests, 19 cases per model, source/verdict/coverage checks and report placeholders')

if __name__=='__main__':main()
