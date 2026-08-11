from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any

AUDIT_LOG_PATH = Path(os.getenv("AUDIT_LOG_PATH", "data/audit.jsonl"))


def record_audit_event(event: str, **fields: Any) -> None:
    AUDIT_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "event": event,
        **fields,
    }
    with AUDIT_LOG_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
