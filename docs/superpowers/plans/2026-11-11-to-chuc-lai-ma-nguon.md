# Tổ chức lại mã nguồn brse-toolkit — kế hoạch thực hiện

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Mục tiêu:** chuyển 32 tập lệnh rời thành một gói Python `brse` có ranh giới rõ, gọi qua một lối vào duy nhất `scripts/brse.py <lệnh>`, mà không đổi kết quả của bất kỳ lệnh nào.

**Kiến trúc:** gói `brse/` ở gốc plugin, chia theo trách nhiệm (cấu hình, tệp văn phòng, kho tài liệu, dịch, rà soát, bộ nhớ dự án, sơ đồ, công cụ mã). `scripts/brse.py` thêm gốc plugin vào `sys.path` rồi gọi `brse.cli.main`. Mỗi lệnh là một hàm trả về `(dữ liệu JSON, mã thoát)`; chỉ `cli.py` in kết quả và tách tham số. Trong lúc chuyển, tập lệnh cũ còn lại làm lớp vỏ ba dòng để văn bản kỹ năng vẫn chạy; nhiệm vụ cuối đổi văn bản sang lối vào mới và xóa lớp vỏ.

**Công nghệ:** Python (CI hiện chạy 3.12 trên ubuntu, macos, windows), thư viện chuẩn, các gói trong `requirements.txt`, pytest.

**Căn cứ:** phần "Tổ chức code" trong cuộc trao đổi ngày 2026-11-11 (đã kiểm bằng lệnh):
- chỉ `scripts/brse_common.py` nạp được bình thường; 17 tệp `import brse_common`;
- 8 tệp nạp lẫn nhau bằng `importlib.spec_from_file_location` vì tên có dấu gạch ngang;
- mỗi tập lệnh tự tách tham số; chỉ `register.py`, `doc2md.py` dùng `argparse`;
- 10 tập lệnh trong `skills/*/scripts/` không đọc cấu hình dự án;
- ba nơi đọc Excel (`extract-cells.py`, `kb-ingest.py`, `office-text.py`), hai nơi chụp trang (`render-sheet.py`, `office.py render`);
- dòng lệnh hook trong `hooks/hooks.json` làm `guard-secrets.py` mất tác dụng (`python3 … || python …` chạy lại lần hai với đầu vào rỗng, thoát 0).

## Đã làm (2026-11-11) — khác kế hoạch ở ba chỗ

- Mỗi lệnh dùng lại hàm `main()` của tập lệnh cũ (đọc `sys.argv`), `cli.py` đặt `sys.argv` rồi gọi — giữ nguyên cách tách tham số cũ, không viết lại bằng `argparse`.
- `docx`/`pptx` vẫn nằm trong `brse/office/text.py`; `drawio-tool` chuyển nguyên khối thành `brse/diagram/drawio.py`, chưa tách.
- Kiểm thử dời vào `tests/` và gọi qua `run_script` (tên tệp cũ → lệnh mới) để các khẳng định giữ nguyên.

## Ràng buộc chung

- Không thêm gói bên thứ ba nào. `markitdown` vẫn là tùy chọn như hiện nay trong `doc2md`.
- Mọi lệnh giữ nguyên khóa JSON đầu ra và mã thoát hiện tại. Các khẳng định (`assert`) trong 171 kiểm thử hiện có là hợp đồng: khi chuyển kiểm thử chỉ được đổi cách gọi, không đổi khẳng định — trừ chỗ kế hoạch ghi rõ.
- Tên lệnh con = tên tệp cũ bỏ `.py` (`kb-ingest.py` → `brse.py kb-ingest`), trừ: `brse-config.py` → `config`; `render-sheet.py` → bỏ, dùng `office render`; `memory-inject.py`, `memory-log.py`, `guard-secrets.py` → chỉ còn `hook session-start`, `hook stop`, `hook guard` (ba tệp này chỉ được hook gọi).
- Plugin không được cài bằng pip: `scripts/brse.py` phải tự thêm gốc plugin vào `sys.path` và đặt `sys.dont_write_bytecode = True` trước mọi import khác.
- Gói thư viện bên thứ ba (`openpyxl`, `docx`, `pptx`, `PIL`, `pytesseract`, `lxml`) chỉ được import bên trong hàm dùng nó, để `brse.py doctor` và `brse.py config` chạy được trên máy chưa cài gói nào.
- Hook không bao giờ làm hỏng phiên: mọi lỗi trong hook `session-start` / `stop` bị nuốt, thoát 0. Riêng `guard` thoát 2 khi chặn.

