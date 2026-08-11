from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

REPO_ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = REPO_ROOT / "submission" / "evidence"


def main() -> None:
    before = json.loads((EVIDENCE / "cost_optimization_before.json").read_text(encoding="utf-8"))
    after = json.loads((EVIDENCE / "cost_optimization_after.json").read_text(encoding="utf-8"))

    fig, axes = plt.subplots(1, 2, figsize=(10, 4.5))

    ax = axes[0]
    ax.bar(["before", "after"], [before["total_cost_usd"], after["total_cost_usd"]], color=["#E45756", "#54A24B"])
    ax.set_title("Total cost (10 req, cost_spike on)")
    ax.set_ylabel("usd")
    for i, v in enumerate([before["total_cost_usd"], after["total_cost_usd"]]):
        ax.text(i, v, f"${v}", ha="center", va="bottom")

    ax = axes[1]
    ax.bar(["before", "after"], [before["tokens_out_total"], after["tokens_out_total"]], color=["#E45756", "#54A24B"])
    ax.set_title("Total output tokens")
    ax.set_ylabel("tokens")
    for i, v in enumerate([before["tokens_out_total"], after["tokens_out_total"]]):
        ax.text(i, v, str(v), ha="center", va="bottom")

    reduction = round((1 - after["total_cost_usd"] / before["total_cost_usd"]) * 100, 1)
    fig.suptitle(
        f"Cost optimization: cap MAX_OUTPUT_TOKENS in app/mock_llm.py "
        f"-> {reduction}% cost reduction under cost_spike incident"
    )
    fig.tight_layout(rect=(0, 0, 1, 0.93))
    out = EVIDENCE / "cost_optimization_before_after.png"
    fig.savefig(out, dpi=130)
    print(f"Saved: {out}")
    print(f"Reduction: {reduction}%")


if __name__ == "__main__":
    main()
