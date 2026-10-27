"""Owner-approved, local-only pinned benchmark dependencies."""
import concurrent.futures
import hashlib
import json
import urllib.request
import zipfile
from pathlib import Path

ROOT=Path('reports/ccw25-20261019')
FILES=[
 ('llama-b11734-bin-win-cpu-x64.zip','https://github.com/ggml-org/llama.cpp/releases/download/b11734/llama-b11734-bin-win-cpu-x64.zip','bd6a8a8cb9d6ba115de3519d401f91dd5295b333243db44b6b8a3ce5e53ff8da'),
 ('Qwen3-4B-Instruct-2507-Q4_K_M.gguf','https://huggingface.co/unsloth/Qwen3-4B-Instruct-2507-GGUF/resolve/a06e946bb6b655725eafa393f4a9745d460374c9/Qwen3-4B-Instruct-2507-Q4_K_M.gguf','3605803b982cb64aead44f6c1b2ae36e3acdb41d8e46c8a94c6533bc4c67e597'),
 ('microsoft_Phi-4-mini-instruct-Q4_K_M.gguf','https://huggingface.co/bartowski/microsoft_Phi-4-mini-instruct-GGUF/resolve/7ff82c2aaa4dde30121698a973765f39be5288c0/microsoft_Phi-4-mini-instruct-Q4_K_M.gguf','01999f17c39cc3074afae5e9c539bc82d45f2dd7faa3917c66cbef76fce8c0c2'),
 ('qwen2.5-7b-instruct-q4_k_m-00001-of-00002.gguf','https://huggingface.co/Qwen/Qwen2.5-7B-Instruct-GGUF/resolve/bb5d59e06d9551d752d08b292a50eb208b07ab1f/qwen2.5-7b-instruct-q4_k_m-00001-of-00002.gguf','dfce12e3862a5283ccfb88221b48480e58745165de856439950d0f22590580db'),
 ('qwen2.5-7b-instruct-q4_k_m-00002-of-00002.gguf','https://huggingface.co/Qwen/Qwen2.5-7B-Instruct-GGUF/resolve/bb5d59e06d9551d752d08b292a50eb208b07ab1f/qwen2.5-7b-instruct-q4_k_m-00002-of-00002.gguf','539cf93f78e887edea1c04e2d7d8cdaca9d01dae9c9025bcb8accbe29df3d72a'),
]
def fetch(item):
 name,url,want=item
 path=ROOT/'models'/name
 if not path.exists():
  temp=path.with_suffix(path.suffix+'.part')
  print('downloading',name,flush=True)
  with urllib.request.urlopen(url,timeout=60) as response,temp.open('wb') as output:
   while block:=response.read(8*1024*1024): output.write(block)
  temp.rename(path)
 sha=hashlib.file_digest(path.open('rb'),'sha256').hexdigest()
 if sha!=want: raise RuntimeError('checksum mismatch: '+name)
 print('verified',name,path.stat().st_size,flush=True)
 return {'file':name,'url':url,'sha256':sha,'bytes':path.stat().st_size}

if __name__=='__main__':
 (ROOT/'models').mkdir(parents=True,exist_ok=True)
 with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
  result=list(pool.map(fetch,FILES))
 (ROOT/'artifact_manifest.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
 dest=(ROOT/'runtime').resolve()
 if not (dest/'llama-server.exe').exists():
  with zipfile.ZipFile(ROOT/'models'/FILES[0][0]) as archive:
   if not all((dest/n).resolve().is_relative_to(dest) for n in archive.namelist()):
    raise RuntimeError('unsafe archive member')
   archive.extractall(dest)
 print('all downloads verified',flush=True)
