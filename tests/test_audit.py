import json

from app import audit


def test_record_audit_event_appends_jsonl(tmp_path, monkeypatch) -> None:
    audit_path = tmp_path / "audit.jsonl"
    monkeypatch.setattr(audit, "AUDIT_LOG_PATH", audit_path)

    audit.record_audit_event("incident_enabled", name="rag_slow", actor="api")
    audit.record_audit_event("incident_disabled", name="rag_slow", actor="api")

    lines = audit_path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 2

    first = json.loads(lines[0])
    assert first["event"] == "incident_enabled"
    assert first["name"] == "rag_slow"
    assert "ts" in first
