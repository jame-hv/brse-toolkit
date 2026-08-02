---
name: detail-design-jp
description: Detail design theo khung SI Nhật chuẩn, hoặc template riêng của khách nếu có. Nội dung lấy từ code-to-business + decisions-log, không tự bịa.
---

## Trước khi chạy

Check `documents/`, `templates/`, `memory/` trong thư mục dự án hiện tại có tồn tại chưa:
- Chỉ thiếu 1 thư mục phụ (`documents/` hoặc `templates/`), `memory/` vẫn có → tự tạo thư mục trống, dùng mặc định cho lần này, báo 1 dòng rõ ràng. Không cần hỏi.
- Thiếu `memory/` → **không được** âm thầm chạy tiếp. Dừng lại, hỏi: "Dự án chưa init (thiếu `memory/`) — chạy `/brse-toolkit:init` trước để lưu được cho lần sau, hay tiếp tục 1 lần không lưu gì?"

## Nguồn nội dung (spec mục 6.11)

- Nội dung lấy từ `code-to-business` (nếu viết DD từ code có sẵn) + `memory/decisions-log.md`
  (quyết định/requirements đã chốt) — KHÔNG tự bịa nội dung kỹ thuật.
- Trước khi tin nội dung DD hiện có (nếu đang cập nhật DD cũ) — check
  `memory/decisions-log.md` trước, DD có thể chưa phản ánh quyết định QA gần nhất.

## Template

2 loại template khác chỗ nhau, không nhầm lẫn (spec mục 7):

- **Template riêng của khách** — nằm trong `templates/` của **thư mục dự án hiện tại** (nơi
  đang chạy Claude Code). Có → dùng thay khung mặc định, giữ nguyên cấu trúc khách quen dùng.
- **Khung mặc định đóng gói sẵn trong plugin** — chưa có template khách thì dùng
  `${CLAUDE_PLUGIN_ROOT}/skills/detail-design-jp/templates/detail-design-jp-template.md`
  (khung SI Nhật chuẩn: 改訂履歴, 概要/目的, 処理概要+フロー, 画面レイアウト+項目定義,
  入力チェック, テーブル定義, エラー処理). File này KHÔNG nằm trong thư mục dự án — đừng tìm
  nó ở `templates/`.

## Tính đầy đủ

Mọi mục trong khung phải có nội dung hoặc ghi rõ "該当なし" (không áp dụng) — KHÔNG được
âm thầm bỏ trống 1 mục mà không giải thích.

## Output

Xuất file qua `report-gen` (Word/Excel theo định dạng khách quen dùng).

## Trước khi trả lời

Áp `verify-output` — chạy
`${CLAUDE_PLUGIN_ROOT}/skills/verify-output/scripts/lint-hedge-words.py` trên draft response
trước khi gửi.
