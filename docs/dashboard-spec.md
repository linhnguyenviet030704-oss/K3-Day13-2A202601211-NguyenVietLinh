# Dashboard Spec - CP2

Nguon du lieu dashboard: `data/logs.jsonl`.

`GET /metrics` chi la endpoint kiem tra nhanh snapshot runtime, khong phai
nguon chuan cua 6 panel dashboard.

Lenh kiem tra snapshot hien tai:

```bash
curl http://localhost:8000/metrics | python -m json.tool
```

Ket qua hien tai khi kiem tra local:

```json
{
  "traffic": 0,
  "latency_p50": 0.0,
  "latency_p95": 0.0,
  "latency_p99": 0.0,
  "error_rate_pct": 0.0,
  "avg_cost_usd": 0.0,
  "total_cost_usd": 0,
  "tokens_in_total": 0,
  "tokens_out_total": 0,
  "error_breakdown": {},
  "quality_avg": 0.0
}
```

Cong cu su dung: dashboard spec trong repo cho CP2; Langfuse dung cho trace waterfall va prompt version, khong phai nguon chinh cua 6 panel metrics.

Khoang thoi gian mac dinh: 60 phut. Tu refresh: 30 giay.

| # | Nhom | Panel | Event/field tu `data/logs.jsonl` | Don vi | Visualization | Threshold/SLO line |
|---|---|---|---|---|---|---|
| 1 | Latency | Latency P50/P95/P99 | `response_sent.latency_ms` | ms | Line chart + single value P95 | P95 <= 3000 ms |
| 2 | Traffic | Request traffic | `request_received` | requests/minute | Counter tong request | >= 1 request/phut khi load test |
| 3 | Error | Error rate and breakdown | `request_received`, `request_failed`, `error_type` | %, count | Single value error rate + table breakdown | Error rate <= 2%; critical neu > 5% trong 3 phut |
| 4 | Cost | Cost budget | `response_sent.cost_usd` | USD | Gauge tong chi phi + avg cost | 60-minute total cost <= 2.5 USD |
| 5 | Tokens | Token consumption | `response_sent.tokens_in`, `response_sent.tokens_out` | tokens | Stacked bar input/output | Canh bao neu tong token tang bat thuong so voi baseline |
| 6 | Quality | Average quality score | `response_sent.quality_score` | score 0-1 | Single value + trend line | Quality avg >= 0.75 |

Yeu cau evidence: luu anh dashboard hoac file spec da dien day du trong `submission/evidence/`. Anh dashboard neu co phai thay ten panel, time range, don vi va threshold/SLO line.

Kiem tra contract dashboard:

```bash
python scripts/validate_dashboard.py
```
