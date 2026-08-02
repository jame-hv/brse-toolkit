# brse-toolkit Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the `brse-toolkit` Claude Code plugin per `docs/superpowers/specs/2026-08-02-brse-toolkit-design.md` — 12 skills + `commands/init.md`, with real scripts (not prompt-only) for every skill the spec requires one for.

**Architecture:** Single Claude Code plugin repo. Skills are `SKILL.md` (instructions loaded into the agent's context) + `scripts/*.py` (deterministic work: parsing, diffing, OCR — the agent runs these via Bash, never re-implements their logic by "reading and guessing"). Per-project runtime state (`memory/`, `documents/`, `templates/`) is NOT part of this repo — it's created by `commands/init.md` inside whatever project directory the user runs it in. See spec mục 3, 7.

**Tech Stack:** Python 3.10+, `pytest` for script tests, `openpyxl` (Excel), `python-pptx`/`python-docx` (report output), `pytesseract` + Pillow (OCR), `chardet` (encoding detection). External binaries used at runtime (not needed to write/test most code): `rg` (ripgrep, for `extract-refs.py`), `tesseract` + `jpn` traineddata (for `ocr-pass.py`), `libreoffice` (for the Excel shape/annotation fallback render).

## Global Constraints

- Every script is a standalone CLI (`argv` in, JSON on stdout, non-zero exit on finding problems where the spec calls for blocking) — this is what lets a `SKILL.md` tell the agent "run `scripts/x.py args` and read the JSON," per spec mục 1's "script deterministic đứng sau."
- Every script ships with a `pytest` test file in `scripts/tests/` — no script is "done" without a passing test using synthetic fixtures built in the test itself (no dependency on real client files, per spec mục 10's honesty note that real data isn't available yet).
- `memory/`, `documents/`, `templates/` are **never** created inside this plugin repo — only referenced by path in code/docs. Spec mục 3, "Tách biệt khỏi repo plugin."
- Vietnamese strings in scripts/tests use UTF-8 source files; string literals are plain UTF-8, no escaping needed.
- Commit after every task.

---

### Task 1: Plugin scaffold

**Files:**
- Create: `brse-toolkit/.claude-plugin/plugin.json`
- Create: `brse-toolkit/README.md`
- Create: `brse-toolkit/requirements.txt`

**Interfaces:**
- Produces: the repo root all later tasks add files under (`brse-toolkit/skills/`, `brse-toolkit/commands/`).

- [ ] **Step 1: Create directory skeleton**

Run:
```bash
mkdir -p brse-toolkit/.claude-plugin brse-toolkit/skills brse-toolkit/commands
```

- [ ] **Step 2: Write `plugin.json`**

```json
{
  "name": "brse-toolkit",
  "version": "0.1.0",
  "description": "Bo cong cu BrSE: dich JP-VI, doi chieu spec/code/excel, verify output, report gen, quan ly memory theo du an",
  "author": { "name": "TODO: dien ten that" },
  "keywords": ["brse", "japanese", "translation", "spec-analysis"]
}
```

(The `author.name` placeholder is intentional — this is data only the plugin owner can fill in, not a code placeholder; fill in before first `claude plugin install`.)

- [ ] **Step 3: Write `requirements.txt`**

```
openpyxl>=3.1
python-pptx>=0.6.23
python-docx>=1.1
pytesseract>=0.3.10
Pillow>=10.0
chardet>=5.2
pytest>=8.0
```

- [ ] **Step 4: Write `README.md`**

```markdown
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
```

- [ ] **Step 5: Commit**

```bash
git add brse-toolkit/.claude-plugin brse-toolkit/README.md brse-toolkit/requirements.txt
git commit -m "chore: scaffold brse-toolkit plugin skeleton"
```

---

### Task 2: `commands/init.md` — per-project scaffolding command

**Files:**
- Create: `brse-toolkit/commands/init.md`

**Interfaces:**
- Consumes: nothing (reads the current working directory only).
- Produces: in the directory the user runs it from — `documents/`, `templates/` (+ `templates/README.md`), `memory/{parties,glossary,conventions,decisions-log}.md`, `CLAUDE.md`, and a `git init` if not already a repo. This is the structure every other skill's `SKILL.md` assumes exists (spec mục 3).

This is a slash-command file (markdown with frontmatter), not a Python script — Claude Code executes the instructions directly using its own tools (Bash/Write), so there is no separate script to unit test. The "test" for this task is a manual dry run (Step 3).

- [ ] **Step 1: Write `commands/init.md`**

```markdown
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
```

- [ ] **Step 2: Commit**

```bash
git add brse-toolkit/commands/init.md
git commit -m "feat: add /brse-toolkit:init project scaffolding command"
```

- [ ] **Step 3: Manual dry run (not automatable — no real project dir yet)**

In a scratch directory, follow the steps in `init.md` by hand once to confirm the file contents above are internally consistent (schema in `memory/*.md` matches what Task 4+ scripts expect). This substitutes for an automated test since this task has no script logic to unit-test.

---

### Task 3: `verify-output` skill — `lint-hedge-words.py`

**Files:**
- Create: `brse-toolkit/skills/verify-output/SKILL.md`
- Create: `brse-toolkit/skills/verify-output/scripts/lint-hedge-words.py`
- Test: `brse-toolkit/skills/verify-output/scripts/tests/test_lint_hedge_words.py`

**Interfaces:**
- Produces: `lint-hedge-words.py <file>` (or stdin) → JSON `{"violations": [...], "ok": bool}` on stdout, exit code 1 if violations found, 0 if clean. `violations` entries: `{"type": "hedge_word", "word": str, "sentence": str}` or `{"type": "missing_source", "line": str}`.

- [ ] **Step 1: Write the failing test**

```python
# brse-toolkit/skills/verify-output/scripts/tests/test_lint_hedge_words.py
import json
import subprocess
import sys
import pathlib

SCRIPT = pathlib.Path(__file__).resolve().parents[1] / "lint-hedge-words.py"


def run(text):
    result = subprocess.run(
        [sys.executable, str(SCRIPT)],
        input=text, capture_output=True, text=True, encoding="utf-8",
    )
    return json.loads(result.stdout), result.returncode


def test_detects_hedge_word():
    out, code = run("- Trường email có lẽ là bắt buộc nhập.")
    assert code == 1
    assert any(v["type"] == "hedge_word" and v["word"] == "có lẽ" for v in out["violations"])


def test_passes_clean_bullet_with_source():
    out, code = run('- Trường email bắt buộc nhập (nguồn: spec.xlsx, sheet ScreenA, dòng 12).')
    assert code == 0
    assert out["violations"] == []


def test_detects_missing_source_on_bullet_claim():
    out, code = run("- Trường email bắt buộc nhập.")
    assert code == 1
    assert any(v["type"] == "missing_source" for v in out["violations"])


def test_question_bullets_are_not_flagged_for_missing_source():
    out, code = run("- Trường email có bắt buộc không?")
    assert code == 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest brse-toolkit/skills/verify-output/scripts/tests/test_lint_hedge_words.py -v`
Expected: FAIL — `lint-hedge-words.py` does not exist yet.

- [ ] **Step 3: Write the implementation**

```python
#!/usr/bin/env python3
# brse-toolkit/skills/verify-output/scripts/lint-hedge-words.py
"""Lint a draft response for banned hedge words and unsourced bullet claims.

Usage: lint-hedge-words.py [file]   (reads stdin if no file given)
Exit 0 if clean, 1 if any violation found.
"""
import json
import re
import sys

HEDGE_WORDS = ["có lẽ", "chắc là", "hình như", "có thể"]
SOURCE_TAG_RE = re.compile(r"\(nguồn:[^)]*\)")


def split_sentences(text: str) -> list[str]:
    parts = re.split(r"(?<=[.!?])\s+", text.strip())
    return [p for p in parts if p.strip()]


def lint_hedge_words(text: str) -> list[dict]:
    violations = []
    for sentence in split_sentences(text):
        lower = sentence.lower()
        for word in HEDGE_WORDS:
            if word in lower:
                violations.append({"type": "hedge_word", "word": word, "sentence": sentence})
    return violations


def lint_missing_sources(text: str) -> list[dict]:
    missing = []
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("- ") and "?" not in stripped:
            if not SOURCE_TAG_RE.search(stripped):
                missing.append({"type": "missing_source", "line": stripped})
    return missing


def main() -> None:
    if len(sys.argv) > 1:
        with open(sys.argv[1], encoding="utf-8") as f:
            text = f.read()
    else:
        text = sys.stdin.read()

    violations = lint_hedge_words(text) + lint_missing_sources(text)
    print(json.dumps({"violations": violations, "ok": len(violations) == 0}, ensure_ascii=False, indent=2))
    sys.exit(1 if violations else 0)


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest brse-toolkit/skills/verify-output/scripts/tests/test_lint_hedge_words.py -v`
Expected: PASS (4 tests)

- [ ] **Step 5: Write `SKILL.md`**

```markdown
---
name: verify-output
description: Bắt buộc trước khi trả lời bất kỳ kết luận nào — kiểm tra mỗi claim có nguồn, cấm từ mơ hồ. Chạy cuối mọi skill khác trong brse-toolkit, không gọi tay.
---

## Chính sách (spec mục 6.1)

1. Liệt kê từng câu kết luận trong draft response.
2. Mỗi câu kết luận phải có tag nguồn: `(nguồn: file:dòng)` / `(nguồn: sheet, ô)` / `(nguồn: spec trang X)`.
3. Không gắn được nguồn → viết "chưa xác định được — cần hỏi khách", không viết như sự thật.
4. Cấm từ mơ hồ trong kết luận: "có lẽ", "chắc là", "hình như", "có thể" (không cấm khi đang hỏi lại khách).

## Cơ chế

Trước khi gửi câu trả lời cuối, chạy:

    python3 scripts/lint-hedge-words.py <draft.txt>

Đọc JSON trả về. Nếu `ok: false`, sửa draft cho tới khi sạch violation rồi mới trả lời —
không bỏ qua kết quả script.
```

- [ ] **Step 6: Commit**

```bash
git add brse-toolkit/skills/verify-output
git commit -m "feat: add verify-output skill with lint-hedge-words.py"
```

---

### Task 4: `extract-cells.py` — shared script (built early; canonical home is `excel-analyze`, but `qa-tone-brse` in Task 5 depends on it)

**Files:**
- Create: `brse-toolkit/skills/excel-analyze/scripts/extract-cells.py`
- Test: `brse-toolkit/skills/excel-analyze/scripts/tests/test_extract_cells.py`

**Interfaces:**
- Produces: `extract-cells.py <xlsx_path>` → JSON `{"<sheet_name>": [{"cell": "A1", "value": ..., "font_color": str|null, "strike": bool, "fill_color": str|null, "comment": str|null}, ...], ...}`.
- Consumed by: Task 5 (`qa-tone-brse`), Task 9 (`excel-analyze` SKILL.md).

> Note on task order: the spec (mục 5, 6.7) has `qa-tone-brse` (Giai đoạn 1) reuse `extract-cells.py`, whose canonical home is `excel-analyze` (Giai đoạn 2). Building it here, before Task 5, resolves that cross-phase dependency without duplicating the script.

- [ ] **Step 1: Write the failing test**

```python
# brse-toolkit/skills/excel-analyze/scripts/tests/test_extract_cells.py
import json
import subprocess
import sys
import pathlib

import openpyxl
from openpyxl.styles import Font, PatternFill
from openpyxl.comments import Comment

SCRIPT = pathlib.Path(__file__).resolve().parents[1] / "extract-cells.py"


def make_fixture(path):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "ScreenA"
    ws["A1"] = "必須項目"
    ws["A1"].font = Font(color="FFFF0000", strike=True)
    ws["A1"].fill = PatternFill(fill_type="solid", fgColor="FFFFFF00")
    ws["A1"].comment = Comment("cần xác nhận lại", "brse")
    ws["B1"] = "登録"
    wb.save(path)


def run(xlsx_path):
    result = subprocess.run(
        [sys.executable, str(SCRIPT), str(xlsx_path)],
        capture_output=True, text=True, encoding="utf-8",
    )
    return json.loads(result.stdout), result.returncode


def test_extracts_value_format_and_comment(tmp_path):
    xlsx = tmp_path / "fixture.xlsx"
    make_fixture(xlsx)
    out, code = run(xlsx)
    assert code == 0
    cells = {c["cell"]: c for c in out["ScreenA"]}
    assert cells["A1"]["value"] == "必須項目"
    assert cells["A1"]["strike"] is True
    assert cells["A1"]["comment"] == "cần xác nhận lại"
    assert cells["B1"]["value"] == "登録"
    assert cells["B1"]["strike"] is False


def test_empty_cells_are_skipped(tmp_path):
    xlsx = tmp_path / "fixture.xlsx"
    make_fixture(xlsx)
    out, _ = run(xlsx)
    coords = {c["cell"] for c in out["ScreenA"]}
    assert "C1" not in coords
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest brse-toolkit/skills/excel-analyze/scripts/tests/test_extract_cells.py -v`
Expected: FAIL — script does not exist.

- [ ] **Step 3: Write the implementation**

```python
#!/usr/bin/env python3
# brse-toolkit/skills/excel-analyze/scripts/extract-cells.py
"""Extract cell values + formatting (color, strike, fill, comment) from an xlsx file.

Usage: extract-cells.py <xlsx_path>
Prints JSON: {"<sheet name>": [{"cell": "A1", "value": ..., "font_color": ..., "strike": ..., "fill_color": ..., "comment": ...}, ...]}
"""
import json
import sys

import openpyxl


def _rgb(color_obj):
    if color_obj is None:
        return None
    rgb = getattr(color_obj, "rgb", None)
    return rgb if isinstance(rgb, str) else None


def extract(path: str) -> dict:
    wb = openpyxl.load_workbook(path, data_only=True)
    sheets = {}
    for ws in wb.worksheets:
        cells = []
        for row in ws.iter_rows():
            for cell in row:
                if cell.value is None:
                    continue
                font = cell.font
                fill = cell.fill
                cells.append({
                    "cell": cell.coordinate,
                    "value": cell.value,
                    "font_color": _rgb(font.color) if font else None,
                    "strike": bool(font.strike) if font else False,
                    "fill_color": _rgb(fill.fgColor) if fill else None,
                    "comment": cell.comment.text.strip() if cell.comment else None,
                })
        sheets[ws.title] = cells
    return sheets


def main() -> None:
    if len(sys.argv) != 2:
        print("usage: extract-cells.py <xlsx_path>", file=sys.stderr)
        sys.exit(2)
    print(json.dumps(extract(sys.argv[1]), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest brse-toolkit/skills/excel-analyze/scripts/tests/test_extract_cells.py -v`
Expected: PASS (2 tests)

- [ ] **Step 5: Commit**

```bash
git add brse-toolkit/skills/excel-analyze/scripts/extract-cells.py brse-toolkit/skills/excel-analyze/scripts/tests/test_extract_cells.py
git commit -m "feat: add extract-cells.py (shared by excel-analyze and qa-tone-brse)"
```

---

### Task 5: `qa-tone-brse` skill

**Files:**
- Create: `brse-toolkit/skills/qa-tone-brse/SKILL.md`

**Interfaces:**
- Consumes: `extract-cells.py` (Task 4), `memory/parties.md`, `memory/glossary.md` (Task 2's scaffolded schema).
- No new script — pure orchestration skill per spec mục 5 ("Các skill không cần script riêng" list does not include `qa-tone-brse`, but its only script dependency is the shared `extract-cells.py` already built).

- [ ] **Step 1: Write `SKILL.md`**

```markdown
---
name: qa-tone-brse
description: Trả lời Q&A cho khách/dev qua chat/ticket tool hoặc Excel Q&A list, đúng văn phong từng kênh. Quản lý luôn QA log trong chính file Excel gửi khách.
---

## Trigger

Cần trả lời câu hỏi từ khách hoặc dev — qua chat/ticket tool (Backlog, Redmine, Chatwork...)
hoặc ghi vào cột trả lời trong Q&A list Excel.

## Trước khi trả lời — bắt buộc

1. Đọc `memory/parties.md` — xác định người hỏi là bên nào, người đọc câu trả lời là bên nào.
   Áp mô hình relay: KHÔNG dịch nguyên đại từ nhân xưng của câu hỏi gốc vào câu trả lời nếu
   người đọc là bên khác — dùng tên bên cụ thể hoặc "chúng tôi"/"quý vị" trung tính.
2. Nếu câu trả lời sẽ ghi vào 1 file Q&A list Excel đã có sẵn: chạy
   `python3 ../excel-analyze/scripts/extract-cells.py <path/to/qa-list.xlsx>` để đọc lại
   toàn bộ câu hỏi/trả lời hiện có.
3. So câu hỏi mới với các câu đã có (text similarity đơn giản — trùng ý, không cần trùng chữ).
   Nếu giống câu đã trả lời rồi → báo lại câu trả lời cũ, KHÔNG tự soạn câu trả lời khác đi.

## Văn phong theo kênh

- **Chat/ticket tool**: ngắn gọn, đi thẳng vào câu trả lời, kính ngữ vừa phải, không mở/đóng
  thư như email.
- **Excel Q&A list**: trang trọng hơn 1 bậc vì là hồ sơ lưu lại chính thức.

Cả 2 kênh đều dùng chung `memory/glossary.md` cho thuật ngữ — không tự đặt từ mới.

## Sau khi trả lời

- Câu trả lời không chắc chắn → gắn nhãn "chưa xác nhận được, cần hỏi khách" (nguyên tắc
  `verify-output`), không tự suy đoán ý khách.
- Nếu câu trả lời này là 1 quyết định mới chưa từng có trong `memory/decisions-log.md` →
  hỏi user có lưu lại không, rồi ghi ngay (không trì hoãn — xem CLAUDE.md rule).
```

- [ ] **Step 2: Commit**

```bash
git add brse-toolkit/skills/qa-tone-brse
git commit -m "feat: add qa-tone-brse skill"
```

---

### Task 6: `cross-check` skill — `diff-structured.py`

**Files:**
- Create: `brse-toolkit/skills/cross-check/SKILL.md`
- Create: `brse-toolkit/skills/cross-check/scripts/diff-structured.py`
- Test: `brse-toolkit/skills/cross-check/scripts/tests/test_diff_structured.py`

**Interfaces:**
- Produces: `diff-structured.py <old.json> <new.json>` → JSON `{"added": [...], "removed": [...], "changed": [...]}`. Input format: `[{"key": str, "value": any}, ...]` — a common shape any adapter (Excel cells, code refs, spec fields) must be converted to before diffing. This script is the generic diff engine; per-source adapters are the calling `SKILL.md`'s job (spec mục 6.2's "adapter riêng theo loại nguồn"), not a separate script — kept out of scope here per YAGNI until a real second source type is tested (spec mục 10 already flags this honestly).

- [ ] **Step 1: Write the failing test**

```python
# brse-toolkit/skills/cross-check/scripts/tests/test_diff_structured.py
import json
import subprocess
import sys
import pathlib

SCRIPT = pathlib.Path(__file__).resolve().parents[1] / "diff-structured.py"


def run(old, new, tmp_path):
    old_file = tmp_path / "old.json"
    new_file = tmp_path / "new.json"
    old_file.write_text(json.dumps(old), encoding="utf-8")
    new_file.write_text(json.dumps(new), encoding="utf-8")
    result = subprocess.run(
        [sys.executable, str(SCRIPT), str(old_file), str(new_file)],
        capture_output=True, text=True, encoding="utf-8",
    )
    return json.loads(result.stdout), result.returncode


def test_detects_added_field(tmp_path):
    old = [{"key": "P101.あいまい検索", "value": "部分一致"}]
    new = [{"key": "P101.あいまい検索", "value": "部分一致"}, {"key": "P102.date_format", "value": "required"}]
    out, code = run(old, new, tmp_path)
    assert code == 0
    assert out["added"] == [{"key": "P102.date_format", "value": "required"}]
    assert out["removed"] == []
    assert out["changed"] == []


def test_detects_changed_value(tmp_path):
    old = [{"key": "P45.登録", "value": "Đăng ký"}]
    new = [{"key": "P45.登録", "value": "Lưu"}]
    out, code = run(old, new, tmp_path)
    assert out["changed"] == [{"key": "P45.登録", "old_value": "Đăng ký", "new_value": "Lưu"}]


def test_detects_removed_field(tmp_path):
    old = [{"key": "P45.登録", "value": "Lưu"}]
    new = []
    out, code = run(old, new, tmp_path)
    assert out["removed"] == [{"key": "P45.登録", "value": "Lưu"}]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest brse-toolkit/skills/cross-check/scripts/tests/test_diff_structured.py -v`
Expected: FAIL — script does not exist.

- [ ] **Step 3: Write the implementation**

```python
#!/usr/bin/env python3
# brse-toolkit/skills/cross-check/scripts/diff-structured.py
"""Diff two structured JSON sources already normalized to [{"key": ..., "value": ...}, ...].

Usage: diff-structured.py <old.json> <new.json>
"""
import json
import sys


def diff(old: list[dict], new: list[dict]) -> dict:
    old_map = {item["key"]: item["value"] for item in old}
    new_map = {item["key"]: item["value"] for item in new}

    added = [{"key": k, "value": v} for k, v in new_map.items() if k not in old_map]
    removed = [{"key": k, "value": v} for k, v in old_map.items() if k not in new_map]
    changed = [
        {"key": k, "old_value": old_map[k], "new_value": new_map[k]}
        for k in old_map.keys() & new_map.keys()
        if old_map[k] != new_map[k]
    ]
    return {"added": added, "removed": removed, "changed": changed}


def main() -> None:
    if len(sys.argv) != 3:
        print("usage: diff-structured.py <old.json> <new.json>", file=sys.stderr)
        sys.exit(2)
    with open(sys.argv[1], encoding="utf-8") as f:
        old = json.load(f)
    with open(sys.argv[2], encoding="utf-8") as f:
        new = json.load(f)
    print(json.dumps(diff(old, new), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest brse-toolkit/skills/cross-check/scripts/tests/test_diff_structured.py -v`
Expected: PASS (3 tests)

- [ ] **Step 5: Write `SKILL.md`**

```markdown
---
name: cross-check
description: Đối chiếu 2 nguồn (spec cũ/mới, code/spec, Excel/Excel). Phát hiện memory/ bị stale khi tài liệu nguồn update. Đối chiếu decisions-log.md với DD khi DD được update.
---

## 3 loại cặp nguồn (spec mục 6.2)

- **Spec cũ vs spec mới**: parse cả 2 thành `[{"key": "<field/trang>", "value": "<nội dung>"}]`,
  chạy `python3 scripts/diff-structured.py old.json new.json`.
- **Code vs spec**: lấy logic thực tế từ `code-to-business`, đối chiếu mô tả trong spec bằng
  cùng cơ chế trên.
- **Excel vs Excel**: dùng `../excel-analyze/scripts/extract-cells.py` trên cả 2 file, convert
  sang `{key, value}` theo cột khóa (key column) của bảng, rồi diff.

**Giới hạn thật**: chỉ so được phần đã convert được sang `{key, value}`. Văn xuôi tự do không
so structured được — hạ xuống so câu-với-câu, độ tin cậy thấp hơn, phải nói rõ trong output
đang dùng chế độ nào.

## Phát hiện `memory/` stale

Mỗi entry trong `memory/*.md` có nguồn + version/ngày (spec mục 3). Khi diff phát hiện 1 field
đã đổi giữa bản cũ/mới, tìm trong `memory/*.md` entry nào trích nguồn đúng field đó ở bản cũ →
gắn nhãn "cần re-verify" ngay trong response, không tự tin dùng tiếp giá trị cũ.

## Đối chiếu `decisions-log.md` với DD

Khi DD/spec được update: với mỗi entry trong `memory/decisions-log.md` có "Trạng thái trong
doc chính thức" khác "ĐÃ update đầy đủ", kiểm bản DD mới đã phản ánh quyết định đó chưa —
nếu có, hỏi user xác nhận đổi trạng thái entry; nếu chưa, tiếp tục flag.
```

- [ ] **Step 6: Commit**

```bash
git add brse-toolkit/skills/cross-check
git commit -m "feat: add cross-check skill with diff-structured.py"
```

---

### Task 7: `jp-vi-translate` skill — `check-glossary.py` + `check-consistency.py`

**Files:**
- Create: `brse-toolkit/skills/jp-vi-translate/SKILL.md`
- Create: `brse-toolkit/skills/jp-vi-translate/scripts/check-glossary.py`
- Create: `brse-toolkit/skills/jp-vi-translate/scripts/check-consistency.py`
- Test: `brse-toolkit/skills/jp-vi-translate/scripts/tests/test_check_glossary.py`
- Test: `brse-toolkit/skills/jp-vi-translate/scripts/tests/test_check_consistency.py`

**Interfaces:**
- `check-glossary.py <text_file> <glossary.md>` → JSON `{"matches": [{"term": str, "translation": str}]}` — parses `memory/glossary.md` entries of the shape `- <term> → "<translation>" — nguồn: ...` (schema fixed in Task 2's `init.md`), scans `text_file` for each term's presence.
- `check-consistency.py` reads JSON `[{"term": str, "translation_used": str}, ...]` from stdin → `{"conflicts": {term: [translations]}, "ok": bool}`, exit 1 if any term has 2+ distinct translations used.

- [ ] **Step 1: Write the failing tests**

```python
# brse-toolkit/skills/jp-vi-translate/scripts/tests/test_check_glossary.py
import json
import subprocess
import sys
import pathlib

SCRIPT = pathlib.Path(__file__).resolve().parents[1] / "check-glossary.py"

GLOSSARY = '''# Glossary JP-VI

- 登録 → "Lưu" — nguồn: spec.xlsx v2, P45, xác nhận 2026-07-20
- 必須項目 → "trường bắt buộc" — nguồn: spec.xlsx v1, P10, xác nhận 2026-07-01
'''


def run(text, glossary_text, tmp_path):
    text_file = tmp_path / "text.txt"
    glossary_file = tmp_path / "glossary.md"
    text_file.write_text(text, encoding="utf-8")
    glossary_file.write_text(glossary_text, encoding="utf-8")
    result = subprocess.run(
        [sys.executable, str(SCRIPT), str(text_file), str(glossary_file)],
        capture_output=True, text=True, encoding="utf-8",
    )
    return json.loads(result.stdout), result.returncode


def test_finds_known_term(tmp_path):
    out, code = run("ユーザーが登録ボタンを押下した場合", GLOSSARY, tmp_path)
    assert code == 0
    assert {"term": "登録", "translation": "Lưu"} in out["matches"]


def test_no_match_when_term_absent(tmp_path):
    out, _ = run("画面のレイアウトについて", GLOSSARY, tmp_path)
    assert out["matches"] == []


def test_finds_multiple_terms(tmp_path):
    out, _ = run("必須項目に登録ボタン", GLOSSARY, tmp_path)
    terms = {m["term"] for m in out["matches"]}
    assert terms == {"登録", "必須項目"}
```

```python
# brse-toolkit/skills/jp-vi-translate/scripts/tests/test_check_consistency.py
import json
import subprocess
import sys
import pathlib

SCRIPT = pathlib.Path(__file__).resolve().parents[1] / "check-consistency.py"


def run(entries):
    result = subprocess.run(
        [sys.executable, str(SCRIPT)],
        input=json.dumps(entries), capture_output=True, text=True, encoding="utf-8",
    )
    return json.loads(result.stdout), result.returncode


def test_no_conflict_when_consistent():
    entries = [
        {"term": "登録", "translation_used": "Lưu"},
        {"term": "登録", "translation_used": "Lưu"},
    ]
    out, code = run(entries)
    assert code == 0
    assert out["conflicts"] == {}


def test_detects_conflict():
    entries = [
        {"term": "登録", "translation_used": "Lưu"},
        {"term": "登録", "translation_used": "Đăng ký"},
    ]
    out, code = run(entries)
    assert code == 1
    assert out["conflicts"]["登録"] == ["Lưu", "Đăng ký"] or out["conflicts"]["登録"] == ["Đăng ký", "Lưu"]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest brse-toolkit/skills/jp-vi-translate/scripts/tests/ -v`
Expected: FAIL — scripts don't exist.

- [ ] **Step 3: Write the implementations**

```python
#!/usr/bin/env python3
# brse-toolkit/skills/jp-vi-translate/scripts/check-glossary.py
"""Scan a source text for terms already confirmed in memory/glossary.md.

Usage: check-glossary.py <text_file> <glossary_md>
Glossary entry format: - <term> → "<translation>" — nguồn: ...
"""
import json
import re
import sys

ENTRY_RE = re.compile(r'^- (?P<term>\S+) → "(?P<translation>[^"]+)"')


def parse_glossary(path: str) -> list[tuple[str, str]]:
    entries = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            m = ENTRY_RE.match(line.strip())
            if m:
                entries.append((m.group("term"), m.group("translation")))
    return entries


def check(text: str, glossary_path: str) -> list[dict]:
    entries = parse_glossary(glossary_path)
    return [{"term": term, "translation": translation} for term, translation in entries if term in text]


def main() -> None:
    if len(sys.argv) != 3:
        print("usage: check-glossary.py <text_file> <glossary_md>", file=sys.stderr)
        sys.exit(2)
    with open(sys.argv[1], encoding="utf-8") as f:
        text = f.read()
    print(json.dumps({"matches": check(text, sys.argv[2])}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
```

```python
#!/usr/bin/env python3
# brse-toolkit/skills/jp-vi-translate/scripts/check-consistency.py
"""Detect a glossary term translated inconsistently within one document.

Usage: cat entries.json | check-consistency.py
Input: JSON list of {"term": str, "translation_used": str}
"""
import json
import sys
from collections import defaultdict


def check(entries: list[dict]) -> dict:
    by_term = defaultdict(list)
    for e in entries:
        if e["translation_used"] not in by_term[e["term"]]:
            by_term[e["term"]].append(e["translation_used"])
    return {term: vals for term, vals in by_term.items() if len(vals) > 1}


def main() -> None:
    data = json.load(sys.stdin)
    conflicts = check(data)
    print(json.dumps({"conflicts": conflicts, "ok": len(conflicts) == 0}, ensure_ascii=False, indent=2))
    sys.exit(1 if conflicts else 0)


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest brse-toolkit/skills/jp-vi-translate/scripts/tests/ -v`
Expected: PASS (6 tests)

- [ ] **Step 5: Write `SKILL.md`**

```markdown
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
```

- [ ] **Step 6: Commit**

```bash
git add brse-toolkit/skills/jp-vi-translate
git commit -m "feat: add jp-vi-translate skill with check-glossary.py and check-consistency.py"
```

---

### Task 8: `code-to-business` skill — `extract-refs.py`

**Files:**
- Create: `brse-toolkit/skills/code-to-business/SKILL.md`
- Create: `brse-toolkit/skills/code-to-business/scripts/extract-refs.py`
- Test: `brse-toolkit/skills/code-to-business/scripts/tests/test_extract_refs.py`

**Interfaces:**
- Produces: `extract-refs.py <path> <keyword> [keyword2 ...]` → JSON `{"matches": [{"keyword": str, "file": str, "line": int, "content": str}, ...]}`. Requires the `rg` (ripgrep) binary on PATH.

- [ ] **Step 1: Write the failing test**

```python
# brse-toolkit/skills/code-to-business/scripts/tests/test_extract_refs.py
import json
import shutil
import subprocess
import sys
import pathlib

import pytest

SCRIPT = pathlib.Path(__file__).resolve().parents[1] / "extract-refs.py"

pytestmark = pytest.mark.skipif(shutil.which("rg") is None, reason="ripgrep (rg) not installed")


def run(path, *keywords):
    result = subprocess.run(
        [sys.executable, str(SCRIPT), str(path), *keywords],
        capture_output=True, text=True, encoding="utf-8",
    )
    return json.loads(result.stdout), result.returncode


def test_finds_keyword_with_file_and_line(tmp_path):
    src = tmp_path / "order.py"
    src.write_text("def get_inventory():\n    return call_order_api()\n", encoding="utf-8")
    out, code = run(tmp_path, "call_order_api")
    assert code == 0
    assert len(out["matches"]) == 1
    match = out["matches"][0]
    assert match["file"].endswith("order.py")
    assert match["line"] == 2
    assert "call_order_api" in match["content"]


def test_multiple_keywords_searched_independently(tmp_path):
    src = tmp_path / "order.py"
    src.write_text("def get_inventory():\n    pass\n\ndef get_revenue():\n    pass\n", encoding="utf-8")
    out, _ = run(tmp_path, "get_inventory", "get_revenue")
    keywords_found = {m["keyword"] for m in out["matches"]}
    assert keywords_found == {"get_inventory", "get_revenue"}


def test_no_match_returns_empty_list(tmp_path):
    src = tmp_path / "order.py"
    src.write_text("def unrelated():\n    pass\n", encoding="utf-8")
    out, _ = run(tmp_path, "nonexistent_symbol")
    assert out["matches"] == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest brse-toolkit/skills/code-to-business/scripts/tests/test_extract_refs.py -v`
Expected: FAIL — script does not exist. (Tests skip automatically if `rg` isn't installed — install ripgrep first: `sudo apt install ripgrep` / `brew install ripgrep`.)

- [ ] **Step 3: Write the implementation**

```python
#!/usr/bin/env python3
# brse-toolkit/skills/code-to-business/scripts/extract-refs.py
"""Grep a codebase for business-domain keywords, returning exact file:line matches.

Usage: extract-refs.py <path> <keyword> [keyword2 ...]
Requires `rg` (ripgrep) on PATH.
"""
import json
import subprocess
import sys


def search(path: str, keywords: list[str]) -> list[dict]:
    results = []
    for kw in keywords:
        proc = subprocess.run(
            ["rg", "--line-number", "--no-heading", "--fixed-strings", kw, path],
            capture_output=True, text=True,
        )
        for line in proc.stdout.splitlines():
            parts = line.split(":", 2)
            if len(parts) == 3:
                results.append({
                    "keyword": kw,
                    "file": parts[0],
                    "line": int(parts[1]),
                    "content": parts[2].strip(),
                })
    return results


def main() -> None:
    if len(sys.argv) < 3:
        print("usage: extract-refs.py <path> <keyword> [keyword2 ...]", file=sys.stderr)
        sys.exit(2)
    path, keywords = sys.argv[1], sys.argv[2:]
    print(json.dumps({"matches": search(path, keywords)}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest brse-toolkit/skills/code-to-business/scripts/tests/test_extract_refs.py -v`
Expected: PASS (3 tests, or SKIPPED if `rg` not installed — install it before continuing)

- [ ] **Step 5: Write `SKILL.md`**

```markdown
---
name: code-to-business
description: Trích nghiệp vụ từ source code không có tài liệu, mỗi câu mô tả trỏ về file:line chính xác qua extract-refs.py.
---

## Trigger

Cần hiểu nghiệp vụ từ source code, không đọc "toàn bộ codebase" — bắt buộc có phạm vi cụ thể
(1 tính năng/luồng nghiệp vụ, vd "luồng đơn hàng tồn kho"). Chưa rõ phạm vi → hỏi lại, không
tự chọn đại.

## Chiến lược đọc codebase lớn (spec mục 6.10)

1. `python3 scripts/extract-refs.py <path> <keyword1> <keyword2> ...` với keyword nghiệp vụ
   trong phạm vi đã xác định → danh sách file:line, không đổ nguyên file vào context.
2. Từ danh sách match, chỉ đọc (Read tool, đúng đoạn dòng liên quan) file/hàm thực sự nằm
   trong luồng — không đọc hết mọi file có match.
3. Phạm vi rải >~10 file → xử lý từng file/module một, ghi phát hiện vào bản nháp trung gian,
   tổng hợp ở bước cuối. Có thể dispatch song song theo module (spec mục 11) — mỗi subagent
   đọc `memory/glossary.md` trước khi phân tích, KHÔNG tự ghi `memory/`.
4. Match tìm được nhưng không chắc liên quan → liệt kê riêng "tìm thấy nhưng chưa chắc liên
   quan, cần xác nhận" — không tự loại, không tự gộp vào kết luận chính.

## Output

Tài liệu nghiệp vụ (điều kiện, luồng xử lý, validation), mỗi câu mô tả kèm `(nguồn:
file:dòng)` — theo `verify-output`.

## Trước khi tin nội dung DD/spec hiện có

Check `memory/decisions-log.md` trước — DD có thể chưa phản ánh quyết định QA gần nhất
(spec mục 3).
```

- [ ] **Step 6: Commit**

```bash
git add brse-toolkit/skills/code-to-business
git commit -m "feat: add code-to-business skill with extract-refs.py"
```

---

### Task 9: `excel-analyze` skill — `extract-images.py` + shape fallback + `SKILL.md`

**Files:**
- Create: `brse-toolkit/skills/excel-analyze/SKILL.md`
- Create: `brse-toolkit/skills/excel-analyze/scripts/extract-images.py`
- Create: `brse-toolkit/skills/excel-analyze/scripts/render-sheet.py`
- Test: `brse-toolkit/skills/excel-analyze/scripts/tests/test_extract_images.py`
- Test: `brse-toolkit/skills/excel-analyze/scripts/tests/test_render_sheet.py`

**Interfaces:**
- `extract-images.py <xlsx_path> <out_dir>` → JSON `{"images": [{"sheet": str, "file": str, "anchor_from": str, "anchor_to": str}]}`.
- `render-sheet.py <xlsx_path> <out_dir>` → prints the path to a rendered PDF (fallback for shapes/annotations `openpyxl` can't read structurally). Requires `libreoffice` on PATH.
- Consumes: `extract-cells.py` (Task 4, already built).

- [ ] **Step 1: Write the failing tests**

```python
# brse-toolkit/skills/excel-analyze/scripts/tests/test_extract_images.py
import json
import subprocess
import sys
import pathlib

import openpyxl
from openpyxl.drawing.image import Image as XLImage
from PIL import Image as PILImage

SCRIPT = pathlib.Path(__file__).resolve().parents[1] / "extract-images.py"


def make_fixture(xlsx_path, png_path):
    PILImage.new("RGB", (10, 10), color="red").save(png_path)
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "ScreenA"
    img = XLImage(str(png_path))
    ws.add_image(img, "B10")
    wb.save(xlsx_path)


def run(xlsx_path, out_dir):
    result = subprocess.run(
        [sys.executable, str(SCRIPT), str(xlsx_path), str(out_dir)],
        capture_output=True, text=True, encoding="utf-8",
    )
    return json.loads(result.stdout), result.returncode


def test_extracts_embedded_image_with_anchor(tmp_path):
    xlsx = tmp_path / "fixture.xlsx"
    png = tmp_path / "src.png"
    out_dir = tmp_path / "out"
    make_fixture(xlsx, png)
    out, code = run(xlsx, out_dir)
    assert code == 0
    assert len(out["images"]) == 1
    entry = out["images"][0]
    assert entry["sheet"] == "ScreenA"
    assert pathlib.Path(entry["file"]).exists()


def test_no_images_returns_empty_list(tmp_path):
    xlsx = tmp_path / "empty.xlsx"
    wb = openpyxl.Workbook()
    wb.save(xlsx)
    out_dir = tmp_path / "out"
    out, code = run(xlsx, out_dir)
    assert out["images"] == []
```

```python
# brse-toolkit/skills/excel-analyze/scripts/tests/test_render_sheet.py
import shutil
import subprocess
import sys
import pathlib

import openpyxl
import pytest

SCRIPT = pathlib.Path(__file__).resolve().parents[1] / "render-sheet.py"

pytestmark = pytest.mark.skipif(shutil.which("libreoffice") is None, reason="libreoffice not installed")


def test_render_produces_output_file(tmp_path):
    xlsx = tmp_path / "fixture.xlsx"
    wb = openpyxl.Workbook()
    wb.active["A1"] = "shape/annotation placeholder"
    wb.save(xlsx)
    out_dir = tmp_path / "out"
    result = subprocess.run(
        [sys.executable, str(SCRIPT), str(xlsx), str(out_dir)],
        capture_output=True, text=True, encoding="utf-8",
    )
    assert result.returncode == 0
    produced = result.stdout.strip()
    assert pathlib.Path(produced).exists()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest brse-toolkit/skills/excel-analyze/scripts/tests/test_extract_images.py brse-toolkit/skills/excel-analyze/scripts/tests/test_render_sheet.py -v`
Expected: FAIL — scripts don't exist. (`test_render_sheet` will SKIP instead if `libreoffice` isn't installed — install it before continuing: `sudo apt install libreoffice`.)

- [ ] **Step 3: Write the implementations**

```python
#!/usr/bin/env python3
# brse-toolkit/skills/excel-analyze/scripts/extract-images.py
"""Extract embedded pictures from an xlsx file, with their anchor cell range.

Usage: extract-images.py <xlsx_path> <out_dir>
Note: anchor is a CELL RANGE (images float over cells), not a single exact cell —
report this limitation when citing an image as a source.
"""
import json
import os
import sys

import openpyxl


def extract(path: str, out_dir: str) -> list[dict]:
    wb = openpyxl.load_workbook(path)
    os.makedirs(out_dir, exist_ok=True)
    results = []
    for ws in wb.worksheets:
        for i, img in enumerate(getattr(ws, "_images", [])):
            anchor = img.anchor
            from_marker = getattr(anchor, "_from", None)
            to_marker = getattr(anchor, "to", None)
            from_cell = f"col{from_marker.col},row{from_marker.row}" if from_marker else "unknown"
            to_cell = f"col{to_marker.col},row{to_marker.row}" if to_marker else "unknown"
            filename = f"{ws.title}_{i}.png"
            out_path = os.path.join(out_dir, filename)
            with open(out_path, "wb") as f:
                f.write(img._data())
            results.append({
                "sheet": ws.title,
                "file": out_path,
                "anchor_from": from_cell,
                "anchor_to": to_cell,
            })
    return results


def main() -> None:
    if len(sys.argv) != 3:
        print("usage: extract-images.py <xlsx_path> <out_dir>", file=sys.stderr)
        sys.exit(2)
    print(json.dumps({"images": extract(sys.argv[1], sys.argv[2])}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
```

```python
#!/usr/bin/env python3
# brse-toolkit/skills/excel-analyze/scripts/render-sheet.py
"""Fallback for shapes/textboxes/arrows openpyxl can't read structurally: render
the workbook to PDF via headless LibreOffice, then hand it to image-analyze.

Usage: render-sheet.py <xlsx_path> <out_dir>
Prints the path to the rendered PDF.
Requires `libreoffice` on PATH. MVP renders the whole workbook (LibreOffice's
default active-sheet export) — per-sheet PNG splitting is a possible refinement,
not needed for the fallback's current scope (spec mục 6.3).
"""
import subprocess
import sys
import os


def render(xlsx_path: str, out_dir: str) -> str:
    os.makedirs(out_dir, exist_ok=True)
    subprocess.run(
        ["libreoffice", "--headless", "--convert-to", "pdf", "--outdir", out_dir, xlsx_path],
        check=True, capture_output=True,
    )
    base = os.path.splitext(os.path.basename(xlsx_path))[0]
    return os.path.join(out_dir, f"{base}.pdf")


def main() -> None:
    if len(sys.argv) != 3:
        print("usage: render-sheet.py <xlsx_path> <out_dir>", file=sys.stderr)
        sys.exit(2)
    print(render(sys.argv[1], sys.argv[2]))


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest brse-toolkit/skills/excel-analyze/scripts/tests/ -v`
Expected: PASS (all — `test_render_sheet` PASS or SKIPPED depending on `libreoffice` availability)

- [ ] **Step 5: Write `SKILL.md`**

```markdown
---
name: excel-analyze
description: Đọc/đối chiếu Excel — cell value+format qua extract-cells.py, ảnh embedded qua extract-images.py, shape/annotation fallback render qua render-sheet.py + image-analyze.
---

## Cơ chế (spec mục 6.3)

1. `python3 scripts/extract-cells.py <file.xlsx>` — value + font_color + strike + fill_color +
   comment, đọc chính xác từ XML, KHÔNG phải vision.
2. Ý nghĩa định dạng (đỏ = gì, gạch ngang = gì) — KHÔNG đoán. Lần đầu quan sát pattern → hỏi
   xác nhận → ghi vào `memory/conventions.md`. Lần sau áp dụng luôn, không hỏi lại. Ô có định
   dạng lạ chưa từng xác nhận → flag riêng, không áp quy ước cũ lên nó.
3. `python3 scripts/extract-images.py <file.xlsx> <out_dir>` — ảnh dán trong sheet, bytes +
   vùng ô neo (KHÔNG phải 1 ô chính xác — nói rõ giới hạn này khi trích dẫn).
4. Shape/textbox/mũi tên annotation `extract-images.py` không đọc được → `python3
   scripts/render-sheet.py <file.xlsx> <out_dir>`, chain kết quả (PDF/ảnh) sang skill
   `image-analyze`.
5. Report cuối gộp 2 loại nguồn, KHÔNG trình bày ngang hàng: phần cell-text (chính xác tuyệt
   đối) và phần ảnh/shape (qua vision, gắn nhãn "đọc bằng ảnh, chưa chắc 100%").

## Dùng chung với `qa-tone-brse`

`extract-cells.py` cũng là script `qa-tone-brse` dùng để đọc lại Q&A list Excel — không có
bản sao thứ 2 của script này ở đâu khác.
```

- [ ] **Step 6: Commit**

```bash
git add brse-toolkit/skills/excel-analyze
git commit -m "feat: add excel-analyze skill with extract-images.py and render-sheet.py"
```

---

### Task 10: `image-analyze` skill — `ocr-pass.py`

**Files:**
- Create: `brse-toolkit/skills/image-analyze/SKILL.md`
- Create: `brse-toolkit/skills/image-analyze/scripts/ocr-pass.py`
- Test: `brse-toolkit/skills/image-analyze/scripts/tests/test_ocr_pass.py`

**Interfaces:**
- Produces: `ocr-pass.py <image_path> [lang]` → JSON `{"words": [{"text": str, "confidence": int, "left": int, "top": int}]}`. Default `lang=jpn`; requires `tesseract` + the relevant traineddata on PATH.

- [ ] **Step 1: Write the failing test**

```python
# brse-toolkit/skills/image-analyze/scripts/tests/test_ocr_pass.py
import json
import shutil
import subprocess
import sys
import pathlib

import pytest
from PIL import Image, ImageDraw

SCRIPT = pathlib.Path(__file__).resolve().parents[1] / "ocr-pass.py"


def _tesseract_has_lang(lang: str) -> bool:
    if shutil.which("tesseract") is None:
        return False
    result = subprocess.run(["tesseract", "--list-langs"], capture_output=True, text=True)
    return lang in result.stdout


pytestmark = pytest.mark.skipif(not _tesseract_has_lang("eng"), reason="tesseract with eng traineddata not installed")


def make_fixture(path):
    img = Image.new("RGB", (200, 60), color="white")
    draw = ImageDraw.Draw(img)
    draw.text((10, 15), "HELLO", fill="black")
    img.save(path)


def run(image_path, lang="eng"):
    result = subprocess.run(
        [sys.executable, str(SCRIPT), str(image_path), lang],
        capture_output=True, text=True, encoding="utf-8",
    )
    return json.loads(result.stdout), result.returncode


def test_ocr_extracts_text_with_position(tmp_path):
    img_path = tmp_path / "fixture.png"
    make_fixture(img_path)
    out, code = run(img_path)
    assert code == 0
    texts = [w["text"] for w in out["words"]]
    assert any("HELLO" in t.upper() for t in texts)
    assert all("left" in w and "top" in w and "confidence" in w for w in out["words"])
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest brse-toolkit/skills/image-analyze/scripts/tests/test_ocr_pass.py -v`
Expected: FAIL — script does not exist. (SKIPPED if `tesseract`/`eng` traineddata missing — install first: `sudo apt install tesseract-ocr tesseract-ocr-jpn`.)

- [ ] **Step 3: Write the implementation**

```python
#!/usr/bin/env python3
# brse-toolkit/skills/image-analyze/scripts/ocr-pass.py
"""OCR pass for printed/typed text in an image — more reliable than vision transcription
for text tesseract can read; vision still handles layout/arrows/handwriting.

Usage: ocr-pass.py <image_path> [lang]   (default lang: jpn)
"""
import json
import sys

import pytesseract
from PIL import Image


def ocr(path: str, lang: str = "jpn") -> list[dict]:
    img = Image.open(path)
    data = pytesseract.image_to_data(img, lang=lang, output_type=pytesseract.Output.DICT)
    words = []
    for i, text in enumerate(data["text"]):
        if text.strip():
            words.append({
                "text": text,
                "confidence": int(data["conf"][i]),
                "left": int(data["left"][i]),
                "top": int(data["top"][i]),
            })
    return words


def main() -> None:
    if len(sys.argv) not in (2, 3):
        print("usage: ocr-pass.py <image_path> [lang]", file=sys.stderr)
        sys.exit(2)
    lang = sys.argv[2] if len(sys.argv) == 3 else "jpn"
    print(json.dumps({"words": ocr(sys.argv[1], lang)}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest brse-toolkit/skills/image-analyze/scripts/tests/test_ocr_pass.py -v`
Expected: PASS (1 test), or SKIPPED if tesseract unavailable.

- [ ] **Step 5: Write `SKILL.md`**

```markdown
---
name: image-analyze
description: Đọc screenshot/sơ đồ tay/ảnh lỗi — OCR trước cho chữ in/UI text, vision chỉ lo bố cục/mũi tên/chữ viết tay.
---

## Cơ chế (spec mục 6.4)

1. `python3 scripts/ocr-pass.py <image> jpn` — chữ in/UI text, đáng tin hơn để vision tự đọc.
   Nếu ảnh có chữ tiếng Anh/Việt, gọi lại với `lang=eng`/`vie`.
2. Vision chỉ đảm nhiệm phần OCR không làm được: bố cục, hướng mũi tên, chữ viết tay.
3. Luôn gắn confidence rõ ràng (dùng field `confidence` từ OCR khi có), KHÔNG trình bày ngang
   hàng với structured data từ script khác (vd `extract-cells.py`).

## Output

Mô tả structured (thành phần UI, luồng mũi tên, text trong ảnh) để đối chiếu với spec bằng
chữ — điểm nghi vấn nếu ảnh không khớp spec, theo `verify-output`.
```

- [ ] **Step 6: Commit**

```bash
git add brse-toolkit/skills/image-analyze
git commit -m "feat: add image-analyze skill with ocr-pass.py"
```

---

### Task 11: `report-gen` skill

**Files:**
- Create: `brse-toolkit/skills/report-gen/SKILL.md`

**Interfaces:**
- No script per spec mục 5 (uses `openpyxl`/`python-pptx`/`python-docx` directly, invoked inline by the agent — not wrapped in a dedicated CLI since the shape of "content → filled template" varies per call and isn't a fixed pure function worth freezing into a script yet, consistent with spec mục 10's honesty about what's untested).

- [ ] **Step 1: Write `SKILL.md`**

```markdown
---
name: report-gen
description: Xuất Excel/Slide/Word đúng template khách. Ví dụ luồng cụ thể cho slide ở dưới.
---

## Nguồn template

Check `templates/` (thư mục dự án, KHÔNG phải template mặc định đóng gói trong
`skills/detail-design-jp/templates/` — 2 khái niệm khác chỗ, xem spec mục 7) — có mẫu riêng
của khách thì dùng `python-pptx`/`python-docx`/`openpyxl` mở template đó và điền nội dung,
giữ nguyên design. Chưa có → dùng mẫu mặc định đơn giản, nói rõ trong response: "chưa có
template khách, dùng mẫu mặc định — xác nhận format sau."

## Luồng cụ thể — tạo slide (spec mục 6.9)

1. **Nội dung lấy từ đâu** — không tự bịa. Status report → `memory/decisions-log.md` +
   `cross-check`/`code-to-business` nếu có. Đề xuất giải pháp → chain qua `proposal-gen`
   trước. User cung cấp trực tiếp → dùng nội dung đó.
2. **Xác định template** — như trên.
3. **Xác định người đọc** — áp mô hình relay (spec mục 2): slide khách Nhật khác slide nội bộ
   PM/dev. Chưa rõ → hỏi trước khi soạn.
4. **Áp `verify-output` cho từng bullet** — claim/số liệu không gắn được nguồn → để trong
   speaker notes "cần xác nhận thêm", KHÔNG đưa thẳng lên slide như fact đã chốt.
5. Tạo file thật bằng `python-pptx` (hoặc `openpyxl`/`python-docx` cho Excel/Word).
6. **Output**: file + danh sách ngắn "giả định/điểm chưa xác nhận" TÁCH RIÊNG để user duyệt
   trước khi gửi — không lẫn vào trong file.
```

- [ ] **Step 2: Commit**

```bash
git add brse-toolkit/skills/report-gen
git commit -m "feat: add report-gen skill"
```

---

### Task 12: `brainstorm-brse` skill

**Files:**
- Create: `brse-toolkit/skills/brainstorm-brse/SKILL.md`

- [ ] **Step 1: Write `SKILL.md`**

```markdown
---
name: brainstorm-brse
description: Đề xuất giải pháp/nghiệp vụ cho 1 vấn đề cụ thể — không phải brainstorm code, có khung, không lan man.
---

## Trigger

Cần đề xuất giải pháp cho 1 vấn đề nghiệp vụ/quy trình cụ thể.

## Cơ chế

Đưa 2-3 phương án, mỗi phương án:
- Mô tả ngắn gọn.
- Trade-off rõ ràng (được gì, mất gì).
- Rủi ro/ảnh hưởng tới phía khách Nhật nếu có (do đặc thù BrSE — quyết định kỹ thuật ở đây
  thường phải giải trình được với khách).
- Khuyến nghị 1 phương án, nói rõ vì sao.

Không đưa quá 3 phương án — quá nhiều lựa chọn không giúp quyết định nhanh hơn.

## Output

Danh sách phương án + khuyến nghị. Nếu phương án nào cần thêm research trước khi chốt được
→ chain sang `research-jp-tech`.
```

- [ ] **Step 2: Commit**

```bash
git add brse-toolkit/skills/brainstorm-brse
git commit -m "feat: add brainstorm-brse skill"
```

---

### Task 13: `research-jp-tech` skill

**Files:**
- Create: `brse-toolkit/skills/research-jp-tech/SKILL.md`

- [ ] **Step 1: Write `SKILL.md`**

```markdown
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
```

- [ ] **Step 2: Commit**

```bash
git add brse-toolkit/skills/research-jp-tech
git commit -m "feat: add research-jp-tech skill"
```

---

### Task 14: `proposal-gen` skill

**Files:**
- Create: `brse-toolkit/skills/proposal-gen/SKILL.md`

- [ ] **Step 1: Write `SKILL.md`**

```markdown
---
name: proposal-gen
description: Requirements → proposal. Bản nội bộ kỹ thuật và bản khách là 2 lần soạn nội dung khác nhau, không phải 1 bản rồi rút gọn cơ học.
---

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
```

- [ ] **Step 2: Commit**

```bash
git add brse-toolkit/skills/proposal-gen
git commit -m "feat: add proposal-gen skill"
```

---

### Task 15: `detail-design-jp` skill

**Files:**
- Create: `brse-toolkit/skills/detail-design-jp/SKILL.md`
- Create: `brse-toolkit/skills/detail-design-jp/templates/detail-design-jp-template.md`

**Interfaces:**
- `templates/detail-design-jp-template.md` here is the plugin's packaged DEFAULT template (generic, public-safe) — distinct from the per-project `templates/` folder a client's own DD format would live in (spec mục 7's disambiguation note).

- [ ] **Step 1: Write the default template**

```markdown
# 詳細設計書 — <画面/機能名>

## 改訂履歴

| 版数 | 日付 | 変更内容 | 担当 |
|---|---|---|---|
| 1.0 | | 新規作成 | |

## 概要 / 目的

<この機能が何のために存在するか>

## 処理概要

<処理の流れをステップで記述>

### フロー

```
<ステップ1> → <ステップ2> → <ステップ3>
```

## 画面レイアウト

<レイアウト図または説明>

### 項目定義

| 項目名 | 型 | 必須 | 説明 |
|---|---|---|---|

## 入力チェック

| 項目 | チェック内容 | エラーメッセージ |
|---|---|---|

## テーブル定義

| テーブル名 | カラム | 型 | 説明 |
|---|---|---|---|

## エラー処理

| ケース | 処理内容 |
|---|---|
```

- [ ] **Step 2: Write `SKILL.md`**

```markdown
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
```

- [ ] **Step 3: Commit**

```bash
git add brse-toolkit/skills/detail-design-jp
git commit -m "feat: add detail-design-jp skill with default SI-style template"
```

---

## After all 15 tasks

Run the full test suite once to confirm nothing regressed between tasks:

```bash
pip install -r brse-toolkit/requirements.txt
pytest brse-toolkit -v
```

Then follow spec mục 10's remaining real-world checklist (a live project directory to run
`/brse-toolkit:init` in, a real client template, a real codebase) — those need the plugin
owner's actual data, not more code.
