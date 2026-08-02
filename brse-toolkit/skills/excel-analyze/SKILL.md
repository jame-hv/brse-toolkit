---
name: excel-analyze
description: Đọc/đối chiếu Excel — cell value+format qua extract-cells.py, ảnh embedded qua extract-images.py, shape/annotation fallback render qua render-sheet.py + image-analyze.
---

## Cơ chế (spec mục 6.3)

1. `python3 scripts/extract-cells.py <file.xlsx>` — value + font_color + strike + fill_color +
   comment, đọc chính xác từ XML, KHÔNG phải vision.
2. Ý nghĩa định dạng (đỏ = gì, gạch ngang = gì) — KHÔNG đoán. Lần đầu quan sát pattern → hỏi
   xác nhận → ghi vào `memory/conventions.md`. Lần sau áp dụng luôn, không hỏi lại. Ô có định
   dạng lạ chưa từng xác nhận → flag riêng, không áp quy ước cũ lên nó.
3. `python3 scripts/extract-images.py <file.xlsx> <out_dir>` — ảnh dán trong sheet, bytes +
   vùng ô neo (KHÔNG phải 1 ô chính xác — nói rõ giới hạn này khi trích dẫn).
4. Shape/textbox/mũi tên annotation `extract-images.py` không đọc được → `python3
   scripts/render-sheet.py <file.xlsx> <out_dir>`, chain kết quả (PDF/ảnh) sang skill
   `image-analyze`.
5. Report cuối gộp 2 loại nguồn, KHÔNG trình bày ngang hàng: phần cell-text (chính xác tuyệt
   đối) và phần ảnh/shape (qua vision, gắn nhãn "đọc bằng ảnh, chưa chắc 100%").

## Dùng chung với `qa-tone-brse`

`extract-cells.py` cũng là script `qa-tone-brse` dùng để đọc lại Q&A list Excel — không có
bản sao thứ 2 của script này ở đâu khác.
