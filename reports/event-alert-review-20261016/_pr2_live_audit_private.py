import json
from pathlib import Path
from collections import Counter
root=Path(__file__).parent
p=root/'merged_pilots_private'
state=json.loads((p/'replay_state.json').read_text(encoding='utf-8'))
ref=json.loads((root/'reviewer_A_significance_for_pr1.json').read_text(encoding='utf-8'))
print('REFERENCE TOP KEYS:', list(ref))
labels=ref.get('labels',[])
print('LABEL SAMPLE STRUCTURE:', list(labels[0]) if isinstance(labels,list) and labels else list(labels)[:5])
if isinstance(labels,list): labels={x['id']:x['warrant'] for x in labels}
else: labels={k:(v.get('warrant') if isinstance(v,dict) else v) for k,v in labels.items()}
print('REFERENCE COUNTS:', dict(Counter(labels.values())))
print('ATTEMPTS:',state['attempted_requests'],'CANDIDATE SCORES:')
for name,rows in state['runs'].items():
 v=[r for r in rows if r.get('status')=='valid' and labels.get(r.get('id')) in ('alert','no_alert')]
 c=Counter((labels[r['id']],r['should_alert']) for r in v)
 attempts=sum(r.get('provider_attempts',0) for r in rows)
 tokens=sum(r.get('total_tokens',0) for r in rows)
 total_pos=sum(v=='alert' for v in labels.values())
 tp,fp,fn,tn=c[('alert',True)],c[('no_alert',True)],c[('alert',False)],c[('no_alert',False)]
 print(name,'rows',len(rows),'valid',len(v),'TP',tp,'FP',fp,'FN',fn,'TN',tn,'precision',round(tp/(tp+fp),3) if tp+fp else None,'recall_seen',round(tp/(tp+fn),3) if tp+fn else None,'provider_attempts',attempts,'tokens',tokens,'statuses',dict(Counter(r.get('status') for r in rows)))
print('REPLAY KEYS:', list(state))
