"""Make two offline blind human-review packets, no production/prompt decisions embedded."""
import pathlib,hashlib,json
base=pathlib.Path(r"D:\Projects\CCWBot\reports\event-alert-review-20261016\ccw29_private")
src=(base/"make_owner_blind_html.py").read_text(encoding="utf-8")
src=src.replace('fresh_holdout")','fresh200_unseen")')
src=src.replace('holdout_20_blind_packet_PRIVATE.json','fresh200_blind_packet_PRIVATE.json')
src=src.replace('len(packet["cases"])==20 and packet["dataset_sha256"]=="cb087b1a52e32b48f96dabda9d9dbf72744fcdb37c273a906572567005fef873"',
 'len(packet["cases"])==200 and packet["dataset_sha256"]=="ad06de5fac921c8d0db46f9ab086bed470733df62670bcda5c96d0479c837f7d"')
src=src.replace('20 New Market Cases','200 New Market Cases')
src=src.replace('20 fresh real-market cases','200 fresh real-market cases')
src=src.replace('ccw29_owner_blind_review_20.json','ccw29_blind_review_200.json')
src=src.replace('out=F/"CCW29_OWNER_BLIND_REVIEW.html"\nout.write_text(htmltext,encoding="utf-8")\nprint(json.dumps({"file":str(out),"bytes":out.stat().st_size,"sha256":hashlib.sha256(out.read_bytes()).hexdigest(),"cases":len(packet["cases"]),"provider_outputs_included":False,"production_labels_included":False}))',
 '''for reviewer in ("A","B"):
 role="independent_human_reviewer_"+reviewer
 page=htmltext.replace('reviewer_id:"independent_owner_review"', 'reviewer_id:"'+role+'"')
 page=page.replace('ccw29_blind_review_200.json','ccw29_blind_review_'+reviewer+'_200.json')
 out=F/("CCW29_BLIND_REVIEW_"+reviewer+"_200.html")
 out.write_text(page,encoding="utf-8")
 print(json.dumps({"file":str(out),"bytes":out.stat().st_size,"sha256":hashlib.sha256(out.read_bytes()).hexdigest(),"cases":len(packet["cases"]),"provider_outputs_included":False,"production_labels_included":False}))
''')
assert "CCW29_BLIND_REVIEW_" in src
exec(compile(src,"<adapted_blind_html_generator>","exec"))
