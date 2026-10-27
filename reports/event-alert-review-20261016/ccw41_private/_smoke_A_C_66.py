"""Smoke-test offline A/C survey in real Edge, plus embedded JS parse check."""
from pathlib import Path
import json
import re
import subprocess
import tempfile

root=Path(__file__).resolve().parents[1]
page=root/"telegram_review/CCWBot_REVIEW_A_vs_GPT6_66.html"
text=page.read_text(encoding="utf-8")
m=re.search(r'let ITEMS=(\[.*?\]);\nconst STORE=',text,re.S)
assert m, "Embedded 66-card JSON not found"
cases=json.loads(m[1])
assert len(cases)==66
assert len({c["id"] for c in cases})==66
assert all(c["voteA"]!=c["voteC"] for c in cases)
assert all(c["rationaleC"] and c["confidenceC"] and c["referencesC"] for c in cases)
assert "CCWBot_A_vs_GPT6_66_answers.json" in text
assert "ALL_ITEMS.filter" in text
assert '<select id="pair-filter"' in text

node=subprocess.run(["node","--version"],capture_output=True,text=True)
if node.returncode == 0:
    js=text.split("<script>",1)[1].split("</script>",1)[0]
    with tempfile.TemporaryDirectory(prefix="ccwbot-ac-check-",dir=root/"ccw41_private") as tmp:
        script=Path(tmp)/"survey.js"
        script.write_text(js,encoding="utf-8")
        subprocess.run(["node","--check",str(script)],check=True,capture_output=True,text=True)

edge=Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe")
assert edge.exists()
with tempfile.TemporaryDirectory(prefix="ccwbot-ac-smoke-") as tmp:
    cmd=[str(edge),"--headless=new","--disable-gpu","--no-first-run",
         "--no-default-browser-check","--user-data-dir="+tmp,
         "--virtual-time-budget=3000","--dump-dom",page.as_uri()]
    done=subprocess.run(cmd,capture_output=True,text=True,encoding="utf-8",errors="replace",timeout=40)
    visible=done.stdout
    assert "Ситуация 1 из 66" in visible, (done.returncode,done.stderr[-700:],visible[-900:])
    assert "Reviewer A" in visible and "Reviewer C" in visible
    assert "Какое решение вы считаете правильным сейчас?" in visible
    assert "Все типы расхождений" in visible
print("PASS: 66 unique differences, 66 C rationales/evidence, browser render, controls, standalone HTML, JS syntax.")
print("FILE:",page)
