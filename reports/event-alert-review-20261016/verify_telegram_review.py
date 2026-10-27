from pathlib import Path
import re,subprocess
root=Path(__file__).resolve().parent
node=r"C:\Program Files\nodejs\node.exe"
for reviewer in "AB":
    for phase in (1,2):
        p=root/f"CCWBot_Reviewer_{reviewer}_PHASE{phase}.html"
        content=p.read_text(encoding="utf-8")
        match=re.search(r"<script>([\s\S]+?)</script>",content)
        assert match,p
        script=root/"_review_tmp_script.js"
        script.write_text(match.group(1),encoding="utf-8")
        verify=subprocess.run([node,"--check",str(script)],capture_output=True,text=True)
        assert verify.returncode==0,verify.stderr
        import json
        items=json.loads(content.split("const ITEMS=",1)[1].split(";\nconst STORE=",1)[0])
        assert len(items)==(200 if phase==1 else 72)
        if phase==1:
            assert all("final_message" not in x and "should_alert" not in x
                       and "sampling_cohort" not in x for x in items)
        else:
            assert all(x.get("final_message") for x in items)
        assert "fetch(" not in content and "XMLHttpRequest" not in content
        print(p.name,"JS_SYNTAX=OK","NO_NETWORK=OK")
(root/"_review_tmp_script.js").unlink()
