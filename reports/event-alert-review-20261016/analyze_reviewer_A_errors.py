import json,sys,collections,statistics
from pathlib import Path
r=Path(__file__).resolve().parents[2];sys.path.insert(0,str(r))
from scripts.event_alert_benchmark import load_frozen
p=Path(__file__).resolve().parent
d=load_frozen(p/'v2_private_sanitized.json')
a={x['id']:x for x in json.loads((p/'reviewer_A_significance_for_pr1.json').read_text(encoding='utf-8'))['labels']}
def prop(case):return case['input']['market']
def result(c):
  label=a[c['id']]['warrant']; pred=c['observed'].get('should_alert')
  return 'AMB' if label=='ambiguous' else 'FP' if pred is True and label=='no_alert' else 'FN' if pred is False and label=='alert' else 'TP' if pred is True and label=='alert' else 'TN' if pred is False and label=='no_alert' else 'NA'
for k in ('input','observed'):print('TEMPLATE_'+k,sorted(d['cases'][0][k]))
print('MARKET_KEYS',sorted(prop(d['cases'][0])))
print('ALL_OUTCOMES',dict(collections.Counter(result(x) for x in d['cases'])))
for symbol in sorted(set(c['symbol'] for c in d['cases'])):
 print('\n',symbol)
 cases=[c for c in d['cases'] if c['symbol']==symbol]
 for outcome in ('FP','FN','TP','TN'):
  grp=[x for x in cases if result(x)==outcome];absw=[abs(float(prop(x)['chg_window_percent'])) for x in grp]
  print(outcome,'count',len(grp),'move_abs_median',round(statistics.median(absw),3) if absw else None,
   'min',round(min(absw),3) if absw else None,'max',round(max(absw),3) if absw else None,
   'day_percentiles',dict(collections.Counter(str(prop(x).get('relative_window_percentile_30d')) for x in grp).most_common(6)),
   'h30missing',sum(prop(x).get('chg30m_percent') is None for x in grp),
   'prev',sum(bool(x['input'].get('previous_event_alert')) for x in grp),
   'news',sum(bool(x['input'].get('news')) for x in grp))
print('\nA_LABELS',dict(collections.Counter(x['warrant'] for x in a.values())))
for outcome in ('FP','FN'):
 print('\n'+outcome+' cases with market-only facts (id omitted)')
 for c in [c for c in d['cases'] if result(c)==outcome][:15]:
  m=prop(c); prev=c['input'].get('previous_event_alert') or {}; cnt=c['input'].get('recent_event_counts') or {}
  print(c['symbol'],'w',m['analysed_window_minutes'],'cw',round(float(m['chg_window_percent']),3),'c24',m.get('chg24h_percent'),'c30',m.get('chg30m_percent'),'c60',m.get('chg1h_percent'),
       'pct30d',m.get('relative_window_percentile_30d'),'prev',bool(prev),'counts',cnt,'snap',len(m['snapshots']))
