---
name: research-jp-tech
description: Research công nghệ/quy định/best practice, ưu tiên nguồn tiếng Nhật/chính thống.
---

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