## Điểm cần soi khi rà

1. Lệnh chạy từ một thư mục con của dự án (không phải gốc) vẫn tìm đúng `.brse/config.json` — kiểm thử ở Nhiệm vụ 1.
2. Máy chưa cài `openpyxl`: `config` (Nhiệm vụ 1) và `doctor` (Nhiệm vụ 6) vẫn chạy và báo thiếu gói.
3. Dòng lệnh hook thật trong `hooks.json` (chạy qua `bash -c`, đầu vào qua stdin) chặn được tệp khóa và thoát 2 — kiểm thử ở Nhiệm vụ 6.
4. Văn bản kỹ năng, lệnh, `init.md` (khối `CLAUDE.md` sinh ra) không còn nhắc tên tập lệnh cũ nào, kể cả tên trần như `office-diff.py` — kiểm thử ở Nhiệm vụ 9.
5. Tệp Excel có hình đọc qua bộ đọc chung vẫn được `kb-ingest` báo `partial`, và `office-text extract` cho cùng tập ô chữ như `extract-cells` — kiểm thử ở Nhiệm vụ 3.
6. Máy có LibreOffice nhưng không có `pdftoppm`: `office render` cho .xlsx vẫn ra ảnh như `render-sheet.py` cũ (cũ dùng `--convert-to png`) — kiểm thử ở Nhiệm vụ 2.

---

## Cấu trúc tệp đích

```
scripts/brse.py                 lối vào duy nhất
brse/
  __init__.py
  cli.py                        tách tham số, bảng lệnh, in JSON, mã thoát
  config.py                     gộp brse-config.py + brse_common.py
  hooks.py                      session-start, stop, guard
  office/
    tools.py                    tìm công cụ văn phòng dòng lệnh, chạy tiến trình (từ office.py)
    xlsx.py                     MỌI chỗ dùng openpyxl để đọc
    docx.py, pptx.py            đọc đoạn văn / khung chữ (từ office-text.py, kb-ingest.py)
    text.py                     extract / apply đơn vị dịch (từ office-text.py)
    diff.py                     (từ office-diff.py)
    render.py                   info / render / check (từ office.py; thay render-sheet.py)
  knowledge/ingest.py, search.py, doc2md.py
  translate/mt.py, glossary.py, consistency.py, lint.py
  review/agents.py, judge.py, wording.py, claims.py, hedge.py
  project/register.py, memory.py, feedback.py, library.py, keys.py, doctor.py
  diagram/templates.py, model.py, checks.py, export.py
  code/refs.py, structured_diff.py, ocr.py
tests/                          toàn bộ kiểm thử, chuyển từ scripts/tests và skills/*/scripts/tests
```

---

### Nhiệm vụ 1: Bộ khung gói, cấu hình, lối vào

**Tệp:**
- Tạo: `scripts/brse.py`, `brse/__init__.py`, `brse/cli.py`, `brse/config.py`, `tests/conftest.py`, `tests/test_cli.py`
- Chuyển: `scripts/tests/test_brse_config.py` → `tests/test_config.py`
- Sửa: `scripts/brse_common.py` (chỉ còn `from brse.config import *` sau khi thêm gốc plugin vào `sys.path`), `scripts/brse-config.py` (lớp vỏ), `pytest.ini` (`testpaths = tests scripts/tests skills`)

