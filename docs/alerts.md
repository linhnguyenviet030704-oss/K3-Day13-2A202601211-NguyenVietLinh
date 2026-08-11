# Alert Runbook - CP2

Moi alert ben duoi dua tren trieu chung nguoi dung thay duoc hoac SLO, khong dua vao ten ham hay chi tiet implementation.

### Alert 1

* **Tên:** Agent Response Latency cao
* **Severity:** P2 (High)
* **SLI/SLO liên quan:** P95 latency của toàn bộ agent response (bao gồm LLM call + tool call nếu có) phải < 3s (SLO: 99% request trong 30 ngày)
* **Điều kiện và thời gian duy trì:** P95 latency > 5s, duy trì liên tục 5 phút
* **Ảnh hưởng tới người dùng:** Người dùng chờ lâu mới nhận được phản hồi từ agent, có thể bỏ ngang phiên chat, cảm giác hệ thống "đơ"
* **Ba bước kiểm tra đầu tiên:**
  1. Xem trace trên Langfuse để xác định span nào chậm — LLM call, tool/function call, hay retrieval/context building
  2. Kiểm tra có đang bị retry liên tục do lỗi tạm thời (timeout, rate limit từ mock LLM) không
  3. Đối chiếu với thời điểm deploy gần nhất hoặc thay đổi prompt/model config
* **Mitigation tạm thời:** Giảm max_tokens hoặc độ phức tạp của prompt, bật timeout + fallback response ngắn, scale thêm worker nếu do queue backlog
* **Owner:** Team AI Platform
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

### Alert 2

* **Tên:** Cost per Request tăng bất thường
* **Severity:** P2 (High) — nâng P1 nếu tăng đột biến (>5x baseline)
* **SLI/SLO liên quan:** Cost trung bình mỗi request (dựa trên token usage) phải nằm trong ngân sách đã định, ví dụ < $0.02/request (SLO: chi phí trung bình theo giờ không vượt ngưỡng)
* **Điều kiện và thời gian duy trì:** Cost trung bình mỗi request tăng > 3x so với baseline 7 ngày, duy trì 15 phút
* **Ảnh hưởng tới người dùng:** Không trực tiếp ảnh hưởng trải nghiệm ngay, nhưng có thể dẫn đến rate limiting/cắt giảm tính năng nếu ngân sách bị vượt, ảnh hưởng tính bền vững dịch vụ
* **Ba bước kiểm tra đầu tiên:**
  1. Xem trace trên Langfuse để kiểm tra token count (input/output) của các request gần đây, so sánh với baseline
  2. Kiểm tra có request nào bị loop (agent gọi tool/LLM lặp lại nhiều lần) hay context bị phình to bất thường không
  3. Kiểm tra có thay đổi model, prompt template, hoặc input người dùng bất thường (input rất dài) không
* **Mitigation tạm thời:** Giới hạn max_tokens/context window, chặn loop bằng max iteration count, tạm thời chuyển sang model rẻ hơn nếu có
* **Owner:** Team AI Platform
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

### Alert 3

* **Tên:** Tỷ lệ lỗi hoặc chất lượng phản hồi giảm (Error Rate / Quality Degradation)
* **Severity:** P1 (Critical)
* **SLI/SLO liên quan:** Tỷ lệ request lỗi (5xx, timeout, hoặc response không hợp lệ/hallucination bị flag) phải < 1% (SLO: 99% response hợp lệ)
* **Điều kiện và thời gian duy trì:** Error rate > 5% trong cửa sổ 5 phút, hoặc tỷ lệ response bị flag chất lượng thấp (validation fail, empty response, format sai) > 10% trong 10 phút
* **Ảnh hưởng tới người dùng:** Người dùng nhận phản hồi sai, không đầy đủ, hoặc không nhận được phản hồi — mất niềm tin vào agent, có thể gây quyết định sai nếu dựa vào output
* **Ba bước kiểm tra đầu tiên:**
  1. Xem log JSON có cấu trúc để phân loại lỗi (lỗi hệ thống vs lỗi logic/parsing vs lỗi từ mock LLM)
  2. Dùng correlation ID để lần theo trace cụ thể trên Langfuse, xem input nào gây lỗi
  3. Đối chiếu thời điểm lỗi tăng với release/deploy gần nhất (đúng tinh thần phần Incident Investigation)
* **Mitigation tạm thời:** Rollback release gần nhất, bật fallback response mặc định khi validation fail, tạm ngắt tính năng agent đang lỗi và thông báo người dùng
* **Owner:** Team AI Platform on-call
- Ten: `cost_budget_exceeded`
- Severity: warning
- SLI/SLO lien quan: `cost_window_usd`, objective <= 2.5 USD trong cua so 60 phut, target 100.0%
- Dieu kien kich hoat: `total_cost_usd > 2.5 over 60 minutes`
- Anh huong toi nguoi dung: he thong co nguy co bi gioi han ngan sach, bi cat giam load test, hoac phai dung prompt/model re hon.
- Ba buoc kiem tra dau tien:
  1. Mo panel Cost budget, so sanh `total_cost_usd` va `avg_cost_usd` voi baseline truoc load test.
  2. Kiem tra panel Tokens de xem chi phi tang do input hay output tokens.
  3. Mo Langfuse trace co cost cao, xem prompt version, span `generate`, va output token usage.
- Mitigation tam thoi: giam so request load test, tat incident `cost_spike` neu dang bat, rut gon prompt/context hoac rollback prompt version tao output dai.
- Owner: `team-lead`

## Cau hoi phan bien

Alert nen symptom-based vi nguoi dung chi cam nhan he thong cham, loi, ton tien bat thuong, hoac chat luong giam; ho khong quan tam ham nao bi fail. Alert theo trieu chung giup on-call uu tien dung tac dong thuc te, tranh bi nhiem nhieu alert noi bo, va van cho phep dung metrics -> traces -> logs de tim implementation root cause sau do.
