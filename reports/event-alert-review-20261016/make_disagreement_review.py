"""Make an optional blinded, human-only disagreement resolution page."""
from pathlib import Path
import json

root=Path(__file__).resolve().parent
target=root/"telegram_review"
original=(target/"CCWBot_Reviewer_A_PHASE1.html").read_text(encoding="utf-8")
before,tail=original.split("const ITEMS=",1)
embedded,after=tail.split(";\nconst STORE=",1)
all_cards=json.loads(embedded)
conf=json.loads((root/"unresolved_human_disagreements_private.json").read_text(encoding="utf-8"))
lookup={x["id"]:x for x in conf["conflicts"]}
cards=[{**c,"voteA":lookup[c["id"]]["reviewer_A"],"voteB":lookup[c["id"]]["reviewer_B"]}
       for c in all_cards if c["id"] in lookup]
assert len(cards)==99
text=before+"const ITEMS="+json.dumps(cards,ensure_ascii=False).replace("</","<\\/")+";\nconst STORE="+after
text=text.replace('REVIEWER="A"','REVIEWER="R"')
text=text.replace(
 'html=\'<div class="question">Вы хотели бы получить такое уведомление?</div>\';',
 'html=\'<div class="question">Какое итоговое решение после обсуждения?</div><div class="notice">Оценщик A: <b>\'+e(ITEMS[current].voteA)+\'</b>. Оценщик B: <b>\'+e(ITEMS[current].voteB)+\'</b>. Оригинальное решение бота скрыто.</div>\';'
)
text=text.replace(
 '"Перед вами реальные рыночные ситуации, оформленные как Telegram-уведомления. Это НЕ обязательно отправленные алерты: ответ бота скрыт. Просто решите, хотели бы вы получить уведомление о таком движении."',
 '"Ваши первые оценки разошлись в 99 случаях. Просмотрите только их и примите совместное окончательное решение. Оригинальные ответы бота здесь не показаны. При отсутствии согласия выберите «Не уверен»."'
)
text=text.replace('REVIEWER==="A"?"A · вы":"B · друг"',
                  'REVIEWER==="R"?"совместное согласование":REVIEWER==="A"?"A · вы":"B · друг"')
text=text.replace('"Нужен ли такой алерт?"','"Согласование спорных событий"')
text=text.replace('"Этап 1 · значимость"','"Дополнительный этап · разногласия"')
text=text.replace(
 'return PHASE===1?["alert","no_alert","ambiguous"].includes(a.warrant):(typeof a.useful==="boolean");',
 'return PHASE===1?["alert","no_alert","ambiguous"].includes(a.warrant):(typeof a.useful==="boolean");'
)
path=target/"CCWBot_RECONCILE_99.html"
path.write_text(text,encoding="utf-8")
print("FILE",path.name,"CASES",len(cards),"BYTES",path.stat().st_size)