**Giao diện:**
- Tạo ra:
  - `brse.config`: `PLUGIN_ROOT: Path`, `LAYOUT_VERSION = 2`, `class ConfigError(ValueError)`, `resolve(start: Path) -> dict` (khóa `config`, `loaded`, `workspace_root`, `warnings` như hiện nay), `workspace(start) -> tuple[Path | None, dict]`, `masked(out: dict) -> dict`, `secret(env_name: str) -> str | None`, `secrets_file() -> Path`, `data_dir() -> Path`, `plugin_version() -> str`, `read_hook_input() -> dict`.
  - `brse.cli`: `class Fail(Exception)` (thông điệp → `{"error": …}`, mã thoát 2); `Command = Callable[[argparse.Namespace], tuple[dict, int]]`; `register(name: str, build: Callable[[argparse.ArgumentParser], None], run: Command) -> None`; `main(argv: list[str] | None = None) -> int`. Mỗi gói con đăng ký lệnh của mình trong một hàm `commands(register)`; `cli.py` gọi lần lượt danh sách module cố định (không quét thư mục).
  - Lớp vỏ chuẩn cho tệp cũ (dùng lại ở mọi nhiệm vụ sau; `N = 1` cho `scripts/*.py`, `N = 3` cho `skills/*/scripts/*.py`):
    ```python
    import sys, pathlib; sys.dont_write_bytecode = True
    sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[N]))
    from brse.cli import main; sys.exit(main(["<lệnh>", *sys.argv[1:]]))
    ```
  - `tests/conftest.py`: giữ fixture `ws`; `run_cli(*args, stdin=None, env=None, tmp=None, cwd=None) -> CompletedProcess` chạy `[sys.executable, ROOT/"scripts/brse.py", *args]` với cùng biến môi trường như `run_script` cũ; thêm `ROOT` vào `sys.path` để kiểm thử import gói trực tiếp.

- [ ] **Bước 1: Viết kiểm thử thất bại** trong `tests/test_cli.py`:
  - `test_unknown_command_exits_2`: `run_cli("khong-co")` → mã 2, stdout JSON có `error`.
  - `test_config_from_subfolder`: trong `ws`, tạo `ws/a/b`, `run_cli("config", cwd=ws/"a"/"b")` → `workspace_root == str(ws)`.
  - `test_config_runs_without_third_party_packages`: chạy `python -I -c` với mã: thêm gốc plugin vào `sys.path`, đặt `sys.modules[m] = None` cho `openpyxl`, `docx`, `pptx`, `PIL`, `pytesseract`, `lxml`, rồi `from brse.cli import main; sys.exit(main(["config"]))` → mã 0. Kiểm thử này chứng minh `cli.py` không kéo theo gói bên thứ ba khi nạp danh sách lệnh.
- [ ] **Bước 2:** `python -m pytest tests/test_cli.py -q` → thất bại vì chưa có `scripts/brse.py`.
- [ ] **Bước 3:** viết `brse/config.py` (dời nguyên logic từ `brse-config.py` và `brse_common.py`, thông điệp lỗi giữ nguyên chữ), `brse/cli.py`, `scripts/brse.py`, lệnh `config`.
- [ ] **Bước 4:** chuyển `test_brse_config.py` sang `tests/test_config.py`, đổi `run_script("brse-config.py", …)` → `run_cli("config", …)`; `python -m pytest -q` → toàn bộ qua.
- [ ] **Bước 5: Commit** `refactor: add brse package, single entry point, config module`

### Nhiệm vụ 2: Tệp văn phòng — một bộ đọc chung

