---
name: excel-analyze
description: Đọc/đối chiếu Excel — cell value+format qua extract-cells.py, ảnh embedded qua extract-images.py, shape/annotation fallback render qua render-sheet.py + image-analyze.
---

## Trước khi chạy

Check `documents/`, `templates/`, `memory/` trong thư mục dự án hiện tại có tồn tại chưa:
- Chỉ thiếu 1 thư mục phụ (`documents/` hoặc `templates/`), `memory/` vẫn có → tự tạo thư mục trống, dùng mặc định cho lần này, báo 1 dòng rõ ràng. Không cần hỏi.
- Thiếu `memory/` → **không được** âm thầm chạy tiếp. Dừng lại, hỏi: "Dự án chưa init (thiếu `memory/`) — chạy `/brse-toolkit:init` trước để lưu được cho lần sau, hay tiếp tục 1 lần không lưu gì?"

## Cơ chế (spec mục 6.3)

1. `python3 ${CLAUDE_PLUGIN_ROOT}/skills/excel-analyze/scripts/extract-cells.py <file.xlsx>` —
   value + font_color + strike + fill_color + comment, đọc chính xác từ XML, KHÔNG phải vision.
2. Ý nghĩa định dạng (đỏ = gì, gạch ngang = gì) — KHÔNG đoán. Lần đầu quan sát pattern → hỏi
   xác nhận → ghi vào `memory/conventions.md`. Lần sau áp dụng luôn, không hỏi lại. Ô có định
   dạng lạ chưa từng xác nhận → flag riêng, không áp quy ước cũ lên nó.
3. `python3 ${CLAUDE_PLUGIN_ROOT}/skills/excel-analyze/scripts/extract-images.py <file.xlsx>
   <out_dir>` — ảnh dán trong sheet, bytes + vùng ô neo (KHÔNG phải 1 ô chính xác — nói rõ
   giới hạn này khi trích dẫn).
4. Shape/textbox/mũi tên annotation `extract-images.py` không đọc được → `python3
   ${CLAUDE_PLUGIN_ROOT}/skills/excel-analyze/scripts/render-sheet.py <file.xlsx> <out_dir>`.
   Script render ra file **PNG** (LibreOffice headless) và in JSON `{"file": "<path.png>"}` —
   chain đúng file PNG đó sang skill `image-analyze` (`ocr-pass.py` chỉ đọc được ảnh, không
   đọc được PDF).
5. Report cuối gộp 2 loại nguồn, KHÔNG trình bày ngang hàng: phần cell-text (chính xác tuyệt
   đối) và phần ảnh/shape (qua vision, gắn nhãn "đọc bằng ảnh, chưa chắc 100%").

## Xử lý batch (nhiều đơn vị độc lập)

Nhiều file Excel/sheet độc lập cần phân tích trong cùng 1 yêu cầu → dispatch song song (spec
mục 11), mỗi file 1 subagent. Mỗi subagent tự đọc `memory/conventions.md` +
`memory/glossary.md` trước khi phân tích. Agent chính gom kết quả, dedupe quy ước format mới
phát hiện rồi hỏi user 1 lần. **Subagent không bao giờ tự ghi `memory/`.**

## Dùng chung với `qa-tone-brse`

`extract-cells.py` cũng là script `qa-tone-brse` dùng để đọc lại Q&A list Excel — không có
bản sao thứ 2 của script này ở đâu khác.

## Trước khi trả lời

Áp `verify-output` — chạy
`${CLAUDE_PLUGIN_ROOT}/skills/verify-output/scripts/lint-hedge-words.py` trên draft response
trước khi gửi.
