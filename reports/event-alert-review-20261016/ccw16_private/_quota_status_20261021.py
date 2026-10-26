"""Audit only aggregated benchmark budget and next-call feasibility (no inference)."""
import json
import subprocess
from datetime import datetime, timezone
script = r"""
import json
from collections import defaultdict, Counter
from datetime import datetime,timezone
from pathlib import Path
b=Path('/home/ccwbot_ops/ccw16_replay')
data=json.loads((b/'pilot-ledger.json').read_text())
rows=data['attempts']
by=defaultdict(lambda:{'n':0,'total_tokens':0,'settled':0,'reserved':0,'last_status':{},'prompts':Counter(),'last_time':None})
today=datetime.now(timezone.utc).date()
for x in rows:
 k=x['provider']; v=by[k]
 v['n']+=1
 v['prompts'][x['prompt']]+=1
 v['total_tokens']+=(x.get('total_tokens') or 0)
 v['last_status'][x.get('status','reserved')]=v['last_status'].get(x.get('status','reserved'),0)+1
 if datetime.fromisoformat(x['timestamp']).date()==today:
  v['reserved']+=x['reserved_units']
  v['settled']+=x.get('settled_units',x['reserved_units'])
 v['last_time']=x['timestamp']
for v in by.values():v['prompts']=dict(v['prompts'])
print(json.dumps({'today_utc':str(today),'by_provider':dict(by)},sort_keys=True))
"""
r=subprocess.run(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=8','ccwbot-prod-ops','python3 -'],input=script,text=True,capture_output=True,timeout=22)
if r.returncode: raise RuntimeError('Could not inspect private ledger')
for line in r.stdout.splitlines():
 try:
  obj=json.loads(line)
  if obj.get('today_utc') and obj.get('by_provider'):
   print(json.dumps(obj,sort_keys=True))
 except ValueError:
  pass
