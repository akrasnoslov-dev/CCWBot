"""Continue the already-started screen without overlapping inference models."""
import json
from pathlib import Path
import socket
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parent
if __name__=='__main__':
 deadline=time.monotonic()+1800
 while True:
  data=json.loads((ROOT/'qwen4.results.json').read_text())
  if len(data['rows'])==34:break
  if time.monotonic()>deadline:raise RuntimeError('initial Qwen4 pass did not finish')
  time.sleep(2)
 for _ in range(30):
  try:
   with socket.create_connection(('127.0.0.1',18725),timeout=1):pass
   time.sleep(1)
  except OSError:break
 else:raise RuntimeError('benchmark port still in use')
 for args in [['--model','qwen4','--case-filter','long_'],['--model','phi'],['--model','qwen7']]:
  print('starting',args,flush=True)
  subprocess.run([sys.executable,str(ROOT/'benchmark.py'),'run','--repeats','1',*args],check=True)
 subprocess.run([sys.executable,str(ROOT/'benchmark.py'),'summary'],check=True)
