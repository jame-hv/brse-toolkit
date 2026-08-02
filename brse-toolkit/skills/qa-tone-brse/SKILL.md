---
name: qa-tone-brse
description: Trả lời Q&A cho khách/dev qua chat/ticket tool hoặc Excel Q&A list, đúng văn phong từng kênh. Quản lý luôn QA log trong chính file Excel gửi khách.
---

## Trước khi chạy

Check `documents/`, `templates/`, `memory/` trong thư mục dự án hiện tại có tồn tại chưa:
- Chỉ thiếu 1 thư mục phụ (`documents/` hoặc `templates/`), `memory/` vẫn có → tự tạo thư mục trống, dùng mặc định cho lần này, báo 1 dòng rõ ràng. Không cần hỏi.
- Thiếu `memory/` → **không được** âm thầm chạy tiếp. Dừng lại, hỏi: "Dự án chưa init (thiếu `memory/`) — chạy `/brse-toolkit:init` trước để lưu được cho lần sau, hay tiếp tục 1 lần không lưu gì?"

## Trigger

Cần trả lời câu hỏi từ khách hoặc dev — qua chat/ticket tool (Backlog, Redmine, Chatwork...)
hoặc ghi vào cột trả lời trong Q&A list Excel.

## Trước khi trả lời — bắt buộc

1. Đọc `memory/parties.md` — xác định người hỏi là bên nào, người đọc câu trả lời là bên nào.
   Áp mô hình relay: KHÔNG dịch nguyên đại từ nhân xưng của câu hỏi gốc vào câu trả lời nếu
   người đọc là bên khác — dùng tên bên cụ thể hoặc "chúng tôi"/"quý vị" trung tính.
2. Nếu câu trả lời sẽ ghi vào 1 file Q&A list Excel đã có sẵn: chạy
   `python3 ${CLAUDE_PLUGIN_ROOT}/skills/excel-analyze/scripts/extract-cells.py
   <path/to/qa-list.xlsx>` để đọc lại toàn bộ câu hỏi/trả lời hiện có.
3. So câu hỏi mới với các câu đã có (text similarity đơn giản — trùng ý, không cần trùng chữ).
   Nếu giống câu đã trả lời rồi → báo lại câu trả lời cũ, KHÔNG tự soạn câu trả lời khác đi.

## Văn phong theo kênh

- **Chat/ticket tool**: ngắn gọn, đi thẳng vào câu trả lời, kính ngữ vừa phải, không mở/đóng
  thư như email.
- **Excel Q&A list**: trang trọng hơn 1 bậc vì là hồ sơ lưu lại chính thức.

Cả 2 kênh đều dùng chung `memory/glossary.md` cho thuật ngữ — không tự đặt từ mới.

## Xử lý batch (nhiều đơn vị độc lập)

Nhiều câu Q&A độc lập trong cùng 1 yêu cầu (vd "trả lời 10 câu trong Q&A list này") →
dispatch song song (spec mục 11), mỗi câu 1 subagent. Mỗi subagent tự đọc
`memory/parties.md` + `memory/glossary.md` trước khi soạn. Agent chính gom kết quả, dedupe
thuật ngữ/quyết định mới rồi hỏi user 1 lần, ghi 1 lượt vào file Q&A list.
**Subagent không bao giờ tự ghi `memory/`.**

## Sau khi trả lời

- Câu trả lời không chắc chắn → gắn nhãn "chưa xác nhận được, cần hỏi khách" (nguyên tắc
  `verify-output` — chạy
  `${CLAUDE_PLUGIN_ROOT}/skills/verify-output/scripts/lint-hedge-words.py` trên draft trước
  khi gửi), không tự suy đoán ý khách.
- Nếu câu trả lời này là 1 quyết định mới chưa từng có trong `memory/decisions-log.md` →
  hỏi user có lưu lại không, rồi ghi ngay (không trì hoãn — xem CLAUDE.md rule).
