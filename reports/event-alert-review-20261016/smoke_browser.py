from pathlib import Path
import subprocess,tempfile
root=Path(__file__).resolve().parent
edge=Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe")
assert edge.exists()
for fname,needle in [
    ("CCWBot_Reviewer_A_PHASE1.html","Ситуация 1 из 200"),
    ("CCWBot_Reviewer_B_PHASE2.html","Ситуация 1 из 72")]:
    with tempfile.TemporaryDirectory(prefix="ccwbot-browser-smoke-") as user_data:
        cmd=[str(edge),"--headless=new","--disable-gpu","--no-first-run",
             "--no-default-browser-check","--user-data-dir="+user_data,
             "--virtual-time-budget=3500","--dump-dom",(root/fname).as_uri()]
        result=subprocess.run(cmd,capture_output=True,text=True,encoding="utf-8",
                              errors="replace",timeout=40)
        text=result.stdout
        assert needle in text, (fname,result.returncode,text[-500:],result.stderr[-500:])
        assert "CCWBot" in text and "Скачать мои ответы" in text
        print(fname, "BROWSER_RENDER=OK", "NEEDLE=",needle)
print("SMOKE_PASS")