**Tệp:**
- Tạo: `brse/office/{__init__,tools,xlsx,docx,pptx,text,diff,render}.py`
- Sửa thành lớp vỏ: `scripts/office.py`, `scripts/office-text.py`, `scripts/office-diff.py`, `skills/excel-analyze/scripts/extract-cells.py`, `skills/excel-analyze/scripts/extract-images.py`
- Xóa: `skills/excel-analyze/scripts/render-sheet.py` và `test_render_sheet.py` (thay bằng `test_office_render_xlsx_without_pdftoppm`: giả lập không có `pdftoppm` trên `PATH`, `office render` một .xlsx → có ít nhất một ảnh .png; bỏ qua khi máy không có LibreOffice)
- Chuyển kiểm thử: `test_office_tools.py`, `test_office_diff_and_library.py` (phần office), `test_extract_cells.py`, `test_extract_images.py` → `tests/office/`

**Giao diện:**
- `brse.office.xlsx` (nơi duy nhất trong gói gọi `openpyxl.load_workbook`):
  - `load(path: Path, values: bool = False)` — `values=True` ứng với `data_only=True`; `diff.py` và `text.apply` dùng hàm này.
  - `read_cells(path: Path) -> dict[str, list[dict]]` — đúng định dạng đầu ra của `extract-cells.py` hiện nay.
  - `sheet_rows(path: Path) -> list[tuple[str, str, list[list[object]]]]` — (tên, trạng thái hiển thị, các hàng có dữ liệu); `kb-ingest` dùng.
  - `sheet_info(path: Path) -> list[dict]` — tên, hiển thị, vùng dùng, số hình, số biểu đồ.
  - `text_cells(wb) -> Iterator[tuple[str, Worksheet, openpyxl.cell.Cell]]` — ô chữ không phải công thức, mã `Sheet!A1`.
  - `cell_value(path: Path, ref: str) -> object` — `verify-claims` dùng.
  - `has_drawings(path: Path) -> bool`, `extract_images(path: Path, out_dir: Path) -> list[dict]`.
- `brse.office.tools`: `find_cli(kind: str, config: dict) -> tuple[str | None, str]`, `run(args, timeout=300)`, `soffice() -> str | None`.
- `brse.office.render`: `op_info`, `op_render`, `op_check` — chữ ký như trong `office.py` hiện nay. Riêng .xlsx qua LibreOffice: có `pdftoppm` thì đi đường PDF như hiện nay, không có thì `soffice --headless --convert-to png` như `render-sheet.py` cũ.
- `brse.office.text`: `extract(path: Path, max_chars: int) -> dict`, `apply(path: Path, translations: dict, out: Path, config: dict) -> dict`.
- `brse.office.diff`: `diff(before: Path, after: Path) -> dict`.
- Lệnh: `office`, `office-text`, `office-diff`, `extract-cells`, `extract-images`.

- [ ] **Bước 1:** chuyển các tệp kiểm thử, đổi cách gọi sang `run_cli`; thêm `test_office_render_xlsx_without_pdftoppm` (mô tả ở phần Tệp).
- [ ] **Bước 2:** chạy → thất bại vì chưa có lệnh.
- [ ] **Bước 3:** dời logic vào `brse/office/`; `docx_paragraphs`, `pptx_paragraphs` nằm ở `docx.py`, `pptx.py` và được `text.py`, `diff.py` import thẳng (bỏ `spec_from_file_location`).
- [ ] **Bước 4:** `python -m pytest -q` → toàn bộ qua.
- [ ] **Bước 5: Commit** `refactor: office package with one xlsx reader`

### Nhiệm vụ 3: Kho tài liệu

**Tệp:** tạo `brse/knowledge/{ingest,search,doc2md}.py`; lớp vỏ `scripts/kb-ingest.py`, `scripts/kb-search.py`, `skills/doc-to-md/scripts/doc2md.py`; chuyển `test_kb.py` → `tests/knowledge/`.

