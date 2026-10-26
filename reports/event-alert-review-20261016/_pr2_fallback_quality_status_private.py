import json
from pathlib import Path
from collections import Counter
from scripts.event_alert_benchmark import load_frozen
from scripts.live_event_significance_benchmark import load_reviewer_a, maximum_possible_quality
p=Path('reports/event-alert-review-20261016')
dataset=load_frozen(p/'v2_private_sanitized.json')
labels=load_reviewer_a(p/'reviewer_A_significance_for_pr1.json',dataset)
for location in sorted((p/'merged_pilots_private').glob('fallback_*/replay_state.json')) + [p/'merged_pilots_private/replay_state.json']:
 if not location.exists():continue
 state=json.loads(location.read_text())
 for name,rows in state['runs'].items():
  if location.name=='replay_state.json' and location.parent.name=='merged_pilots_private' and name!='path_facts':continue
  counts=Counter(r['status'] for r in rows)
  matrix=Counter()
  for row in rows:
   if row['status']!='valid' or labels[row['id']]=='ambiguous':continue
   matrix['TP' if row['should_alert'] and labels[row['id']]=='alert' else 'FP' if row['should_alert'] else 'FN' if labels[row['id']]=='alert' else 'TN']+=1
  quality=maximum_possible_quality(dataset,labels,state,name)
  print(json.dumps(dict(run=location.parent.name,variant=name,attempts=state['attempted_requests'],counts=counts,confusion=matrix,best_case=quality),default=dict))
