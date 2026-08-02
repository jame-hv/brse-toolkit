---
name: cross-check
description: Đối chiếu 2 nguồn (spec cũ/mới, code/spec, Excel/Excel). Phát hiện memory/ bị stale khi tài liệu nguồn update. Đối chiếu decisions-log.md với DD khi DD được update.
---

## 3 loại cặp nguồn (spec mục 6.2)

- **Spec cũ vs spec mới**: parse cả 2 thành `[{"key": "<field/trang>", "value": "<nội dung>"}]`,
  chạy `python3 scripts/diff-structured.py old.json new.json`.
- **Code vs spec**: lấy logic thực tế từ `code-to-business`, đối chiếu mô tả trong spec bằng
  cùng cơ chế trên.
- **Excel vs Excel**: dùng `../excel-analyze/scripts/extract-cells.py` trên cả 2 file, convert
  sang `{key, value}` theo cột khóa (key column) của bảng, rồi diff.

**Giới hạn thật**: chỉ so được phần đã convert được sang `{key, value}`. Văn xuôi tự do không
so structured được — hạ xuống so câu-với-câu, độ tin cậy thấp hơn, phải nói rõ trong output
đang dùng chế độ nào.

## Phát hiện `memory/` stale

Mỗi entry trong `memory/*.md` có nguồn + version/ngày (spec mục 3). Khi diff phát hiện 1 field
đã đổi giữa bản cũ/mới, tìm trong `memory/*.md` entry nào trích nguồn đúng field đó ở bản cũ →
gắn nhãn "cần re-verify" ngay trong response, không tự tin dùng tiếp giá trị cũ.

## Đối chiếu `decisions-log.md` với DD

Khi DD/spec được update: với mỗi entry trong `memory/decisions-log.md` có "Trạng thái trong
doc chính thức" khác "ĐÃ update đầy đủ", kiểm bản DD mới đã phản ánh quyết định đó chưa —
nếu có, hỏi user xác nhận đổi trạng thái entry; nếu chưa, tiếp tục flag.
