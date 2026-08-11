# Khung thiết kế Observability

Dùng khung này trước khi triển khai, sau đó chuyển kết quả cuối sang `submission/REPORT.md`.

> Điền bởi: Role C (QA & Chief Investigator), dựa trên đọc code `app/main.py`, `app/middleware.py`, `app/agent.py` — một số chi tiết (correlation ID, enrichment) hiện còn là `TODO` phía Role A, đánh dấu `[A làm]` bên dưới.

## Người dùng và luồng chính

- Ai gửi request? Client gọi `POST /chat` với `user_id`, `session_id`, `feature`, `message` (xem `app/schemas.py`).
- Request đi qua những thành phần nào?
  `CorrelationIdMiddleware` (app/middleware.py) → endpoint `/chat` (app/main.py) → `LabAgent.run` (app/agent.py) → `mock_rag.retrieve` (Retrieval) → `prompt_management.resolve_prompt` (Langfuse prompt) → `mock_llm.FakeLLM.generate` (LLM) → ghi metrics (`app/metrics.py`) + cập nhật trace Langfuse → trả `ChatResponse`.
- Correlation ID được tạo và truyền ở đâu?
  Thiết kế: sinh tại `CorrelationIdMiddleware.dispatch` (từ header `x-request-id` nếu có, hoặc tạo mới dạng `req-<8-char-hex>`), gán vào `request.state.correlation_id`, bind vào `structlog.contextvars` để mọi log trong cùng request tự động có field này, và trả lại qua response header `x-request-id`. **[A làm]** — hiện `app/middleware.py` còn `TODO`, giá trị đang là chuỗi cố định `"MISSING"`.

## Tín hiệu quan sát

| Thành phần | Log cần có | Metric cần có | Span cần có |
|---|---|---|---|
| API (middleware + `/chat`) | `request_received`, `response_sent`, `request_failed` (event, correlation_id, user_id_hash, session_id, feature, model, env) | traffic (count/phút), error_rate theo `error_type`, latency P50/P95/P99 | span request/response bọc toàn bộ handler |
| Retrieval (`mock_rag.retrieve`) | số lượng doc trả về, query preview đã redact | doc_count (đang log trong metadata generation) | span retrieval lồng trong generation (hiện gộp chung, có thể tách nếu cần chi tiết hơn) |
| LLM (`mock_llm.FakeLLM` qua `LabAgent.run`) | tokens_in/out, cost_usd, quality_score, prompt_name/label/version/source | cost theo phút, tổng token, quality trung bình | span `generation` (đã có decorator `@observe(as_type="generation")` trong `app/agent.py`) |

## SLO và alert

Nguồn: `config/slo.yaml` (window 28 ngày) — role C đối chiếu với dashboard threshold trong `config/dashboard.yaml`, alert cụ thể chờ Role B điền `config/alert_rules.yaml` + `docs/alerts.md`.

| SLI | Mục tiêu | Cửa sổ đo | Alert |
|---|---:|---|---|
| Latency P95 | ≤ 3000 ms (99.5% thời gian) | 28 ngày (dashboard hiển thị rolling 60 phút) | **[B làm]** chưa có trong `config/alert_rules.yaml` |
| Error rate | ≤ 2% (99.0% thời gian) | 28 ngày | **[B làm]** |
| Cost | ≤ 2.5 USD/ngày (100% thời gian) | 28 ngày | **[B làm]** |
| Quality | ≥ 0.75 trung bình (95% thời gian) | 28 ngày | **[B làm]** |

## Rủi ro dữ liệu

- PII có thể xuất hiện ở đâu? Trong `message` người dùng gửi lên (`/chat`), trong `answer` LLM trả về, và trong bất kỳ `payload` nào log ra (message_preview, answer_preview, detail lỗi).
- Dữ liệu nào được phép ghi vào log? Chỉ bản đã qua `scrub_text`/`summarize_text` (`app/pii.py`) — che email, SĐT VN, CCCD, số thẻ tín dụng theo regex trong `PII_PATTERNS`. `user_id` luôn ghi dạng hash (`hash_user_id`), không ghi id gốc.
- Redaction diễn ra trước bước nào? Về nguyên tắc phải chạy trước khi `JsonlFileProcessor` ghi ra file. Hiện tại hàm `scrub_event` đã viết sẵn trong `app/logging_config.py` nhưng **chưa được đăng ký vào pipeline** (dòng `# scrub_event` đang bị comment) — đây là rủi ro cần Role A bật lên trước khi coi là "an toàn PII". Role C sẽ kiểm tra lại bằng cách thử gửi message chứa email/SĐT giả và xác nhận log không lộ nguyên văn.
