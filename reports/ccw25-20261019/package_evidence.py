"""Package an explicit, privacy-reviewed research whitelist; no binaries or secrets."""
import hashlib
import json
from pathlib import Path
import zipfile

ROOT=Path(__file__).resolve().parent
FILES='''README.md owner_decision_report.md technical_appendix.md benchmark.py
finalize.py download.py collect_workload.py run_remaining.py monitor_resources.ps1
package_evidence.py artifact_manifest.json benchmark_summary.json benchmark_table.md
corpus.json cost_model.json dev_source_manifest.json heartbeat_post_validation.json
host_evidence.json python_environment.json quality_review.json qwen4_memory_sizing.json
qwen4.results.json qwen4.long.results.json phi.results.json qwen7.results.json
resource_samples.jsonl resource_summary.json run_manifest.json source_manifest.json
verification.json workload_queries.json workload.json workstation.json review_notes.json'''.split()

if __name__=='__main__':
 manifest={name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in FILES}
 (ROOT/'evidence_manifest.json').write_text(json.dumps({'algorithm':'SHA-256','files':manifest,'excluded':'Model weights, runtime binaries, source bodies, bytecode, server logs, invoices and credentials.'},indent=2),encoding='utf-8')
 target=ROOT.parent/'ccw25-20261019-evidence.zip'
 with zipfile.ZipFile(target,'w',compression=zipfile.ZIP_DEFLATED) as archive:
  for name in FILES+['evidence_manifest.json']:archive.write(ROOT/name,name)
 with zipfile.ZipFile(target) as archive:
  if archive.testzip() is not None:raise RuntimeError('ZIP integrity failure')
  for name,want in manifest.items():
   if hashlib.sha256(archive.read(name)).hexdigest()!=want:raise RuntimeError('Packaged hash mismatch')
 print(json.dumps({'path':str(target),'bytes':target.stat().st_size,'sha256':hashlib.sha256(target.read_bytes()).hexdigest(),'files':len(FILES)+1}))
