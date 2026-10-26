"""Commit only reviewed PR349 benchmark tooling after a complete test run."""
import subprocess
from pathlib import Path

root=Path(r'D:\Projects\CCWBot')
python=root/'.venv/Scripts/python.exe'
ruff=root/'.venv/Scripts/ruff.exe'
allowed=[
 'docs/event_alert_benchmark.md',
 'scripts/auto_event_alert_quality_replay.py',
 'scripts/auto_event_significance_replay.py',
 'scripts/live_event_significance_benchmark.py',
 'scripts/merge_event_significance_runs.py',
 'scripts/multi_provider_event_significance_benchmark.py',
 'tests/test_auto_event_significance_replay.py',
 'tests/test_merge_event_significance_runs.py',
 'tests/test_multi_provider_event_significance_benchmark.py',
]
def run(args):
 r=subprocess.run([str(x) for x in args],cwd=root,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
 print('EXEC:',args[0],'status',r.returncode,flush=True)
 print(r.stdout[-3200:],flush=True)
 if r.returncode: raise SystemExit(r.returncode)
 return r.stdout
assert run(['git','branch','--show-current']).strip().endswith('fix/event-alert-pr2-semantic-cooldown')
run([ruff,'check','.'])
run([python,'-m','pytest','tests','-q'])
run(['git','add','--',*allowed])
staged=run(['git','diff','--cached','--name-only'])
if set(staged.splitlines())!=set(allowed):
 raise RuntimeError('Unexpected staged files; refusing commit')
run(['git','diff','--cached','--check'])
run(['git','commit','-m','test(alerts): resume provider benchmark candidates with safety gates'])
run(['git','push','origin','HEAD:fix/event-alert-pr2-semantic-cooldown'])
print('PUSHED_COMMIT',run(['git','rev-parse','HEAD']).strip(),flush=True)
