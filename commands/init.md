---
name: init
description: Scaffold documents/, templates/, memory/, CLAUDE.md for a new BrSE project in the current directory
---

Run the following steps in the current directory (the user's project directory, NOT the plugin repo):

1. If `memory/` already exists — stop, ask the user whether to overwrite, do not continue on your own.
2. Create the directories: `documents/`, `templates/`, `memory/`.
3. Create `templates/README.md` with this content:
   "Bỏ vào đây mẫu report/slide/DD riêng của khách (font, màu, cấu trúc cột). Skill report-gen/detail-design-jp sẽ đọc file trong thư mục này nếu có, dùng mặc định nếu chưa có."
4. Create 4 files in `memory/`, each with only a title line + schema guidance (empty, no real data yet). Content stays in Vietnamese — these are working files for the project itself, not plugin documentation:

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

5. Create `CLAUDE.md` at the project root (if it doesn't exist yet — if it does, append instead of overwriting):

   ```markdown
   ## brse-toolkit memory

   Trước khi chạy bất kỳ skill nào của brse-toolkit, đọc `memory/parties.md`,
   `memory/glossary.md`, `memory/conventions.md`, `memory/decisions-log.md`.

   Khi phát hiện thông tin mới (thuật ngữ, quy ước, quan hệ giữa các bên, quyết định QA) —
   xác nhận 1 câu ngắn với user, rồi **ghi vào file tương ứng ngay lập tức**, trước khi làm
   việc khác. Không gộp nhiều xác nhận lại ghi 1 lần cuối session — hội thoại có thể bị nén,
   file thì không.
   ```

   (This injected block also stays in Vietnamese: it configures the project's own `CLAUDE.md`, addressed to whoever works in that project, not to the plugin's documentation.)

6. Check whether the current directory is already a git repo (`git rev-parse --is-inside-work-tree`).
   If not, run `git init` — the anti-staleness mechanism in `cross-check` needs git
   history to retrieve prior versions when comparing documents.
7. Report back to the user: done, list the files/directories just created.
