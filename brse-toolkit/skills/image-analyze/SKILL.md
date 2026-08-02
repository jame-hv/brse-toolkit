---
name: image-analyze
description: Đọc screenshot/sơ đồ tay/ảnh lỗi — OCR trước cho chữ in/UI text, vision chỉ lo bố cục/mũi tên/chữ viết tay.
---

## Cơ chế (spec mục 6.4)

1. `python3 ${CLAUDE_PLUGIN_ROOT}/skills/image-analyze/scripts/ocr-pass.py <image> jpn` — chữ in/UI text, đáng tin hơn để vision tự đọc.
   Nếu ảnh có chữ tiếng Anh/Việt, gọi lại với `lang=eng`/`vie`.
2. Vision chỉ đảm nhiệm phần OCR không làm được: bố cục, hướng mũi tên, chữ viết tay.
3. Luôn gắn confidence rõ ràng (dùng field `confidence` từ OCR khi có), KHÔNG trình bày ngang
   hàng với structured data từ script khác (vd `extract-cells.py`).

## Output

Mô tả structured (thành phần UI, luồng mũi tên, text trong ảnh) để đối chiếu với spec bằng
chữ — điểm nghi vấn nếu ảnh không khớp spec, theo `verify-output`.
