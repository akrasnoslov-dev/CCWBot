from pathlib import Path
import os,json
from dotenv import load_dotenv
from openai import OpenAI
from bot.services import ai_agent_groq
from scripts.event_significance_candidates import candidate_prompt
from scripts.event_alert_benchmark import load_frozen
from scripts.live_event_significance_benchmark import load_reviewer_a,eligible_replay_cases
root=Path(__file__).resolve().parents[2]
load_dotenv(root/'.env')
dataset=load_frozen(root/'reports/event-alert-review-20261016/v2_private_sanitized.json')
labels=load_reviewer_a(root/'reports/event-alert-review-20261016/reviewer_A_significance_for_pr1.json',dataset)
case=next(iter(eligible_replay_cases(dataset,labels,excluded_case_ids=frozenset(),skip_ambiguous=True,screen_positives_first=True)))
model='qwen/qwen3.8-27b'
client=OpenAI(api_key=os.environ['GROQ_API_KEY'],base_url='https://api.groq.com/openai/v1',max_retries=0,timeout=25)
options={'model':model,'messages':[{'role':'system','content':ai_agent_groq.SYSTEM_PROMPT},{'role':'user','content':candidate_prompt(case['input'],'global_prior_no_family')}],'response_format':{'type':'json_schema','json_schema':{'name':'event_significance','strict':True,'schema':ai_agent_groq._EVENT_SIGNIFICANCE_JSON_SCHEMA}},'max_tokens':1200,'temperature':0.0}
try:
 r=client.chat.completions.create(**options)
 answer=json.loads(r.choices[0].message.content)
 print('STATUS','valid','total_tokens',r.usage.total_tokens if r.usage else None,'should_alert',answer.get('should_alert'))
except Exception as e:
 print('STATUS','error',type(e).__name__,'http',getattr(e,'status_code',None))
 body=getattr(e,'body',None); err=body.get('error',body) if isinstance(body,dict) else {}
 if isinstance(err,dict):
  print('ERROR_CODE',str(err.get('code'))[:60], 'MESSAGE',str(err.get('message',''))[:350])
