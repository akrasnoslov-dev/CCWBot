"""Safe capabilities check: metadata GET only, no private benchmark data."""
import os
import httpx
from pathlib import Path
from dotenv import load_dotenv
root=Path(__file__).resolve().parents[2]
load_dotenv(root/'.env')
checks=[
 ('groq','https://api.groq.com/openai/v1/models',
  {'Authorization':f"Bearer {os.getenv('GROQ_API_KEY','')}"},'openai/gpt-oss-120b'),
 ('gemini','https://generativelanguage.googleapis.com/v1beta/models',
  {'x-goog-api-key':os.getenv('GEMINI_API_KEY','')},'models/gemini-3.8-flash'),
]
for name,url,headers,model in checks:
 try:
  r=httpx.get(url,headers=headers,timeout=12)
  data=r.json() if r.is_success else {}
  rows=data.get('data',data.get('models',[]))
  names=[m.get('id',m.get('name')) for m in rows]
  print(name,'status',r.status_code,'configured_model_present',model in names,'model_count',len(rows))
  if name=='gemini' and model in names:
   m=next(x for x in rows if x.get('name')==model)
   print('gemini_supported_generateContent','generateContent' in m.get('supportedGenerationMethods',[]))
 except Exception as ex:
  print(name,'metadata_probe_failed',type(ex).__name__)
print('cloudflare_model_configured',bool(os.getenv('CLOUDFLARE_MODEL')),'cloudflare_key_configured',bool(os.getenv('CLOUDFLARE_API_TOKEN')))
