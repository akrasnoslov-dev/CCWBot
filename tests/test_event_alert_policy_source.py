from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_event_alert_runtime_has_no_numeric_significance_gate_or_similarity_bucket():
    alerts = (ROOT / "bot" / "alerts.py").read_text(encoding="utf-8")
    identity = (ROOT / "bot" / "alerting" / "event_identity.py").read_text(encoding="utf-8")
    assert "evaluate_event_significance" not in alerts
    assert "event_significance" not in alerts
    assert "movement_bucket" not in identity
    assert "MATERIAL_MOVEMENT" not in identity


def test_event_alert_uses_exact_context_and_full_coingecko_precision():
    alerts = (ROOT / "bot" / "alerts.py").read_text(encoding="utf-8")
    price_service = (ROOT / "bot" / "services" / "price_service.py").read_text(encoding="utf-8")
    assert "_build_exact_event_context_fingerprint" in alerts
    assert '"precision": "full"' in price_service
    assert "parse_float=Decimal" in price_service
