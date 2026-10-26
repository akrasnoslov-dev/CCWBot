import json, statistics, collections
from pathlib import Path
p=Path(__file__).resolve().parent
cases=json.loads((p/'v2_private_sanitized.json').read_text(encoding='utf-8'))['cases']
labels={x['id']:x['warrant'] for x in json.loads((p/'reviewer_A_significance_for_pr1.json').read_text(encoding='utf-8'))['labels']}
state=json.loads((p/'live_groq_ab_20261016/replay_state.json').read_text(encoding='utf-8'))
rows={v:{i['id']:i for i in l} for v,l in state['runs'].items()}
paired=[c for c in cases if labels[c['id']]!='ambiguous' and all(c['id'] in rows[v] for v in ('production','materiality_first'))]
print('paired',len(paired))
for var in ('production','materiality_first'):
 print('VARIANT',var)
 groups=collections.defaultdict(list)
 for c in paired:
  r=rows[var][c['id']]
  lab=labels[c['id']]
  cat='TP' if r.get('should_alert') and lab=='alert' else 'FP' if r.get('should_alert') else 'FN' if lab=='alert' else 'TN'
  groups[(cat,r.get('materiality'),r.get('novelty'),r.get('reason_code'))].append(c)
 for k,cs in sorted(groups.items(),key=lambda it:(it[0][0],it[0][1] or '')):
  moves=[abs(float(x['input']['market']['chg_window_percent'])) for x in cs]
  print(k,'n',len(cs),'median_abs_3h',round(statistics.median(moves),3),'symbols',dict(collections.Counter(x['symbol'] for x in cs)))
print('CHANGES')
for c in paired:
 a=rows['production'][c['id']];b=rows['materiality_first'][c['id']]
 if a['should_alert']!=b['should_alert']:
  print(c['symbol'],labels[c['id']],round(float(c['input']['market']['chg_window_percent']),3),'p30',c['input']['market'].get('relative_window_percentile_30d'),'prod',a['materiality'],a['novelty'],'candidate',b['materiality'],b['novelty'])
