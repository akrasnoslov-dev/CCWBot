import subprocess
from pathlib import Path
root=Path(r'D:\Projects\CCWBot')
python=root/'.venv/Scripts/python.exe'
worker=root/'scripts/auto_event_alert_quality_replay.py'
task='CCWBot-PR349-QualityReplay'
cmd=f'{python} {worker} --once'
r=subprocess.run(['schtasks','/Create','/SC','MINUTE','/MO','10','/TN',task,'/TR',cmd,'/F'],capture_output=True,text=True)
print('register_rc=',r.returncode)
print('register_stdout=',r.stdout.strip()[:300])
print('register_stderr=',r.stderr.strip()[:300])
if r.returncode:raise SystemExit(r.returncode)
q=subprocess.run(['schtasks','/Query','/TN',task,'/FO','LIST','/V'],capture_output=True,text=True)
for line in q.stdout.splitlines():
 if any(line.startswith(s) for s in ['TaskName:','Next Run Time:','Status:','Scheduled Task State:','Task To Run:','Schedule Type:']):
  print(line)
