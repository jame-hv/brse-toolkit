---
name: init
description: Scaffold documents/, templates/, memory/, CLAUDE.md for a new BrSE project in the current directory
---

Chạy các bước sau trong thư mục hiện tại (thư mục dự án của user, KHÔNG phải repo plugin):

1. Nếu đã tồn tại `memory/` — dừng lại, hỏi user có muốn ghi đè hay không, không tự ý chạy tiếp.
2. Tạo các thư mục: `documents/`, `templates/`, `memory/`.
3. Tạo `templates/README.md` với nội dung:
   "Bỏ vào đây mẫu report/slide/DD riêng của khách (font, màu, cấu trúc cột). Skill report-gen/detail-design-jp sẽ đọc file trong thư mục này nếu có, dùng mặc định nếu chưa có."
4. Tạo 4 file trong `memory/`, mỗi file chỉ có 1 dòng tiêu đề + hướng dẫn schema (rỗng, chưa có dữ liệu thật):

   `memory/parties.md`:
   ```
   # Parties — ai là ai trong dự án này

   Schema mỗi entry:
   - <Tên bên> — vai trò: <khách/vendor/team mình/...> — xưng hô mặc định: <chưa xác nhận, dùng "chúng tôi"/"quý vị" cho tới khi có>
   ```

   `memory/glossary.md`:
   ```
   # Glossary JP-VI

   Schema mỗi entry:
   - <term JP> → "<translation VI>" — nguồn: <file>, <version/ngày>, xác nhận <ngày>
   ```

   `memory/conventions.md`:
   ```
   # Conventions — quy ước format phát sinh

   Schema mỗi entry:
   - <mô tả định dạng, vd "chữ đỏ trong Excel sheet X"> → <ý nghĩa đã xác nhận> — nguồn: <file>, xác nhận <ngày>
   ```

   `memory/decisions-log.md`:
   ```
   # Decisions log — lớp phủ lên DD/spec chính thức

   Schema mỗi entry:
   - Quyết định: <nội dung, ghi rõ phạm vi áp dụng>
     Nguồn: QA #<id>, ngày <date>
     Trạng thái trong doc chính thức: <ĐÃ update đầy đủ / CHỈ update 1 phần / CHƯA update>
   ```

5. Tạo `CLAUDE.md` ở root thư mục (nếu chưa có — nếu đã có, append thay vì ghi đè):

   ```markdown
   ## brse-toolkit memory

   Trước khi chạy bất kỳ skill nào của brse-toolkit, đọc `memory/parties.md`,
   `memory/glossary.md`, `memory/conventions.md`, `memory/decisions-log.md`.

   Khi phát hiện thông tin mới (thuật ngữ, quy ước, quan hệ giữa các bên, quyết định QA) —
   xác nhận 1 câu ngắn với user, rồi **ghi vào file tương ứng ngay lập tức**, trước khi làm
   việc khác. Không gộp nhiều xác nhận lại ghi 1 lần cuối session — hội thoại có thể bị nén,
   file thì không.
   ```

6. Kiểm tra thư mục hiện tại đã là git repo chưa (`git rev-parse --is-inside-work-tree`).
   Nếu chưa, chạy `git init` — cơ chế chống-stale của `cross-check` cần git history để
   lấy lại version cũ khi so sánh tài liệu.
7. Báo cho user: đã tạo xong, liệt kê các file/thư mục vừa tạo.
