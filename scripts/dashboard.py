from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components
import yaml


REPO_ROOT = Path(__file__).resolve().parents[1]
LOG_PATH = REPO_ROOT / "data" / "logs.jsonl"
DASHBOARD_CONFIG_PATH = REPO_ROOT / "config" / "dashboard.yaml"

PANEL_ORDER = ("latency", "traffic", "errors", "cost", "tokens", "quality")


def load_dashboard_config() -> dict[str, Any]:
    with DASHBOARD_CONFIG_PATH.open(encoding="utf-8") as file:
        return yaml.safe_load(file)["dashboard"]


@st.cache_data(ttl=10)
def load_logs(path: str) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    log_path = Path(path)
    if not log_path.exists():
        return pd.DataFrame()

    with log_path.open(encoding="utf-8") as file:
        for line in file:
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue

    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(rows)
    df["ts"] = pd.to_datetime(df.get("ts"), utc=True, errors="coerce")
    df = df.dropna(subset=["ts"]).sort_values("ts")

    for column in ("latency_ms", "tokens_in", "tokens_out", "cost_usd", "quality_score"):
        if column in df.columns:
            df[column] = pd.to_numeric(df[column], errors="coerce")

    return df


def panel_by_id(config: dict[str, Any], panel_id: str) -> dict[str, Any]:
    return next(panel for panel in config["panels"] if panel["id"] == panel_id)


def window_logs(df: pd.DataFrame, minutes: int) -> pd.DataFrame:
    if df.empty:
        return df
    end = df["ts"].max()
    start = end - pd.Timedelta(minutes=minutes)
    return df[df["ts"].between(start, end)].copy()


def minute_series(
    df: pd.DataFrame,
    event: str,
    column: str | None = None,
    agg: str = "count",
) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame()

    event_df = df[df["event"] == event].copy()
    if event_df.empty:
        return pd.DataFrame()

    event_df["minute"] = event_df["ts"].dt.floor("min")
    if column is None:
        series = event_df.groupby("minute").size()
    elif agg == "sum":
        series = event_df.groupby("minute")[column].sum(min_count=1)
    elif agg == "mean":
        series = event_df.groupby("minute")[column].mean()
    else:
        series = event_df.groupby("minute")[column].count()

    return series.rename(column or event).reset_index()


def threshold_label(panel: dict[str, Any]) -> str:
    threshold = panel["threshold"]
    operator = "<=" if threshold["operator"] == "lte" else ">="
    return f"SLO {threshold['aggregation']} {operator} {threshold['value']} {panel['unit']}"


def passes_threshold(value: float, panel: dict[str, Any]) -> bool:
    threshold = panel["threshold"]
    if threshold["operator"] == "lte":
        return value <= threshold["value"]
    return value >= threshold["value"]


def status_badge(label: str, ok: bool) -> None:
    css_class = "ok" if ok else "warn"
    st.markdown(f'<span class="status {css_class}">{label}</span>', unsafe_allow_html=True)


def format_window(df: pd.DataFrame) -> str:
    if df.empty:
        return "No log data"
    start = df["ts"].min().strftime("%Y-%m-%d %H:%M UTC")
    end = df["ts"].max().strftime("%Y-%m-%d %H:%M UTC")
    return f"{start} to {end}"


def pct(value: float) -> str:
    return f"{value:.2f}%"


def usd(value: float) -> str:
    return f"${value:,.4f}"


