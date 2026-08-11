# Báo cáo Day 13 Observability

## 1. Thông tin nhóm

- Tên nhóm: Matikanefukukitaru
- Repository URL: https://github.com/linhnguyenviet030704-oss/K3-Day13-2A202601211-NguyenVietLinh/
- Commit SHA cuối: 4bb8f28
- Thành viên và vai trò:
  - Nguyễn Việt Linh - 2A202601211 - Role A: CP1, xây dựng middleware, gán correlation ID, enrichment logs.
  - Nguyễn Thị Hoàng Yến - 2A202601959 - Role B: CP2, cấu hình Langfuse, thiết lập SLO/alert rules, viết alert runbook.
  - Đỗ Tùng Dương - 2A202601899 - Role C: thiết kế dashboard spec, thực hiện load test, quản lý challenge/practice incident và tổng hợp báo cáo.

## 2. Kết quả kỹ thuật

- Điểm `validate_logs.py`: `Estimated Score: 100/100` (105 log records, 0 missing required fields, 0 missing enrichment, 45 unique correlation IDs, 0 potential PII leaks).
- Tổng số traces: tối thiểu 10 traces trên Langfuse; evidence: `submission/evidence/traces.png`.
- Số PII leak còn lại: 0.
- Link/đường dẫn dashboard: `http://127.0.0.1:8501`; evidence ảnh: `submission/evidence/dashboard_baseline.png`, `submission/evidence/dashboard_rag_slow.png`.

## 3. Logging và tracing

- Evidence correlation ID: `data/logs.jsonl` có request/response cùng `correlation_id=req-0bd581bd`; log đã trích riêng tại `submission/evidence/incident_slowest_log.json`.
- Evidence PII redaction: log request `req-0bd581bd` ghi `message_preview` là `What is your refund policy? My email is [REDACTED_EMAIL]`; `validate_logs.py` báo 0 potential PII leaks.
- Evidence trace waterfall: `submission/evidence/traces_detail.png`; trace/run ID hiện trên ảnh: `3523209d2bff888a75e91fcb51c1b1ca`.
- Giải thích một span đáng chú ý: span `run` trong trace waterfall bọc toàn bộ request. Với incident `rag_slow`, điểm cần khoanh vùng là bước retrieve/RAG vì `app/mock_rag.py` chèn `time.sleep(2.5)` khi `STATE["rag_slow"]` bật.

## 4. Prompt versioning

- Prompt name: `day13-chat`.
- Version/label baseline: `v1` / `production` theo `submission/evidence/traces_detail.png`.
- Version/label candidate: chưa có evidence candidate riêng trong repo; cần bổ sung screenshot Langfuse nếu nộp đầy đủ phần prompt versioning.
- Trace ID của mỗi version: baseline trace/run `3523209d2bff888a75e91fcb51c1b1ca`; candidate trace ID chưa có text evidence trong repo.
- Bằng chứng đổi label hoặc rollback: chưa có ảnh riêng trong `submission/evidence/`; cần bổ sung screenshot đổi label/rollback trên Langfuse.

## 5. Dashboard, SLO và alerts

- Kết quả `validate_dashboard.py`: `HỢP LỆ: 6/6 panel có trong dashboard contract.`
- Evidence dashboard: baseline `submission/evidence/dashboard_baseline.png`; incident `submission/evidence/dashboard_rag_slow.png`; dashboard doc/source: `scripts/dashboard.py`, `config/dashboard.yaml`, `data/logs.jsonl`.
- SLO đã chọn và lý do: Latency P95 <= 3000 ms để bắt request chậm; error rate <= 2% để bắt lỗi người dùng thấy; cost 60-minute total <= 2.5 USD để tránh vượt ngân sách; quality avg >= 0.75 để theo dõi chất lượng proxy.
- Alert rules và runbook: `config/alert_rules.yaml` và `docs/alerts.md`.

## 6. Điều tra challenge

- Challenge ID: `day13-k3-observability-v1`.
- Triệu chứng từ metrics: dashboard baseline P95 khoảng 153 ms; sau `rag_slow`, P95 tăng lên khoảng 2653 ms trong ảnh `dashboard_rag_slow.png`; error rate vẫn 0% vì đây là incident latency, không phải error.
- Trace ID liên quan: trace/run `3523209d2bff888a75e91fcb51c1b1ca` trong `submission/evidence/traces_detail.png`; request chậm dùng correlation ID `req-0bd581bd`.
- Log line/correlation ID liên quan: `submission/evidence/incident_slowest_log.json`, `correlation_id=req-0bd581bd`, `latency_ms=2653`, `event=response_sent`.
- Root cause: practice incident `rag_slow` bật có chủ đích làm chậm RAG/retrieve; code tại `app/mock_rag.py` sleep 2.5 giây khi `STATE["rag_slow"]` là true.
- Fix action: tắt incident bằng `python scripts/inject_incident.py --scenario rag_slow --disable`; health check sau đó báo `rag_slow=false`.
- Preventive measure: giữ alert `high_latency_p95`, dashboard P95 60 phút, trace waterfall và log correlation ID để on-call khoanh vùng retrieve/RAG trước khi điều tra LLM hoặc API.

## 7. Đóng góp cá nhân

Với mỗi thành viên, ghi rõ nhiệm vụ và link commit/PR tương ứng.

| Thành viên | Phần việc | Commit/PR | Điều đã học |
|---|---|---|---|
| Nguyễn Việt Linh | CP1 | cp1/linh | setup base, gán log metadata |
| Nguyễn Thị Hoàng Yến | CP2 | cp2/new | setup langfuse, prompt, dashboard |
| Đỗ Tùng Dương | CP3 | cp3/duong | Dashboard spec, load test, quản lý challenge, incident |

## Checkpoint 0-1 - Thành viên A

- CP0 setup/baseline: API `/health` trả về `{"ok": true, "tracing_enabled": false}`; `python scripts/load_test.py` sinh `data/logs.jsonl`.
- Baseline `python scripts/validate_logs.py`: `Estimated Score: 100/100`.
- Kết quả validator: 21 log records, 0 missing required fields, 0 missing enrichment, 10 unique correlation IDs, 0 potential PII leaks.
- CP1 correlation ID: các request trong load test trả về ID dạng `req-<8 hex>` như `req-d90c82f8`, `req-562cefa3`, `req-4d6dc3f6`.
- CP1 enrichment logs: log API có `user_id_hash`, `session_id`, `feature`, `model`, `env`.
- CP1 PII redaction: email `student@vinuni.edu.vn`, phone `0987654321`, credit card `4111 1111 1111 1111` không xuất hiện nguyên văn trong `data/logs.jsonl`.
- Đóng góp cá nhân: Thành viên A hoàn thành middleware correlation ID, context enrichment và PII scrub processor.
