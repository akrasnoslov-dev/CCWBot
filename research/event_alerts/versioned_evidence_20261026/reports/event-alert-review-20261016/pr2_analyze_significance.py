import collections, json, pathlib, statistics
p=pathlib.Path(r'D:\Projects\CCWBot\reports\event-alert-review-20261016')
cases=json.loads((p/'v2_private_sanitized.json').read_text(encoding='utf-8'))['cases']
for fn in ['reviewer_A_significance_for_pr1.json','reviewer_B_significance_for_pr1.json']:
 d=json.loads((p/fn).read_text(encoding='utf-8'))
 print(fn,'keys',list(d),'label fields',list(d['labels'][0]))
lab=[]
for fn in ['reviewer_A_significance_for_pr1.json','reviewer_B_significance_for_pr1.json']:
 d=json.loads((p/fn).read_text(encoding='utf-8')); lab.append({r['id']:r['warrant'] for r in d['labels']})
out=collections.defaultdict(list)
for c in cases:
 id=c['id']; a,b=(d.get(id) for d in lab)
 if a!=b or a=='ambiguous': continue
 observed=c['observed'].get('should_alert')
 name='TP' if a=='alert' and observed else 'FN' if a=='alert' else 'FP' if observed else 'TN'
 inp=c['input']; m=inp.get('market') or {}
 out[(c['symbol'],name)].append({
  'id':id, 'cw':m.get('chg_window_percent'), 'c24':m.get('chg24h_percent'),
  'w':m.get('analysed_window_minutes'), 'news':len(inp.get('news') or []),
  'snap':len(m.get('snapshots') or []), 'pw':m.get('relative_window_percentile_30d'),
  'short30':m.get('chg30m_percent'), 'short60':m.get('chg1h_percent'),
  'count':inp.get('recent_event_counts'), 'prev': bool(inp.get('previous_event_alert'))
 })
for symbol in ['BTC','ETH','GRAM','SOL']:
 for label in ['TP','FP','FN','TN']:
  v=out[(symbol,label)]
  if not v: continue
  print(symbol,label,'n',len(v),'moves',[round(float(x['cw']),4) for x in v][:17],
    'news',sum(x['news']>0 for x in v),'prev',sum(x['prev'] for x in v),
    'missing_pw',sum(x['pw'] is None for x in v),
    'missing_short',sum(x['short30'] is None and x['short60'] is None for x in v),
    'snap_min',min(x['snap'] for x in v),'snap_max',max(x['snap'] for x in v))
