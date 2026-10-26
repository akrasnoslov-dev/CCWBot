import json
from pathlib import Path
p=Path(r'D:\Projects\CCWBot\reports\event-alert-review-20261016')
for name in ['reviewer_A_significance_for_pr1.json','owner_A_cli_scoring_private.json','reviewer_A_phase1_significance.csv','unresolved_human_disagreements_private.json']:
    path=p/name
    if path.suffix=='.json':
        data=json.loads(path.read_text(encoding='utf-8-sig'))
        print(name, 'root:',list(data.keys())[:15] if isinstance(data,dict) else type(data).__name__)
        for key in ['labels','answers','conflicts']:
            if isinstance(data,dict) and isinstance(data.get(key),list):
                print(' ',key,'count',len(data[key]),'first_fields',list(data[key][0].keys()))
                print(' ',key,'first_sample_types',{k:type(v).__name__ for k,v in data[key][0].items()})
    else:
        import csv
        with path.open(encoding='utf-8-sig') as f:
            rdr=csv.DictReader(f)
            print(name,'fields',rdr.fieldnames)
c=json.loads((p/'ccw41_private/reviewer_c_sealed.json').read_text(encoding='utf-8'))
print('Reviewer C result keys',list(c['results'][0].keys()))
print('C first case reason',c['results'][0].get('rationale','')[:250])
print('Previously A/B survey HTML size', (p/'telegram_review/CCWBot_RECONCILE_99.html').stat().st_size)
