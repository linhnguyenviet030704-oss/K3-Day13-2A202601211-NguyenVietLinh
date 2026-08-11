from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient

from app import logging_config
from app.main import app, agent
from app.pii import hash_user_id


def test_chat_logs_correlation_enrichment_and_scrubbed_pii(
    monkeypatch, tmp_path: Path
) -> None:
    log_path = tmp_path / "logs.jsonl"
    monkeypatch.setattr(logging_config, "LOG_PATH", log_path)
    monkeypatch.setenv("APP_ENV", "test")

    with TestClient(app) as client:
        response = client.post(
            "/chat",
            headers={"x-request-id": "req-deadbeef"},
            json={
                "user_id": "student-a",
                "session_id": "session-a",
                "feature": "qa",
                "message": "Email a@b.com, phone 090 123 4567, card 4111 1111 1111 1111",
            },
        )

    assert response.status_code == 200
    assert response.json()["correlation_id"] == "req-deadbeef"
    assert response.headers["x-request-id"] == "req-deadbeef"
    assert float(response.headers["x-response-time-ms"]) >= 0

    raw_logs = log_path.read_text(encoding="utf-8")
    assert "a@b.com" not in raw_logs
    assert "090 123 4567" not in raw_logs
    assert "4111 1111 1111 1111" not in raw_logs

    api_events = [
        json.loads(line)
        for line in raw_logs.splitlines()
        if json.loads(line).get("service") == "api"
    ]
    assert api_events
    for event in api_events:
        assert event["correlation_id"] == "req-deadbeef"
        assert event["user_id_hash"] == hash_user_id("student-a")
        assert event["session_id"] == "session-a"
        assert event["feature"] == "qa"
        assert event["model"] == agent.model
        assert event["env"] == "test"
