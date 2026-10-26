import json,pathlib,statistics,collections
p=pathlib.Path(__file__).resolve().parent
d=json.loads((p/'v2_private_sanitized.json').read_text(encoding='utf8'))
labels={row['id']:row['warrant'] for row in json.loads((p/'reviewer_A_significance_for_pr1.json').read_text(encoding='utf8'))['labels']}
s=json.loads((p/'merged_pilots_private/replay_state.json').read_text(encoding='utf8'))
by={v:{row['id']:row for row in values if row['status']=='valid'} for v,values in s['runs'].items()}
for case in d['cases']:
 id=case['id']
 if id not in by['relative_displacement'] or id not in by['production'] or labels[id]=='ambiguous':continue
 a=by['relative_displacement'][id]['should_alert'];truth=labels[id]=='alert'
 cat='TP' if a and truth else 'FP' if a else 'FN' if truth else 'TN'
 m=case['input']['market'];prev=case['input'].get('previous_event_alert') or {}
 print(cat,case['symbol'],'window',round(m['chg_window_percent'],3),'pctile',m.get('relative_window_percentile_30d'),'previous_fam',str(prev.get('semantic_family',''))[:19],'prev_cw',prev.get('analysed_window_move'),'news?',bool(case['input'].get('news')),'history',str(case['input'].get('recent_event_counts'))[:37],'prod',by['production'][id]['should_alert'])
