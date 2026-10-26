import json, pathlib
from collections import Counter
p=pathlib.Path(__file__).resolve().parent
d=json.loads((p/'v2_private_sanitized.json').read_text(encoding='utf8'))
labels={x['id']:x['warrant'] for x in json.loads((p/'reviewer_A_significance_for_pr1.json').read_text(encoding='utf8'))['labels']}
s=json.loads((p/'merged_pilots_private/replay_state.json').read_text(encoding='utf8'))
model={x['id']:x for x in s['runs']['global_prior_safe']}
for c in d['cases']:
    x=model.get(c['id'])
    if x is None or labels[c['id']]=='ambiguous' or x['status']!='valid':continue
    pred=x['should_alert'];truth=labels[c['id']]=='alert'
    if pred==truth:continue
    market=c['input']['market']
    prev=c['input'].get('previous_event_alert') or {}
    counts=c['input'].get('recent_event_counts') or {}
    print('FP' if pred else 'FN',c['symbol'],'cw',round(market['chg_window_percent'],3),'pw',market.get('relative_window_percentile_30d'),
          'prev_family',prev.get('semantic_family'),'prev_cw',prev.get('analysed_window_move'),
          'prev_age',prev.get('age_minutes'),'cnt6',counts.get('h6'),'cnt24',counts.get('h24'),
          'news',len(c['input'].get('news') or []),'reason',x.get('reason_code'),'material',x.get('materiality'),'novelty',x.get('novelty'))
