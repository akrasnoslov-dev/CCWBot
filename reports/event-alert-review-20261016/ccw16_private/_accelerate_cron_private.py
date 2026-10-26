"""Change only the CCW-16 experiment user cron cadence, preserving all other jobs."""
import json
import subprocess
remote = r'''
import subprocess
import json
import pwd,os
from pathlib import Path
assert os.geteuid() != 0 and pwd.getpwuid(os.geteuid()).pw_name == 'ccwbot_ops'
r=subprocess.run(['crontab','-l'],capture_output=True,text=True,check=True)
original=r.stdout
lines=original.splitlines(keepends=True)
selected=[i for i,x in enumerate(lines) if 'CCW16_ISOLATED_PILOT' in x]
assert len(selected)==1, 'CCW16 marker not unique'
line=lines[selected[0]]
assert line.startswith('*/10 * * * * ') or line.startswith('*/2 * * * * '), 'Unexpected schedule'
if line.startswith('*/10'):
    lines[selected[0]]=line.replace('*/10 * * * * ','*/2 * * * * ',1)
    result=subprocess.run(['crontab','-'], input=''.join(lines), text=True,
        capture_output=True, check=True)
updated=subprocess.run(['crontab','-l'],capture_output=True,text=True,check=True).stdout
assert updated==''.join(lines) and len(updated.splitlines())==len(original.splitlines()), 'Unexpected cron mutation'
print(json.dumps({'old_interval_minutes':10 if line.startswith('*/10') else 2,'new_interval_minutes':2,
                 'unrelated_cron_entries_preserved':True,'cron_verified':True}))
'''
r=subprocess.run(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=8',
    'ccwbot-prod-ops','python3 -'],input=remote,text=True,capture_output=True,timeout=30)
if r.returncode:raise RuntimeError('Cron cadence change failed')
for line in r.stdout.splitlines():
 try:
  item=json.loads(line)
  if item.get('cron_verified'):print(json.dumps(item,sort_keys=True))
 except ValueError:pass