**Giao diện:**
- Dùng: `brse.office.xlsx.sheet_rows`, `brse.office.docx`, `brse.office.pptx`.
- Tạo: `convert(path: Path) -> tuple[list[tuple[str, str]], list[str]]` (giữ nguyên, `verify-claims` dùng), `source_files(root: Path, config: dict)`, `ingest(root: Path, force: bool) -> dict`, `search(root: Path, query: str, limit: int, origin: str | None) -> dict`.
- Lệnh: `kb-ingest`, `kb-search`, `doc2md`.

- [ ] **Bước 1:** chuyển kiểm thử, đổi cách gọi; thêm `test_ingest_and_extract_agree_on_xlsx`: một .xlsx có 1 hình và có ô công thức → `kb-ingest` báo `partial`; tập mã ô của `office-text extract` bằng tập ô của `extract-cells` có giá trị là chữ và `formula` là `None`.
- [ ] **Bước 2:** chạy → thất bại vì chưa có lệnh.
- [ ] **Bước 3:** dời logic; `convert_xlsx` đọc qua `sheet_rows`.
- [ ] **Bước 4:** `python -m pytest -q` → qua.
- [ ] **Bước 5: Commit** `refactor: knowledge package`

### Nhiệm vụ 4: Rà soát

**Tệp:** tạo `brse/review/{agents,judge,wording,claims,hedge}.py`; lớp vỏ `scripts/ask-agent.py`, `scripts/judge.py`, `scripts/wording.py`, `scripts/verify-claims.py`, `skills/verify-output/scripts/lint-hedge-words.py`; chuyển `test_quality.py`, `test_wording.py`, `test_agents_and_mt.py` (phần ask-agent), `test_lint_hedge_words.py` → `tests/review/`.

**Giao diện:**
- Tạo: `agents.ask(prompt: str, config: dict, timeout: int) -> dict`; `judge.verdict(reply: str, config: dict) -> dict`; `wording.verdict(reply: str) -> dict`, `wording.text_of(path: Path) -> str`; `claims.check(claim: dict, root: Path) -> dict`; `hedge.lint(text: str, source_tag: str) -> list[dict]`.
- `wording.text_of` cho `.drawio` gọi `brse.diagram.model.labels(path)` — Nhiệm vụ 7 tạo hàm này; tới lúc đó giữ cách nạp cũ, đổi ở Nhiệm vụ 7.
- Lệnh: `ask-agent`, `judge`, `wording`, `verify-claims`, `lint-hedge-words`.

- [ ] **Bước 1–5** như Nhiệm vụ 3. Commit `refactor: review package`

### Nhiệm vụ 5: Dịch

**Tệp:** tạo `brse/translate/{mt,glossary,consistency,lint}.py`; lớp vỏ `scripts/mt.py`, `scripts/lang-lint.py`, `skills/jp-vi-translate/scripts/check-glossary.py`, `check-consistency.py`; chuyển `test_check_glossary.py`, `test_check_consistency.py`, phần mt của `test_agents_and_mt.py`, phần lang-lint của `test_quality.py` / `test_office_tools.py` → `tests/translate/`.

**Giao diện:** `mt.translate(text: str, src: str | None, dst: str, config: dict) -> dict`; `glossary.parse(path: Path) -> list[dict]`, `glossary.check(text: str, path: Path) -> list[dict]`; `consistency.check(entries: list[dict]) -> dict`; `lint.lint(text: str, lang: str, source_lang: str | None) -> list[dict]`. Lệnh: `mt`, `lang-lint`, `check-glossary`, `check-consistency`.

- [ ] **Bước 1–5** như Nhiệm vụ 3. Commit `refactor: translate package`

### Nhiệm vụ 6: Bộ nhớ dự án, hook, sửa hook chặn khóa

