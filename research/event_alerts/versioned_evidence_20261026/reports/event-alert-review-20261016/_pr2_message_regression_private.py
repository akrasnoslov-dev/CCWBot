"""Add focused market-copy regression tests first, then safe patch; no production changes."""
from pathlib import Path
import subprocess,sys,os
root=Path(__file__).resolve().parents[2]
test=root/'tests/test_event_alert_message_quality.py'
src=root/'bot/alerting/event_text.py'
suffix='''


def test_mismatched_snapshot_path_cannot_claim_persistent_primary_move():
    market = {
        "chg_window_percent": Decimal("-3"),
        "chg24h_percent": Decimal("-4"),
        "snapshots": [
            {"m": -120, "p": Decimal("100")},
            {"m": -60, "p": Decimal("102")},
            {"m": 0, "p": Decimal("104")},
        ],
    }
    situation, _ = event_alert_presentation_fallback(market, [])
    assert "persistent" not in situation.lower()
    assert "24-hour" in situation

    llm_text = compact_event_alert_situation(
        "The supplied snapshots show persistent short-term weakness aligned with the broader 24-hour direction.",
        significance_reason=None, market_data=market, related_news=[],
    )
    assert "persistent" not in llm_text.lower()


def test_latest_reversal_aligned_with_primary_does_not_claim_move_fading():
    market = {
        "chg_window_percent": Decimal("-2"),
        "chg24h_percent": Decimal("-4"),
        "snapshots": [
            {"m": -120, "p": Decimal("100")},
            {"m": -60, "p": Decimal("105")},
            {"m": 0, "p": Decimal("101")},
        ],
    }
    situation, _ = event_alert_presentation_fallback(market, [])
    assert "reverses part of the earlier path" in situation
    assert "fading" not in situation
    assert "aligns with the analysed-window direction" in situation
'''
original_test=test.read_text(encoding='utf-8')
if "test_mismatched_snapshot_path_cannot_claim_persistent_primary_move" not in original_test:
    test.write_text(original_test+suffix,encoding='utf-8')
env=os.environ.copy()
env['PYTHON_DOTENV_DISABLED']='1'
cmd=[sys.executable,'-m','pytest','-q','tests/test_event_alert_message_quality.py','-k','mismatched_snapshot_path or latest_reversal_aligned']
pre=subprocess.run(cmd,cwd=root,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
print('PRE_FIX_EXIT:',pre.returncode,pre.stdout[-1900:],flush=True)
if pre.returncode==0:
    raise RuntimeError("Expected regression failures were not reproduced; implementation unchanged")
text=src.read_text(encoding='utf-8')
old='    has_persistence = _has_persistent_snapshot_direction(step_changes)'
new='''    has_persistence = (
        _has_persistent_snapshot_direction(step_changes)
        and window_change is not None
        and window_change != 0
        and (step_changes[-1] > 0) == (window_change > 0)
    )'''
count=text.count(old)
if count != 2: raise RuntimeError(f'Unexpected persistence sites: {count}')
text=text.replace(old,new)
needle='''    if len(step_changes) >= 2 and step_changes[-1] * step_changes[-2] < 0:
        return (
            "The most recent supplied snapshot reverses part of the earlier path, so the "'''
replacement='''    if len(step_changes) >= 2 and step_changes[-1] * step_changes[-2] < 0:
        if (
            window_change is not None
            and window_change != 0
            and (step_changes[-1] > 0) == (window_change > 0)
        ):
            return (
                "The most recent supplied snapshot reverses part of the earlier path, "
                "but the latest step aligns with the analysed-window direction.",
                "Watch the next short-term snapshots for continuation in that direction "
                "versus another counter-move.",
            )
        return (
            "The most recent supplied snapshot reverses part of the earlier path, so the "'''
if text.count(needle)!=1: raise RuntimeError('Expected counter-move branch not found')
text=text.replace(needle,replacement)
src.write_text(text,encoding='utf-8')
for label,command in [
 ('FOCUSED', [sys.executable,'-m','pytest','-q','tests/test_event_alert_message_quality.py']),
 ('RUFF', [sys.executable,'-m','ruff','check','bot/alerting/event_text.py','tests/test_event_alert_message_quality.py']),
]:
 p=subprocess.run(command,cwd=root,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
 print(label,'EXIT',p.returncode,p.stdout[-3500:],flush=True)
 if p.returncode: raise RuntimeError(label+' did not pass')
print('PATCH_TESTED_NOT_COMMITTED',flush=True)
