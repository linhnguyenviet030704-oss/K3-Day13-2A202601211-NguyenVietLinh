# Template Alert và Runbook

Mỗi alert phải dựa trên triệu chứng người dùng hoặc SLO, không dựa trực tiếp vào tên implementation nội bộ.

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
