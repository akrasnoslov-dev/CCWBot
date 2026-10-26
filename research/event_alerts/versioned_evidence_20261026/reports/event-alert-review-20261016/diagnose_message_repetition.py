from pathlib import Path
from collections import Counter
import json,re
p=Path(r"D:\Projects\CCWBot\reports\event-alert-review-20261016\v2_private_sanitized.json")
cases=json.loads(p.read_text(encoding="utf-8"))["cases"]
delivered=[c for c in cases if c["observed"].get("final_message")]
situations=Counter();actions=Counter();missing=Counter()
for c in delivered:
    message=c["observed"]["final_message"]
    for name,pattern,target in [
        ("situation",r"(?is)\bSituation:\s*(.*?)\s*(?:(?:\bRelated context:)|(?:\bPossible action:)|(?:\bNot financial advice\.))",situations),
        ("action",r"(?is)\bPossible action:\s*(.*?)\s*(?:\bNot financial advice\.)",actions)]:
        hit=re.search(pattern,message)
        if hit:
            clean=" ".join(hit.group(1).lower().split())
            clean=re.sub(r"\b(?:btc|eth|sol|gram|bitcoin|ethereum|solana)\b","COIN",clean)
            target[clean]+=1
        else:missing[name]+=1
print("MESSAGES",len(delivered),"UNIQUE_SITUATION",len(situations),"UNIQUE_ACTION",len(actions),"MISSING",dict(missing))
print("ACTION_REPEATS",[{"count":n,"phrase":k[:170]} for k,n in actions.most_common(12) if n>1])
print("SITUATION_REPEATS",[{"count":n,"phrase":k[:170]} for k,n in situations.most_common(8) if n>1])
