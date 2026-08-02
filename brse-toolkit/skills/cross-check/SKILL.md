---
name: cross-check
description: Đối chiếu 2 nguồn (spec cũ/mới, code/spec, Excel/Excel). Phát hiện memory/ bị stale khi tài liệu nguồn update. Đối chiếu decisions-log.md với DD khi DD được update.
---

## Trước khi chạy

Check `documents/`, `templates/`, `memory/` trong thư mục dự án hiện tại có tồn tại chưa:
- Chỉ thiếu 1 thư mục phụ (`documents/` hoặc `templates/`), `memory/` vẫn có → tự tạo thư mục trống, dùng mặc định cho lần này, báo 1 dòng rõ ràng. Không cần hỏi.
- Thiếu `memory/` → **không được** âm thầm chạy tiếp. Dừng lại, hỏi: "Dự án chưa init (thiếu `memory/`) — chạy `/brse-toolkit:init` trước để lưu được cho lần sau, hay tiếp tục 1 lần không lưu gì?"

## Lấy version cũ của tài liệu từ git history (spec mục 3)

`/brse-toolkit:init` chạy `git init` chính là để phục vụ bước này — bản cũ của tài liệu KHÔNG
nằm ở file trùng tên kiểu `spec_v2.xlsx`/`spec_v3.xlsx`, mà nằm trong git history của thư mục
dự án. Trước khi diff:

1. Xem lịch sử commit của file: `git -C <project-dir> log --oneline -- documents/<relative-path>`.
2. Trích bản cũ ra file tạm để diff với bản hiện tại:

       git -C <project-dir> show <rev>:documents/<relative-path> > /tmp/<tên>-old.<ext>

   (`<rev>` = commit hash/tag của bản khách gửi trước đó; với file nhị phân như `.xlsx` nhớ
   redirect ra file, không đọc thẳng ra stdout.)
3. Parse cả bản cũ (file tạm) lẫn bản mới theo adapter tương ứng bên dưới rồi mới diff.

Thư mục dự án chưa phải git repo, hoặc file chưa từng được commit → **không có** bản cũ để so.
Nói thẳng giới hạn này trong output, không đoán bản cũ trông thế nào.

## 3 loại cặp nguồn (spec mục 6.2)

- **Spec cũ vs spec mới**: parse cả 2 thành `[{"key": "<field/trang>", "value": "<nội dung>"}]`,
  chạy `python3 ${CLAUDE_PLUGIN_ROOT}/skills/cross-check/scripts/diff-structured.py old.json new.json`.
- **Code vs spec**: lấy logic thực tế từ `code-to-business`, đối chiếu mô tả trong spec bằng
  cùng cơ chế trên.
- **Excel vs Excel**: dùng `${CLAUDE_PLUGIN_ROOT}/skills/excel-analyze/scripts/extract-cells.py`
  trên cả 2 file, convert sang `{key, value}` theo cột khóa (key column) của bảng, rồi diff.

**Giới hạn thật**: chỉ so được phần đã convert được sang `{key, value}`. Văn xuôi tự do không
so structured được — hạ xuống so câu-với-câu, độ tin cậy thấp hơn, phải nói rõ trong output
đang dùng chế độ nào.

## Xử lý batch (nhiều đơn vị độc lập)

Nhiều cặp nguồn độc lập cần đối chiếu trong cùng 1 yêu cầu (vd 5 file spec đều có bản mới) →
dispatch song song (spec mục 11), mỗi cặp 1 subagent. Mỗi subagent tự đọc `memory/` liên quan
trước khi so. Agent chính gom kết quả, dedupe các entry "cần re-verify" trùng nhau rồi hỏi
user 1 lần. **Subagent không bao giờ tự ghi `memory/`.**

## Phát hiện `memory/` stale

Mỗi entry trong `memory/*.md` có nguồn + version/ngày (spec mục 3). Khi diff phát hiện 1 field
đã đổi giữa bản cũ/mới, tìm trong `memory/*.md` entry nào trích nguồn đúng field đó ở bản cũ →
gắn nhãn "cần re-verify" ngay trong response, không tự tin dùng tiếp giá trị cũ.

## Đối chiếu `decisions-log.md` với DD

Khi DD/spec được update: với mỗi entry trong `memory/decisions-log.md` có "Trạng thái trong
doc chính thức" khác "ĐÃ update đầy đủ", kiểm bản DD mới đã phản ánh quyết định đó chưa —
nếu có, hỏi user xác nhận đổi trạng thái entry; nếu chưa, tiếp tục flag.

## Trước khi trả lời

Áp `verify-output` — chạy
`${CLAUDE_PLUGIN_ROOT}/skills/verify-output/scripts/lint-hedge-words.py` trên draft response
trước khi gửi.
