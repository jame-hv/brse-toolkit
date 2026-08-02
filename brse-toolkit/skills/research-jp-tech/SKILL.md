---
name: research-jp-tech
description: Research công nghệ/quy định/best practice, ưu tiên nguồn tiếng Nhật/chính thống.
---

## Trước khi chạy

Check `documents/`, `templates/`, `memory/` trong thư mục dự án hiện tại có tồn tại chưa:
- Chỉ thiếu 1 thư mục phụ (`documents/` hoặc `templates/`), `memory/` vẫn có → tự tạo thư mục trống, dùng mặc định cho lần này, báo 1 dòng rõ ràng. Không cần hỏi.
- Thiếu `memory/` → **không được** âm thầm chạy tiếp. Dừng lại, hỏi: "Dự án chưa init (thiếu `memory/`) — chạy `/brse-toolkit:init` trước để lưu được cho lần sau, hay tiếp tục 1 lần không lưu gì?"

## Thứ tự ưu tiên nguồn (spec mục 6.12)

1. Domain chính phủ/tổ chức Nhật (`.go.jp`, hiệp hội ngành).
2. Tài liệu hãng (nếu research công nghệ cụ thể).
3. Blog kỹ thuật uy tín.
4. Nguồn tiếng Anh/Việt bổ sung sau cùng.

## Cơ chế

- Mỗi kết luận phải kèm URL + ngày truy cập (áp `verify-output`) — không tóm tắt rồi bỏ nguồn.
- Nhiều nguồn độc lập → search song song (spec mục 11), agent chính tổng hợp + verify trước
  khi trả lời, không để mỗi subagent tự kết luận riêng rồi ghép thô.
- Kết quả liên quan tới quy ước/quyết định của dự án đang làm → hỏi có lưu vào
  `memory/decisions-log.md` không, tránh phải research lại lần sau cho cùng 1 vấn đề.

## Output

Tổng hợp kèm nguồn (URL + ngày), không có nguồn thì không đưa vào kết luận.