**Tệp:** tạo `brse/hooks.py`, `brse/project/{register,memory,feedback,library,keys,doctor}.py`; lớp vỏ `scripts/{register,feedback-stats,library,set-key,doctor}.py`; `memory-inject.py`, `memory-log.py`, `guard-secrets.py` thành lớp vỏ gọi `hook session-start|stop|guard` (bị xóa ở Nhiệm vụ 9); sửa `hooks/hooks.json`; chuyển `test_register.py`, `test_memory_hooks.py`, `test_guard_secrets.py`, `test_doctor.py`, phần library → `tests/project/`.

**Giao diện:**
- `hooks.session_start(data: dict) -> str`, `hooks.stop(data: dict) -> None`, `hooks.guard(data: dict) -> tuple[int, str]` (mã 0 hoặc 2, thông điệp cho stderr).
- `feedback.stats(log: Path, days: int | None) -> dict` (giữ nguyên từ `feedback-stats.py`).
- Lệnh: `hook session-start|stop|guard` (đọc stdin bằng `config.read_hook_input`), `register`, `feedback-stats`, `library`, `set-key`, `doctor`.
- `hooks.json`, mỗi lệnh có dạng:
  `"$(command -v python3 || command -v python)" "${CLAUDE_PLUGIN_ROOT}/scripts/brse.py" hook guard`
  — chạy đúng một lần, mã thoát đi thẳng ra ngoài.
- `session_start` import thẳng `brse.knowledge.ingest.source_files` (để so tệp với danh mục) và `feedback.stats` (bỏ `spec_from_file_location`). Việc nạp lại tài liệu đổi vẫn chạy bằng tiến trình con `scripts/brse.py kb-ingest` với `timeout=60` như hiện nay, chỉ khi ≤ 5 tệp đổi — giữ đúng hành vi cũ, để hook không bị treo theo một tệp lỗi.

- [ ] **Bước 1:** thêm `test_hooks_json_guard_command_blocks`: đọc lệnh `PreToolUse` từ `hooks/hooks.json`, thay `${CLAUDE_PLUGIN_ROOT}` bằng gốc plugin, chạy `bash -c` với stdin `{"tool_name":"Read","tool_input":{"file_path":"/x/.brse/config.local.json"}}` → mã 2, stderr chứa `Blocked`. Thêm `test_hooks_json_other_hooks_exit_0` cho `SessionStart`, `Stop` với stdin `{}`. Bỏ qua trên máy không có `bash`. Thêm `test_doctor_runs_without_third_party_packages` theo cùng cách với kiểm thử `config` ở Nhiệm vụ 1, khẳng định `openpyxl` có `found: false`.
- [ ] **Bước 2:** chạy → `test_hooks_json_guard_command_blocks` thất bại với mã 0 (đúng lỗi đã ghi ở phần Căn cứ).
- [ ] **Bước 3:** dời logic, sửa `hooks.json`.
- [ ] **Bước 4:** `python -m pytest -q` → qua.
- [ ] **Bước 5: Commit** `fix: hook commands run once; refactor: project package`

### Nhiệm vụ 7: Sơ đồ — tách `drawio-tool.py` (961 dòng)

**Tệp:** tạo `brse/diagram/templates.py` (đọc app.asar, catalog, suggest), `model.py` (giải mã XML, cells, edit, build, kiểu hình), `checks.py` (lint, check, reader-test), `export.py`; lớp vỏ `scripts/drawio-tool.py`; chuyển `test_drawio_tool.py` → `tests/diagram/`; sửa `brse/review/wording.py` dùng `model.labels`.

**Giao diện:** `model.load(path) -> ET.Element`, `model.labels(path: Path) -> list[str]`, `model.build(model: dict, out: Path) -> dict`, `model.edit(path, changes: dict, out) -> dict`; `checks.lint(path) -> list[dict]`, `checks.check(path, changes: list | None) -> dict`; `templates.catalog(config) -> list[dict]`, `templates.suggest(needs: dict, catalog: list) -> dict`; `export.export(path, out, layout: str | None, config: dict) -> dict`. Lệnh: `drawio-tool <lệnh con>` giữ nguyên các lệnh con hiện có.

