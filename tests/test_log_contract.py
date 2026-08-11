from __future__ import annotations

import json
from pathlib import Path

from app.schemas import LogRecord
from scripts import validate_logs


REPO_ROOT = Path(__file__).resolve().parents[1]


def test_log_record_model_accepts_runtime_response_fields() -> None:
    record = LogRecord(
        level="info",
        service="api",
        event="response_sent",
        correlation_id="req-12345678",
        env="test",
        quality_score=0.9,
    )

    assert record.quality_score == 0.9


def test_log_record_required_fields_match_json_schema() -> None:
    schema = json.loads((REPO_ROOT / "config" / "logging_schema.json").read_text())

    assert set(schema["required"]) == {"ts", "level", "service", "event"}
    assert validate_logs.REQUIRED_FIELDS == set(schema["required"])
    assert LogRecord.model_fields["correlation_id"].is_required() is False
    assert LogRecord.model_fields["env"].is_required() is False
