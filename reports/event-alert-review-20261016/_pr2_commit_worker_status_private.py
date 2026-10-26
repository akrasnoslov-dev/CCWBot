import subprocess
from pathlib import Path
root=Path(r'D:\Projects\CCWBot')
paths=['scripts/auto_event_alert_quality_replay.py','tests/test_multi_provider_event_significance_benchmark.py']
def run(*args):
 r=subprocess.run(args,cwd=root,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
 print(args[0],r.returncode,r.stdout[-1200:],flush=True)
 if r.returncode:raise SystemExit(r.returncode)
 return r.stdout
assert run('git','branch','--show-current').strip()=='fix/event-alert-pr2-semantic-cooldown'
run('git','add','--',*paths)
staged=run('git','diff','--cached','--name-only')
if set(staged.splitlines())!=set(paths):raise RuntimeError('unexpected staged files')
run('git','diff','--cached','--check')
run('git','commit','-m','fix(alerts): accurately record multi-provider replay results')
run('git','push','origin','HEAD:fix/event-alert-pr2-semantic-cooldown')
print('SHA',run('git','rev-parse','HEAD').strip())
run('git','status','--short')
