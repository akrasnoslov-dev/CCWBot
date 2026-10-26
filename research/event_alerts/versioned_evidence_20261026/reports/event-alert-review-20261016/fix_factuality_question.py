from pathlib import Path

root=Path(__file__).resolve().parent
source=root/"make_telegram_review.py"
text=source.read_text(encoding="utf-8")
patches=[
  ('(typeof a.useful==="boolean"&&typeof a.factual==="boolean")',
   '(typeof a.useful==="boolean")'),
  ('''  html+='<div class="question">Всё ли в тексте соответствует рыночным фактам?</div>';
  html+='<button class="choice '+(a.factual===true?"selected":"")+'" data-key="factual" data-value="true"><span class="circle">✓</span> Да, фактически верно</button>';
  html+='<button class="choice '+(a.factual===false?"selected":"")+'" data-key="factual" data-value="false"><span class="circle">×</span> Нет, есть ошибка</button>';''',
   '''  html+='<div class="question">Нашли ли вы очевидную фактическую ошибку?</div>';
  html+='<div class="muted">Это НЕ обязательная проверка. Без независимых данных нельзя подтвердить достоверность. Если вы не сверяли цифры и описание с рыночными фактами, оставьте «Не могу проверить». Для этого раскрывать дополнительные сведения необязательно.</div>';
  html+='<button class="choice '+(a.factual===false?"selected":"")+'" data-key="factual" data-value="false"><span class="circle">×</span> Да, могу указать конкретную ошибку</button>';
  html+='<button class="choice '+(a.factual===true?"selected":"")+'" data-key="factual" data-value="true"><span class="circle">✓</span> Проверил по данным — факты верны</button>';
  html+='<button class="choice '+(a.factual===undefined||a.factual===null?"selected":"")+'" data-key="factual" data-value="unknown"><span class="circle">?</span> Не могу проверить (по умолчанию)</button>';'''),
  ('"Если текст бесполезен или неверен, напишите почему (необязательно)"',
   '"Если вы обнаружили ошибку, укажите конкретное утверждение. Если не проверяли — комментарий не нужен."'),
  ('btn.dataset.value==="true"?true:btn.dataset.value==="false"?false:btn.dataset.value',
   'btn.dataset.value==="true"?true:btn.dataset.value==="false"?false:btn.dataset.value==="unknown"?null:btn.dataset.value'),
  ('const answers=ITEMS.filter((c,i)=>done(i)).map(c=>({id:c.id,...responses[c.id]}));',
   'const answers=ITEMS.filter((c,i)=>done(i)).map(c=>({id:c.id,...responses[c.id],...(PHASE===2?{factual:typeof responses[c.id]?.factual==="boolean"?responses[c.id].factual:null}:{})}));'),
  ('Оцените пользу и правдивость текста. Этот этап открывайте после завершения первого этапа ОБОИМИ оценщиками.',
   'Оцените пользу текста. Проверка фактов необязательна: выбирайте «Не могу проверить», если не сверяли утверждения с независимыми рыночными данными. Этот этап открывайте после завершения первого этапа ОБОИМИ оценщиками.'),
  ('Точки цены и новости доступны только для проверки контекста. Процентиль не является автоматическим порогом значимости.',
   'Точки цены и новости помогают оценить контекст, но не доказывают правдивость всех утверждений. Процентиль не является автоматическим порогом значимости.')
]
for old,new in patches:
    count=text.count(old)
    if count!=1:raise ValueError(f"Expected 1 occurrence; got {count} for {old[:100]!r}")
    text=text.replace(old,new)
source.write_text(text,encoding="utf-8")
converter=root/"convert_html_reviews.py"
c=converter.read_text(encoding="utf-8")
old='assert type(item.get("useful")) is bool and type(item.get("factual")) is bool, "Missing message scores"'
new='assert type(item.get("useful")) is bool and (item.get("factual") is None or type(item.get("factual")) is bool), "Missing usefulness score or invalid factuality status"'
if c.count(old)!=1:raise ValueError("Converter not found")
converter.write_text(c.replace(old,new),encoding="utf-8")
print("UPDATED_UI_GENERATOR_AND_CONVERTER")
