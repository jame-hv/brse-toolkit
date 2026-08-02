---
name: jp-vi-translate
description: Dịch JP-VI. Field/thuật ngữ cố định dùng glossary script; văn xuôi/email/QA dịch theo nghĩa + relay model, KHÔNG dùng mô hình pass-1-literal/pass-2-naturalize.
---

## Trước khi dịch bất kỳ đoạn nào

1. Đọc `memory/parties.md` — ai nói, dịch cho ai đọc (mô hình relay, spec mục 2).
2. Chạy `python3 scripts/check-glossary.py <text> memory/glossary.md` — lấy các thuật ngữ đã
   chốt, dùng đúng bản dịch đó, không tự đặt từ khác.
3. Thuật ngữ xuất hiện trong text nhưng KHÔNG có trong glossary → flag "chưa có trong
   glossary, đang tạm dịch X, cần xác nhận" — không âm thầm tự quyết.

## Field/thuật ngữ cố định

Dùng nguyên bản dịch từ `check-glossary.py`. Không đổi.

## Văn xuôi / email / QA (spec mục 6.6 — đã test thật, mô hình 2-pass cũ cho kết quả tệ hơn máy dịch thường)

1. Đọc hết đoạn để hiểu **mục đích giao tiếp**, không dịch từng mệnh đề.
2. Dịch thẳng theo nghĩa + đúng giọng văn Việt business — KHÔNG bám ranh giới câu/cấu trúc
   mệnh đề tiếng Nhật, KHÔNG dịch literal từ đệm mềm hóa giọng điệu (というか/ということです).
3. Áp mô hình relay: đại từ nhân xưng nguồn (私たち/chúng tôi) → đổi thành tên bên cụ thể khi
   relay sang phía khác, không dịch nguyên. Chưa xác nhận quan hệ giữa các bên trong
   `memory/parties.md` → mặc định "chúng tôi"/"quý vị" trung tính, không tự chọn em/anh/chị.
4. Fact-check tách riêng: liệt kê fact/quyết định chính (không phải từng câu) kèm nguồn, đặt
   SAU bản dịch — không nhét giữa câu văn.
5. Từ chêm vào chỉ để câu Việt có ngữ pháp đúng (không map được token nguồn) → đánh dấu rõ
   (vd ngoặc vuông `[...]`), không để lẫn như thể có nguồn.

## Sau khi dịch xong 1 tài liệu

Chạy `check-consistency.py` trên danh sách `{term, translation_used}` đã áp dụng trong tài
liệu — nếu có `conflicts`, sửa cho nhất quán trước khi trả lời.

Thuật ngữ mới được xác nhận trong lúc dịch → ghi ngay vào `memory/glossary.md` (không trì
hoãn, xem CLAUDE.md rule).