def apply_style() -> None:
    st.markdown(
        """
        <style>
        .block-container {
            max-width: 1440px;
            padding-top: 1.25rem;
            padding-bottom: 2rem;
        }
        h1, h2, h3, p, div, span {
            letter-spacing: 0;
        }
        div[data-testid="stMetric"] {
            border: 1px solid #d8dee8;
            border-radius: 8px;
            padding: 12px 14px;
            background: #ffffff;
        }
        div[data-testid="stMetric"] label {
            color: #43536a;
            font-size: 0.88rem;
        }
        .status {
            display: inline-block;
            border-radius: 999px;
            padding: 4px 10px;
            font-size: 0.78rem;
            font-weight: 700;
            margin-bottom: 8px;
        }
        .status.ok {
            background: #e8f7ef;
            color: #13643b;
            border: 1px solid #a7dfbd;
        }
        .status.warn {
            background: #fff0e6;
            color: #93410c;
            border: 1px solid #f3bf95;
        }
        .panel-note {
            color: #56657a;
            font-size: 0.86rem;
            margin-top: -4px;
            margin-bottom: 8px;
        }
        section[data-testid="stSidebar"] {
            border-right: 1px solid #d8dee8;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_latency(df: pd.DataFrame, panel: dict[str, Any]) -> None:
    values = df.loc[df["event"] == "response_sent", "latency_ms"].dropna()
    p50 = float(values.quantile(0.50)) if not values.empty else 0.0
    p95 = float(values.quantile(0.95)) if not values.empty else 0.0
    p99 = float(values.quantile(0.99)) if not values.empty else 0.0
    threshold = panel["threshold"]["value"]

    st.subheader(panel["title"])
    status_badge("Within SLO" if passes_threshold(p95, panel) else "SLO breach", passes_threshold(p95, panel))
    st.markdown(f'<div class="panel-note">{threshold_label(panel)}</div>', unsafe_allow_html=True)
    c1, c2, c3 = st.columns(3)
    c1.metric("P50 latency", f"{p50:,.0f} ms")
    c2.metric("P95 latency", f"{p95:,.0f} ms")
    c3.metric("P99 latency", f"{p99:,.0f} ms")

    by_minute = minute_series(df, "response_sent", "latency_ms", "mean")
    if not by_minute.empty:
        chart = by_minute.rename(columns={"latency_ms": "avg_latency_ms"}).set_index("minute")
        chart["p95_slo_ms"] = threshold
        st.line_chart(chart, height=220)


def render_traffic(df: pd.DataFrame, panel: dict[str, Any], minutes: int) -> None:
    request_count = int((df["event"] == "request_received").sum()) if not df.empty else 0
    rate = request_count / max(minutes, 1)

    st.subheader(panel["title"])
    status_badge("Traffic present" if passes_threshold(rate, panel) else "Below expected traffic", passes_threshold(rate, panel))
    st.markdown(f'<div class="panel-note">{threshold_label(panel)}</div>', unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    c1.metric("Requests", f"{request_count:,}")
    c2.metric("Requests/min", f"{rate:.2f}")

    by_minute = minute_series(df, "request_received")
    if not by_minute.empty:
        st.bar_chart(by_minute.rename(columns={"request_received": "requests"}).set_index("minute"), height=220)


def render_errors(df: pd.DataFrame, panel: dict[str, Any]) -> None:
    requests = int((df["event"] == "request_received").sum()) if not df.empty else 0
    failures = int((df["event"] == "request_failed").sum()) if not df.empty else 0
    error_rate = (failures / requests * 100) if requests else 0.0

    st.subheader(panel["title"])
    status_badge("Within SLO" if passes_threshold(error_rate, panel) else "SLO breach", passes_threshold(error_rate, panel))
    st.markdown(f'<div class="panel-note">{threshold_label(panel)}</div>', unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    c1.metric("Error rate", pct(error_rate))
    c2.metric("Failed requests", f"{failures:,}")

    failed = df[df["event"] == "request_failed"]
    if not failed.empty and "error_type" in failed.columns:
        breakdown = failed["error_type"].fillna("unknown").value_counts().rename_axis("error_type").reset_index(name="count")
        st.bar_chart(breakdown.set_index("error_type"), height=220)
    else:
        st.info("No request_failed events in the selected window.")


def render_cost(df: pd.DataFrame, panel: dict[str, Any]) -> None:
    total = float(df.loc[df["event"] == "response_sent", "cost_usd"].sum(skipna=True)) if not df.empty else 0.0

    st.subheader(panel["title"])
    status_badge("Within budget" if passes_threshold(total, panel) else "Budget threshold exceeded", passes_threshold(total, panel))
    st.markdown(f'<div class="panel-note">{threshold_label(panel)}</div>', unsafe_allow_html=True)
    st.metric("Total cost", usd(total))

    by_minute = minute_series(df, "response_sent", "cost_usd", "sum")
    if not by_minute.empty:
        st.line_chart(by_minute.rename(columns={"cost_usd": "cost_usd"}).set_index("minute"), height=220)


def render_tokens(df: pd.DataFrame, panel: dict[str, Any]) -> None:
    response_df = df[df["event"] == "response_sent"] if not df.empty else pd.DataFrame()
    tokens_in = int(response_df["tokens_in"].sum(skipna=True)) if "tokens_in" in response_df else 0
    tokens_out = int(response_df["tokens_out"].sum(skipna=True)) if "tokens_out" in response_df else 0
    max_field = max(tokens_in, tokens_out)

    st.subheader(panel["title"])
    status_badge("Within SLO" if passes_threshold(max_field, panel) else "Token threshold exceeded", passes_threshold(max_field, panel))
    st.markdown(f'<div class="panel-note">{threshold_label(panel)}</div>', unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    c1.metric("Input tokens", f"{tokens_in:,}")
    c2.metric("Output tokens", f"{tokens_out:,}")
    st.bar_chart(pd.DataFrame({"tokens": [tokens_in, tokens_out]}, index=["input", "output"]), height=220)


def render_quality(df: pd.DataFrame, panel: dict[str, Any]) -> None:
    values = df.loc[df["event"] == "response_sent", "quality_score"].dropna()
    score = float(values.mean()) if not values.empty else 0.0

    st.subheader(panel["title"])
    status_badge("Within SLO" if passes_threshold(score, panel) else "SLO breach", passes_threshold(score, panel))
    st.markdown(f'<div class="panel-note">{threshold_label(panel)}</div>', unsafe_allow_html=True)
    st.metric("Mean quality score", f"{score:.3f}")

    by_minute = minute_series(df, "response_sent", "quality_score", "mean")
    if not by_minute.empty:
        chart = by_minute.rename(columns={"quality_score": "quality_score"}).set_index("minute")
        chart["quality_slo"] = panel["threshold"]["value"]
        st.line_chart(chart, height=220)


def main() -> None:
    config = load_dashboard_config()
    st.set_page_config(page_title=config["title"], layout="wide")
    apply_style()

    default_minutes = int(config["time_range_minutes"])
    refresh_seconds = int(config["refresh_seconds"])
    components.html(
        f"<script>setTimeout(() => window.parent.location.reload(), {refresh_seconds * 1000});</script>",
        height=0,
    )

    with st.sidebar:
        st.header("Controls")
        time_range = st.slider("Time range, minutes", 15, 240, default_minutes, step=15)
        st.caption(f"Default contract range: {default_minutes} minutes")
        st.caption(f"Auto refresh: {refresh_seconds} seconds")
        st.divider()
        st.caption(f"Source: {LOG_PATH.relative_to(REPO_ROOT)}")
        st.caption(f"Contract: {DASHBOARD_CONFIG_PATH.relative_to(REPO_ROOT)}")

    raw_logs = load_logs(str(LOG_PATH))
    logs = window_logs(raw_logs, time_range)

    st.title(config["title"])
    st.caption(f"Time range shown: last {time_range} minutes | {format_window(logs)}")

    if raw_logs.empty:
        st.warning("No valid logs found. Run the API and `python scripts/load_test.py --concurrency 5` first.")
        return

    total_requests = int((logs["event"] == "request_received").sum())
    total_responses = int((logs["event"] == "response_sent").sum())
    total_failures = int((logs["event"] == "request_failed").sum())
    total_cost = float(logs.loc[logs["event"] == "response_sent", "cost_usd"].sum(skipna=True))

    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Requests in window", f"{total_requests:,}")
    k2.metric("Responses", f"{total_responses:,}")
    k3.metric("Failures", f"{total_failures:,}")
    k4.metric("Cost", usd(total_cost))

    st.divider()

    left, right = st.columns(2)
    with left:
        render_latency(logs, panel_by_id(config, "latency"))
        st.divider()
        render_errors(logs, panel_by_id(config, "errors"))
        st.divider()
        render_tokens(logs, panel_by_id(config, "tokens"))
    with right:
        render_traffic(logs, panel_by_id(config, "traffic"), time_range)
        st.divider()
        render_cost(logs, panel_by_id(config, "cost"))
        st.divider()
        render_quality(logs, panel_by_id(config, "quality"))

    with st.expander("Dashboard contract"):
        contract_rows = []
        for panel_id in PANEL_ORDER:
            panel = panel_by_id(config, panel_id)
            contract_rows.append(
                {
                    "panel": panel["title"],
                    "events": ", ".join(panel["events"]),
                    "fields": ", ".join(panel["fields"]),
                    "unit": panel["unit"],
                    "threshold": threshold_label(panel),
                }
            )
        st.dataframe(pd.DataFrame(contract_rows), use_container_width=True, hide_index=True)


if __name__ == "__main__":
    main()
