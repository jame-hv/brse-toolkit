---
name: verify-output
description: Bắt buộc trước khi trả lời bất kỳ kết luận nào — kiểm tra mỗi claim có nguồn, cấm từ mơ hồ. Chạy cuối mọi skill khác trong brse-toolkit, không gọi tay.
---

## Chính sách (spec mục 6.1)

1. Liệt kê từng câu kết luận trong draft response.
2. Mỗi câu kết luận phải có tag nguồn: `(nguồn: file:dòng)` / `(nguồn: sheet, ô)` / `(nguồn: spec trang X)`.
3. Không gắn được nguồn → viết "chưa xác định được — cần hỏi khách", không viết như sự thật.
4. Cấm từ mơ hồ trong kết luận: "có lẽ", "chắc là", "hình như", "có thể" (không cấm khi đang hỏi lại khách).

## Cơ chế

Trước khi gửi câu trả lời cuối, chạy:

    python3 scripts/lint-hedge-words.py <draft.txt>

Đọc JSON trả về. Nếu `ok: false`, sửa draft cho tới khi sạch violation rồi mới trả lời —
không bỏ qua kết quả script.
