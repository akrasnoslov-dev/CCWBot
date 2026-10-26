from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED
root=Path(__file__).resolve().parent
for reviewer in ("A","B"):
    for phase,suffix in ((1,"phase1_significance.csv"),(2,"phase2_final_message.csv")):
        path=root/("Reviewer_"+reviewer+"_PHASE"+str(phase)+"_private.zip")
        names=("reviewer_"+reviewer+"_"+suffix,"README_RU.md")
        with ZipFile(path,"w",ZIP_DEFLATED) as z:
            for name in names:z.write(root/name,arcname=name)
        with ZipFile(path,"r") as z:
            assert z.testzip() is None and set(z.namelist())==set(names)
        print(path.name,path.stat().st_size,"OK")
for reviewer in ("A","B"):
    old=root/("Reviewer_"+reviewer+"_private.zip")
    if old.exists(): old.unlink()
