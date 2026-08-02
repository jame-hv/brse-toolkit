---
name: code-to-business
description: Trích nghiệp vụ từ source code không có tài liệu, mỗi câu mô tả trỏ về file:line chính xác qua extract-refs.py.
---

## Trigger

Cần hiểu nghiệp vụ từ source code, không đọc "toàn bộ codebase" — bắt buộc có phạm vi cụ thể
(1 tính năng/luồng nghiệp vụ, vd "luồng đơn hàng tồn kho"). Chưa rõ phạm vi → hỏi lại, không
tự chọn đại.

## Chiến lược đọc codebase lớn (spec mục 6.10)

1. `python3 scripts/extract-refs.py <path> <keyword1> <keyword2> ...` với keyword nghiệp vụ
   trong phạm vi đã xác định → danh sách file:line, không đổ nguyên file vào context.
2. Từ danh sách match, chỉ đọc (Read tool, đúng đoạn dòng liên quan) file/hàm thực sự nằm
   trong luồng — không đọc hết mọi file có match.
3. Phạm vi rải >~10 file → xử lý từng file/module một, ghi phát hiện vào bản nháp trung gian,
   tổng hợp ở bước cuối. Có thể dispatch song song theo module (spec mục 11) — mỗi subagent
   đọc `memory/glossary.md` trước khi phân tích, KHÔNG tự ghi `memory/`.
4. Match tìm được nhưng không chắc liên quan → liệt kê riêng "tìm thấy nhưng chưa chắc liên
   quan, cần xác nhận" — không tự loại, không tự gộp vào kết luận chính.

## Output

Tài liệu nghiệp vụ (điều kiện, luồng xử lý, validation), mỗi câu mô tả kèm `(nguồn:
file:dòng)` — theo `verify-output`.

## Trước khi tin nội dung DD/spec hiện có

Check `memory/decisions-log.md` trước — DD có thể chưa phản ánh quyết định QA gần nhất
(spec mục 3).
