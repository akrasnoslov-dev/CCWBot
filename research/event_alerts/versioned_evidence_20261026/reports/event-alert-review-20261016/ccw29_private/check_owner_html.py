"""Quick syntax and blind-payload integrity check for standalone owner form."""
from html.parser import HTMLParser
import pathlib,json,subprocess,hashlib
file=pathlib.Path(r"D:\Projects\CCWBot\reports\event-alert-review-20261016\ccw29_private\fresh_holdout\CCW29_OWNER_BLIND_REVIEW.html")
class P(HTMLParser):
 def __init__(self):super().__init__();self.in_script=False;self.scripts=[];self.attr=None
 def handle_starttag(self,tag,attrs):
  if tag=="script":self.in_script=True;self.scripts.append([])
 def handle_endtag(self,tag):
  if tag=="script":self.in_script=False
 def handle_data(self,text):
  if self.in_script:self.scripts[-1].append(text)
p=P();p.feed(file.read_text(encoding="utf-8"))
assert len(p.scripts)==2
packet=json.loads("".join(p.scripts[0]))
assert packet["dataset_sha256"]=="cb087b1a52e32b48f96dabda9d9dbf72744fcdb37c273a906572567005fef873" and len(packet["cases"])==20
assert all("observed" not in c and "decision" not in c for c in packet["cases"])
test=subprocess.run(["node","--check"],input="".join(p.scripts[1]),text=True,capture_output=True,timeout=15)
print(json.dumps({"owner_html_exists":True,"source_only":True,"case_count":len(packet["cases"]),"js_syntax_check":test.returncode==0,"html_sha256":hashlib.sha256(file.read_bytes()).hexdigest()}))
if test.returncode:print("CHECK_FAILED",test.stderr[-500:]);raise SystemExit(1)