- [ ] **Bước 1–5** như Nhiệm vụ 3. Commit `refactor: split diagram tool`

### Nhiệm vụ 8: Công cụ mã nguồn và ảnh

**Tệp:** tạo `brse/code/{refs,structured_diff,ocr}.py`; lớp vỏ `extract-refs.py`, `diff-structured.py`, `ocr-pass.py`; chuyển kiểm thử tương ứng → `tests/code/`. Lệnh: `extract-refs`, `diff-structured`, `ocr-pass`.

- [ ] **Bước 1–5** như Nhiệm vụ 3. Commit `refactor: code tools package`

### Nhiệm vụ 9: Đổi văn bản sang lối vào mới, xóa tệp cũ

**Tệp:**
- Sửa: mọi `skills/*/SKILL.md`, `commands/*.md` (gồm khối `CLAUDE.md` trong `init.md`), `agents/*.md`, `README.md`.
- Xóa: mọi lớp vỏ trong `scripts/` (trừ `brse.py`) và `skills/*/scripts/`, `scripts/brse_common.py`, `scripts/tests/`, `skills/*/scripts/tests/`; `pytest.ini` còn `testpaths = tests`.
- Sửa: `tests/test_plugin_structure.py` (chuyển từ `scripts/tests/`).

**Giao diện:** dùng `brse.cli` để lấy danh sách lệnh đã đăng ký: thêm `brse.cli.command_names() -> set[str]`.

- [ ] **Bước 1:** trong `test_plugin_structure.py` thêm:
  - `test_docs_call_only_registered_commands`: mọi chuỗi `scripts/brse.py <tên>` trong `skills/`, `commands/`, `agents/`, `README.md` có `<tên>` thuộc `command_names()`.
  - `test_docs_mention_no_old_script`: trong các tệp trên, mọi chữ khớp `[\w-]+\.py\b` đều là `brse.py` (bắt cả tên trần như `office-diff.py` trong quy tắc 6 của khối `CLAUDE.md`), và không còn `skills/[\w-]+/scripts/`.
  - `test_no_spec_from_file_location`: không tệp nào trong `brse/` chứa `spec_from_file_location`.
- [ ] **Bước 2:** chạy → thất bại (văn bản còn đường dẫn cũ).
- [ ] **Bước 3:** thay `${CLAUDE_PLUGIN_ROOT}/scripts/<tên>.py` và `${CLAUDE_PLUGIN_ROOT}/skills/<k>/scripts/<tên>.py` bằng `${CLAUDE_PLUGIN_ROOT}/scripts/brse.py <tên>`; `render-sheet.py` → `brse.py office render`; `brse-config.py` → `brse.py config`; tên trần (`office-diff.py`, `ask-agent.py`, `set-key.py`…) → `brse.py <tên>`. Xóa tệp cũ.
- [ ] **Bước 4:** `python -m pytest -q` → qua; `claude plugin validate .` → "Validation passed".
- [ ] **Bước 5: Commit** `refactor: docs call scripts/brse.py; remove old scripts`

---

## Ngoài phạm vi kế hoạch này (mỗi mục là một kế hoạch riêng, làm sau)

- Sửa cách dịch (một tài liệu một ngữ cảnh, ngữ cảnh cho từng ô, bảng song ngữ, `lang-lint` chấp nhận thuật ngữ gốc trong 「」).
- Bắt buộc xem lại bằng hook `Stop` và biên bản kiểm tra.
- Viết lại văn bản kỹ năng: một tệp định nghĩa luồng, gom đoạn "Before running", bỏ con số không căn cứ, bỏ tên không có trong gói.
- Commit hay bỏ 5 kỹ năng mới và `register.py` đang chưa commit — kế hoạch này coi `register.py` là mã hiện có và chuyển nó ở Nhiệm vụ 6.
