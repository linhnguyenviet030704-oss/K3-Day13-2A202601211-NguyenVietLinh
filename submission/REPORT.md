# Báo cáo Day 13 Observability

## 1. Thông tin nhóm

- Tên nhóm: Matikanefukukitaru
- Repository URL:https://github.com/linhnguyenviet030704-oss/K3-Day13-2A202601211-NguyenVietLinh/
- Commit SHA cuối:
- Thành viên và vai trò:
Nguyễn Việt Linh - 2A202601211 - Role A: CP1, Xây dựng Middleware, gán Correlation ID, Enrichment logs
Nguyễn Thị Hoàng Yến - 2A202601959 : Role B: CP2, Cấu hình Langfuse, thiết lập SLO/Alert Rules, viết tài liệu Alert Runbook.
Đỗ Tùng Dương - 2A202601899 - Role C: Thiết kế Dashboard Spec, thực hiện load test, quản lý Challenge/Practice Incident (CP3) và tổng hợp báo cáo nhóm.

## 2. Kết quả kỹ thuật

- Điểm `validate_logs.py`:
- Tổng số traces:
- Số PII leak còn lại:
- Link/đường dẫn dashboard:

## 3. Logging và tracing

- Evidence correlation ID:
- Evidence PII redaction:
- Evidence trace waterfall:
- Giải thích một span đáng chú ý:

## 4. Prompt versioning

- Prompt name:
- Version/label baseline:
- Version/label candidate:
- Trace ID của mỗi version:
- Bằng chứng đổi label hoặc rollback:

## 5. Dashboard, SLO và alerts

- Kết quả `validate_dashboard.py`:
- Evidence dashboard:
- SLO đã chọn và lý do:
- Alert rules và runbook:

## 6. Điều tra challenge

- Challenge ID:
- Triệu chứng từ metrics:
- Trace ID liên quan:
- Log line/correlation ID liên quan:
- Root cause:
- Fix action:
- Preventive measure:

## 7. Đóng góp cá nhân

Với mỗi thành viên, ghi rõ nhiệm vụ và link commit/PR tương ứng.

| Thành viên | Phần việc | Commit/PR | Điều đã học |
|---|---|---|---|
| | | | |

## Checkpoint 0-1 - Thanh vien A

- CP0 setup/baseline: API `/health` tra ve `{"ok": true, "tracing_enabled": false}`; `python scripts/load_test.py` sinh `data/logs.jsonl`.
- Baseline `python scripts/validate_logs.py`: `Estimated Score: 100/100`.
- Ket qua validator: 21 log records, 0 missing required fields, 0 missing enrichment, 10 unique correlation IDs, 0 potential PII leaks.
- CP1 correlation ID: cac request trong load test tra ve ID dang `req-<8 hex>` nhu `req-d90c82f8`, `req-562cefa3`, `req-4d6dc3f6`.
- CP1 enrichment logs: log API co `user_id_hash`, `session_id`, `feature`, `model`, `env`.
- CP1 PII redaction: email `student@vinuni.edu.vn`, phone `0987654321`, credit card `4111 1111 1111 1111` khong xuat hien nguyen van trong `data/logs.jsonl`.
- Dong gop ca nhan: Thanh vien A hoan thanh middleware correlation ID, context enrichment va PII scrub processor.
