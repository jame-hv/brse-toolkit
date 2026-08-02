---
name: report-gen
description: Xuất Excel/Slide/Word đúng template khách. Ví dụ luồng cụ thể cho slide ở dưới.
---

## Nguồn template

Check `templates/` (thư mục dự án, KHÔNG phải template mặc định đóng gói trong
`skills/detail-design-jp/templates/` — 2 khái niệm khác chỗ, xem spec mục 7) — có mẫu riêng
của khách thì dùng `python-pptx`/`python-docx`/`openpyxl` mở template đó và điền nội dung,
giữ nguyên design. Chưa có → dùng mẫu mặc định đơn giản, nói rõ trong response: "chưa có
template khách, dùng mẫu mặc định — xác nhận format sau."

## Luồng cụ thể — tạo slide (spec mục 6.9)

1. **Nội dung lấy từ đâu** — không tự bịa. Status report → `memory/decisions-log.md` +
   `cross-check`/`code-to-business` nếu có. Đề xuất giải pháp → chain qua `proposal-gen`
   trước. User cung cấp trực tiếp → dùng nội dung đó.
2. **Xác định template** — như trên.
3. **Xác định người đọc** — áp mô hình relay (spec mục 2): slide khách Nhật khác slide nội bộ
   PM/dev. Chưa rõ → hỏi trước khi soạn.
4. **Áp `verify-output` cho từng bullet** — claim/số liệu không gắn được nguồn → để trong
   speaker notes "cần xác nhận thêm", KHÔNG đưa thẳng lên slide như fact đã chốt.
5. Tạo file thật bằng `python-pptx` (hoặc `openpyxl`/`python-docx` cho Excel/Word).
6. **Output**: file + danh sách ngắn "giả định/điểm chưa xác nhận" TÁCH RIÊNG để user duyệt
   trước khi gửi — không lẫn vào trong file.
