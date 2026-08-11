# Alert Runbook - CP2

Moi alert ben duoi dua tren trieu chung nguoi dung thay duoc hoac SLO, khong dua vao ten ham hay chi tiet implementation.

## Alert 1

- Ten: `high_latency_p95`
- Severity: warning
- SLI/SLO lien quan: `latency_p95_ms`, objective P95 <= 3000 ms, target 99.5%
- Dieu kien kich hoat: `latency_p95 > 3000ms for 5 minutes`
- Anh huong toi nguoi dung: request tra loi cham, chat bi tre, demo co cam giac he thong bi dung.
- Ba buoc kiem tra dau tien:
  1. Mo dashboard Latency, xac nhan P95 tang trong 60 phut gan nhat va khong phai chi mot request le.
  2. Mo Langfuse trace cua request cham, so sanh span `retrieve`, `generate`, va span cha `run`.
  3. Tim log cung correlation ID de xem request cham co trung voi incident, error, hay payload bat thuong khong.
- Mitigation tam thoi: giam concurrency load test, tat incident `rag_slow` neu dang bat, rollback prompt/model neu trace cho thay LLM chieu dai bat thuong.
- Owner: `on-call-engineer`

## Alert 2

- Ten: `elevated_error_rate`
- Severity: critical
- SLI/SLO lien quan: `error_rate_pct`, objective <= 2%, target 99.0%
- Dieu kien kich hoat: `error_rate_pct > 5 for 3 minutes`
- Anh huong toi nguoi dung: nguoi dung nhan HTTP 500 hoac cau tra loi bi fail thay vi co ket qua.
- Ba buoc kiem tra dau tien:
  1. Mo panel Error rate and breakdown, xac dinh loai loi chiem nhieu nhat trong `error_breakdown`.
  2. Loc log `request_failed` theo correlation ID gan nhat de lay `error_type` va message da sanitize.
  3. Mo trace tu cung request de xem loi xay ra truoc RAG, trong `retrieve`, trong `generate`, hay sau khi tao response.
- Mitigation tam thoi: tat incident `tool_fail` neu dang bat, rollback cau hinh/prompt gan nhat, hoac chuyen ve fallback answer neu loi den tu dependency ben ngoai.
- Owner: `on-call-engineer`

## Alert 3

- Ten: `cost_budget_exceeded`
- Severity: warning
- SLI/SLO lien quan: `daily_cost_usd`, objective <= 2.5 USD/ngay, target 100.0%
- Dieu kien kich hoat: `daily_cost_usd > 2.5`
- Anh huong toi nguoi dung: he thong co nguy co bi gioi han ngan sach, bi cat giam load test, hoac phai dung prompt/model re hon.
- Ba buoc kiem tra dau tien:
  1. Mo panel Cost budget, so sanh `total_cost_usd` va `avg_cost_usd` voi baseline truoc load test.
  2. Kiem tra panel Tokens de xem chi phi tang do input hay output tokens.
  3. Mo Langfuse trace co cost cao, xem prompt version, span `generate`, va output token usage.
- Mitigation tam thoi: giam so request load test, tat incident `cost_spike` neu dang bat, rut gon prompt/context hoac rollback prompt version tao output dai.
- Owner: `team-lead`

## Cau hoi phan bien

Alert nen symptom-based vi nguoi dung chi cam nhan he thong cham, loi, ton tien bat thuong, hoac chat luong giam; ho khong quan tam ham nao bi fail. Alert theo trieu chung giup on-call uu tien dung tac dong thuc te, tranh bi nhiem nhieu alert noi bo, va van cho phep dung metrics -> traces -> logs de tim implementation root cause sau do.
