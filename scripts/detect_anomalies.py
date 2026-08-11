from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app.cli import configure_utf8_stdio
from app.pii import PII_PATTERNS

LOG_PATH = REPO_ROOT / "data" / "logs.jsonl"
SLO_PATH = REPO_ROOT / "config" / "slo.yaml"


def load_records(path: Path) -> list[dict]:
    records = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            records.append(json.loads(line))
    return records


def flatten_strings(value, out: list[str]) -> None:
    if isinstance(value, str):
        out.append(value)
    elif isinstance(value, dict):
        for v in value.values():
            flatten_strings(v, out)
    elif isinstance(value, list):
        for v in value:
            flatten_strings(v, out)


def find_pii_leaks(records: list[dict]) -> list[dict]:
    leaks = []
    for record in records:
        strings: list[str] = []
        flatten_strings(record, strings)
        for text in strings:
            for name, pattern in PII_PATTERNS.items():
                for match in re.finditer(pattern, text):
                    window_start = max(0, match.start() - 12)
                    if "REDACTED" in text[window_start:match.end() + 12]:
                        continue
                    leaks.append(
                        {
                            "type": name,
                            "correlation_id": record.get("correlation_id"),
                            "event": record.get("event"),
                            "match": match.group(0),
                        }
                    )
    return leaks


def find_latency_violations(records: list[dict], objective_ms: float) -> list[dict]:
    violations = []
    for record in records:
        if record.get("event") == "response_sent" and "latency_ms" in record:
            if record["latency_ms"] > objective_ms:
                violations.append(
                    {
                        "correlation_id": record.get("correlation_id"),
                        "latency_ms": record["latency_ms"],
                        "objective_ms": objective_ms,
                    }
                )
    return violations


def find_error_spikes(records: list[dict], objective_pct: float) -> dict | None:
    received = sum(1 for r in records if r.get("event") == "request_received")
    failed = sum(1 for r in records if r.get("event") == "request_failed")
    if received == 0:
        return None
    error_rate_pct = round(failed / received * 100, 2)
    if error_rate_pct > objective_pct:
        return {"error_rate_pct": error_rate_pct, "objective_pct": objective_pct, "failed": failed, "received": received}
    return None


def main() -> int:
    configure_utf8_stdio()
    parser = argparse.ArgumentParser(description="Phat hien anomaly tu data/logs.jsonl")
    parser.add_argument("--log", type=Path, default=LOG_PATH)
    args = parser.parse_args()

    if not args.log.exists():
        print(f"Khong tim thay log file: {args.log}")
        return 1

    slo = yaml.safe_load(SLO_PATH.read_text(encoding="utf-8"))
    latency_objective = slo["slis"]["latency_p95_ms"]["objective"]
    error_objective = slo["slis"]["error_rate_pct"]["objective"]

    records = load_records(args.log)

    pii_leaks = find_pii_leaks(records)
    latency_violations = find_latency_violations(records, latency_objective)
    error_spike = find_error_spikes(records, error_objective)

    print(f"--- Anomaly scan: {args.log} ({len(records)} records) ---")

    if pii_leaks:
        print(f"[CRITICAL] {len(pii_leaks)} potential PII leak(s) found:")
        for leak in pii_leaks[:10]:
            print(f"  - type={leak['type']} correlation_id={leak['correlation_id']} match={leak['match']!r}")
    else:
        print("[OK] No raw PII leaks detected.")

    if latency_violations:
        print(f"[WARNING] {len(latency_violations)} request(s) exceeded latency SLO ({latency_objective} ms):")
        for v in latency_violations[:10]:
            print(f"  - correlation_id={v['correlation_id']} latency_ms={v['latency_ms']}")
    else:
        print(f"[OK] No request exceeded latency SLO ({latency_objective} ms).")

    if error_spike:
        print(f"[WARNING] Error rate {error_spike['error_rate_pct']}% exceeds SLO {error_spike['objective_pct']}%.")
    else:
        print(f"[OK] Error rate within SLO ({error_objective}%).")

    return 1 if pii_leaks else 0


if __name__ == "__main__":
    raise SystemExit(main())
