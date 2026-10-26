from pathlib import Path
import os,json
from dotenv import load_dotenv
from openai import OpenAI
from bot.services import ai_agent_groq
from bot.services.llm import config
load_dotenv(Path(__file__).resolve().parents[2]/'.env')
model='qwen/qwen3.8-27b'
effort=config.reasoning_effort_for(model,'event_analysis')
max_tokens=config.effective_max_tokens_for(call_type='event_analysis',provider='groq',model=model)
print('config','model',model,'effort',effort,'max_tokens',max_tokens)
client=OpenAI(api_key=os.environ['GROQ_API_KEY'],base_url='https://api.groq.com/openai/v1',max_retries=0,timeout=20)
options={'model':model,'messages':[{'role':'system','content':ai_agent_groq.SYSTEM_PROMPT},{'role':'user','content':'JSON English. For symbol BTC with routine price changes, choose no alert. Return exactly symbol,materiality,novelty,should_alert,reason_code,confidence.'}],'response_format':{'type':'json_schema','json_schema':{'name':'event_significance','strict':True,'schema':ai_agent_groq._EVENT_SIGNIFICANCE_JSON_SCHEMA}},'max_tokens':max_tokens,'temperature':0.0}
if effort is not None: options['reasoning_effort']=effort
try:
 response=client.chat.completions.create(**options)
 print('status','valid_http','usage',response.usage.total_tokens if response.usage else None,'content_is_json',bool(response.choices[0].message.content))
except Exception as exc:
 print('ERROR',type(exc).__name__,'http_status',getattr(exc,'status_code',None))
 body=getattr(exc,'body',None)
 err=body.get('error',body) if isinstance(body,dict) else {}
 if isinstance(err,dict):
  print('code',str(err.get('code'))[:80],'type',str(err.get('type'))[:80])
  print('message_category',[(k,k in str(err.get('message','')).lower()) for k in ('reasoning','effort','schema','temperature','model','max_tokens','unsupported','strict','plan','not allowed','invalid')])
  print('message_sanitized',str(err.get('message',''))[:450])
