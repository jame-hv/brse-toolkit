---
name: detail-design-jp
description: Detail design theo khung SI Nhật chuẩn, hoặc template riêng của khách nếu có. Nội dung lấy từ code-to-business + decisions-log, không tự bịa.
---

## Nguồn nội dung (spec mục 6.11)

- Nội dung lấy từ `code-to-business` (nếu viết DD từ code có sẵn) + `memory/decisions-log.md`
  (quyết định/requirements đã chốt) — KHÔNG tự bịa nội dung kỹ thuật.
- Trước khi tin nội dung DD hiện có (nếu đang cập nhật DD cũ) — check
  `memory/decisions-log.md` trước, DD có thể chưa phản ánh quyết định QA gần nhất.

## Template

- Có template khách trong `templates/` (thư mục dự án) → dùng thay khung mặc định, giữ
  nguyên cấu trúc khách quen dùng.
- Chưa có → dùng `templates/detail-design-jp-template.md` đóng gói sẵn trong skill này
  (khung SI Nhật chuẩn: 改訂履歴, 概要/目的, 処理概要+フロー, 画面レイアウト+項目定義,
  入力チェック, テーブル定義, エラー処理).

## Tính đầy đủ

Mọi mục trong khung phải có nội dung hoặc ghi rõ "該当なし" (không áp dụng) — KHÔNG được
âm thầm bỏ trống 1 mục mà không giải thích.

## Output

Xuất file qua `report-gen` (Word/Excel theo định dạng khách quen dùng).
