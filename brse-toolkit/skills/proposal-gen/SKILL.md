---
name: proposal-gen
description: Requirements → proposal. Bản nội bộ kỹ thuật và bản khách là 2 lần soạn nội dung khác nhau, không phải 1 bản rồi rút gọn cơ học.
---

## Trước khi chạy

Check `documents/`, `templates/`, `memory/` trong thư mục dự án hiện tại có tồn tại chưa:
- Chỉ thiếu 1 thư mục phụ (`documents/` hoặc `templates/`), `memory/` vẫn có → tự tạo thư mục trống, dùng mặc định cho lần này, báo 1 dòng rõ ràng. Không cần hỏi.
- Thiếu `memory/` → **không được** âm thầm chạy tiếp. Dừng lại, hỏi: "Dự án chưa init (thiếu `memory/`) — chạy `/brse-toolkit:init` trước để lưu được cho lần sau, hay tiếp tục 1 lần không lưu gì?"

## Trigger

Có requirements (spec, email khách, note họp) cần tổng hợp thành proposal.

## Cơ chế (spec mục 6.8)

1. Trích yêu cầu từ nguồn (`documents/`, `memory/decisions-log.md`) → nhóm theo hạng mục
   (scope, ràng buộc, rủi ro, ước lượng).
2. Áp mô hình relay (spec mục 2) ngay ở bước soạn NỘI DUNG, không chỉ trình bày:
   - **Bản nội bộ kỹ thuật**: giữ chi tiết/thuật ngữ kỹ thuật đầy đủ, dùng để chốt scope với
     team dev trước khi gửi khách.
   - **Bản gửi khách**: giản lược, không dùng thuật ngữ nội bộ chưa giải thích, không dịch
     nguyên xưng hô nội bộ. Nhiều phương án → chain qua `brainstorm-brse` để có trade-off rõ.
3. Mỗi mục trong cả 2 bản trỏ lại nguồn requirement gốc.
4. Xuất file qua `report-gen`.

## Output

Proposal nội bộ + proposal bản khách (nếu được yêu cầu bản khách).

Trước khi trả lời, áp `verify-output` — chạy
`${CLAUDE_PLUGIN_ROOT}/skills/verify-output/scripts/lint-hedge-words.py` trên cả 2 bản draft
(bản gửi khách càng phải sạch từ mơ hồ + đủ nguồn).
