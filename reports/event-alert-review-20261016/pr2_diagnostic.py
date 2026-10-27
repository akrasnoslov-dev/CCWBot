import json, pathlib, csv, collections
p=pathlib.Path(r'D:\Projects\CCWBot\reports\event-alert-review-20261016')
d=json.loads((p/'v2_private_sanitized.json').read_text(encoding='utf-8'))
print('DATASET top',list(d.keys()))
print('version',d.get('version'),'sha',d.get('dataset_sha256'),'count',len(d.get('cases',[])))
for c in d.get('cases',[])[:1]:
 print('CASE fields',list(c))
 print('INPUT fields',list(c.get('input',{})))
 print('OBSERVED fields',list(c.get('observed',{})))
 print('sample symbolic',c.get('symbol'),'scenario',c.get('scenario_type'))
for n in ['reviewer_A_phase1_significance.csv','reviewer_B_phase1_significance.csv','reviewer_A_phase2_final_message.csv','reviewer_B_phase2_final_message.csv']:
 with (p/n).open(encoding='utf-8-sig',newline='') as f:
  rows=list(csv.DictReader(f))
 print(n,'rows',len(rows),'fields',list(rows[0]) if rows else [],'warrant',dict(collections.Counter((x.get('warrant') or '').strip().lower() for x in rows)),'useful',dict(collections.Counter((x.get('useful') or '').strip().lower() for x in rows)),'factual',dict(collections.Counter((x.get('factual') or '').strip().lower() for x in rows)))
print('validation files',list((p/'validation').rglob('*.json'))[:12])
