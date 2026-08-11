from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

LOG_PATH = REPO_ROOT / "data" / "logs.jsonl"
OUT_PATH = REPO_ROOT / "submission" / "evidence" / "dashboard_baseline.png"


def load_records() -> list[dict]:
    records = []
    for line in LOG_PATH.read_text(encoding="utf-8").splitlines():
        if line.strip():
            records.append(json.loads(line))
    return records


def percentile(values: list[float], p: int) -> float:
    if not values:
        return 0.0
    items = sorted(values)
    idx = max(0, min(len(items) - 1, round((p / 100) * len(items) + 0.5) - 1))
    return float(items[idx])


def minute_bucket(ts: str) -> str:
    return datetime.fromisoformat(ts.replace("Z", "+00:00")).strftime("%H:%M")


def build() -> dict:
    records = load_records()
    received = [r for r in records if r.get("event") == "request_received"]
    sent = [r for r in records if r.get("event") == "response_sent"]
    failed = [r for r in records if r.get("event") == "request_failed"]

    latencies = [r["latency_ms"] for r in sent]
    costs = [r["cost_usd"] for r in sent]
    tokens_in = sum(r.get("tokens_in", 0) for r in sent)
    tokens_out = sum(r.get("tokens_out", 0) for r in sent)
    quality = [r["quality_score"] for r in sent]
    error_types = Counter(r.get("error_type", "unknown") for r in failed)

    traffic_by_min: dict[str, int] = defaultdict(int)
    for r in received:
        traffic_by_min[minute_bucket(r["ts"])] += 1

    cost_by_min: dict[str, float] = defaultdict(float)
    for r in sent:
        cost_by_min[minute_bucket(r["ts"])] += r["cost_usd"]

    total_requests = len(received)
    error_rate_pct = (len(failed) / total_requests * 100) if total_requests else 0.0

    summary = {
        "latency_p50": percentile(latencies, 50),
        "latency_p95": percentile(latencies, 95),
        "latency_p99": percentile(latencies, 99),
        "traffic_count": total_requests,
        "traffic_rate_per_minute": total_requests / max(1, len(traffic_by_min)),
        "error_rate_pct": round(error_rate_pct, 2),
        "error_breakdown": dict(error_types),
        "cost_total_usd": round(sum(costs), 4),
        "cost_by_minute": dict(cost_by_min),
        "tokens_in_total": tokens_in,
        "tokens_out_total": tokens_out,
        "quality_mean": round(sum(quality) / len(quality), 3) if quality else 0.0,
    }

    thresholds = {
        "latency_p95": ("lte", 3000, summary["latency_p95"]),
        "traffic_rate_per_minute": ("gte", 1, summary["traffic_rate_per_minute"]),
        "error_rate_pct": ("lte", 2, summary["error_rate_pct"]),
        "cost_total_usd": ("lte", 2.5, summary["cost_total_usd"]),
        "tokens_total": ("lte", 50000, tokens_in + tokens_out),
        "quality_mean": ("gte", 0.75, summary["quality_mean"]),
    }
    checks = {}
    for name, (op, value, actual) in thresholds.items():
        ok = actual <= value if op == "lte" else actual >= value
        checks[name] = {"actual": actual, "threshold": value, "op": op, "ok": ok}

    return {"summary": summary, "checks": checks, "latencies": latencies, "traffic_by_min": traffic_by_min,
            "cost_by_min": cost_by_min, "error_types": error_types, "quality": quality}


def render(data: dict) -> None:
    fig, axes = plt.subplots(2, 3, figsize=(16, 10))
    fig.suptitle(
        "Day 13 AI Observability Dashboard — source: data/logs.jsonl | "
        "time range: 60 minutes | refresh: 30s",
        fontsize=12,
    )

    s = data["summary"]

    ax = axes[0][0]
    ax.bar(["p50", "p95", "p99"], [s["latency_p50"], s["latency_p95"], s["latency_p99"]], color="#4C78A8")
    ax.axhline(3000, color="red", linestyle="--", label="SLO p95 <= 3000")
    ax.set_title("Latency percentiles")
    ax.set_ylabel("ms")
    ax.legend(fontsize=8)

    ax = axes[0][1]
    mins = sorted(data["traffic_by_min"])
    ax.plot(mins, [data["traffic_by_min"][m] for m in mins], marker="o", color="#54A24B")
    ax.axhline(1, color="red", linestyle="--", label="SLO >= 1 req/min")
    ax.set_title(f"Request traffic ({s['traffic_count']} req total)")
    ax.set_ylabel("requests_per_minute")
    ax.tick_params(axis="x", rotation=45)
    ax.legend(fontsize=8)

    ax = axes[0][2]
    if data["error_types"]:
        ax.bar(list(data["error_types"].keys()), list(data["error_types"].values()), color="#E45756")
    else:
        ax.text(0.5, 0.5, "0 errors", ha="center", va="center")
    ax.axhline(2, color="red", linestyle="--", label="SLO <= 2%")
    ax.set_title(f"Error rate and breakdown ({s['error_rate_pct']}%)")
    ax.set_ylabel("percent")
    ax.legend(fontsize=8)

    ax = axes[1][0]
    cmins = sorted(data["cost_by_min"])
    ax.plot(cmins, [data["cost_by_min"][m] for m in cmins], marker="o", color="#F58518")
    ax.set_title(f"Cost over time (total {s['cost_total_usd']}, SLO <= 2.5)")
    ax.set_ylabel("usd")
    ax.tick_params(axis="x", rotation=45)

    ax = axes[1][1]
    ax.bar(["tokens_in", "tokens_out"], [s["tokens_in_total"], s["tokens_out_total"]], color="#72B7B2")
    ax.axhline(50000, color="red", linestyle="--", label="SLO <= 50000")
    ax.set_title("Input and output tokens")
    ax.set_ylabel("tokens")
    ax.legend(fontsize=8)

    ax = axes[1][2]
    ax.hist(data["quality"], bins=10, color="#B279A2")
    ax.axvline(0.75, color="red", linestyle="--", label="SLO >= 0.75")
    ax.set_title(f"Quality proxy (mean {s['quality_mean']})")
    ax.set_xlabel("score_0_to_1")
    ax.legend(fontsize=8)

    fig.tight_layout(rect=(0, 0, 1, 0.96))
    fig.subplots_adjust(hspace=0.5, wspace=0.3)
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT_PATH, dpi=130)
    print(f"Saved: {OUT_PATH}")


def main() -> None:
    data = build()
    render(data)
    print("\n--- Panel summary ---")
    print(json.dumps(data["summary"], indent=2, ensure_ascii=False))
    print("\n--- Threshold checks ---")
    for name, check in data["checks"].items():
        status = "OK" if check["ok"] else "VI PHAM"
        print(f"[{status}] {name}: actual={check['actual']} {check['op']} threshold={check['threshold']}")


if __name__ == "__main__":
    main()
