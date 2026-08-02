# brse-toolkit

Claude Code plugin cho công việc BrSE hàng ngày: dịch JP-VI, đối chiếu spec/code/Excel,
tạo report/slide/DD, quản lý Q&A — với bộ nhớ bền theo từng dự án.

## Cài đặt

    claude plugin install ./brse-toolkit

## Bắt đầu 1 dự án mới

Mở Claude Code trong thư mục dự án (khách/project cụ thể), chạy:

    /brse-toolkit:init

Lệnh này tạo `documents/`, `templates/`, `memory/`, `CLAUDE.md` trong thư mục hiện tại
và `git init` nếu chưa phải git repo. Xem `docs/superpowers/specs/2026-08-02-brse-toolkit-design.md`
trong repo nguồn để hiểu đầy đủ kiến trúc.

## Dependencies

    pip install -r requirements.txt

Ngoài ra cần cài trên máy: `ripgrep` (rg), `tesseract-ocr` + gói ngôn ngữ `jpn`,
`libreoffice` (dùng cho fallback render Excel có shape/annotation).
