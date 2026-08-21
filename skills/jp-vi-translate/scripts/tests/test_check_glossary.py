import json
import subprocess
import sys
import pathlib

SCRIPT = pathlib.Path(__file__).resolve().parents[1] / "check-glossary.py"

GLOSSARY = '''# Glossary EN-VI-JP

- EN: register | VI: Lưu | JP: 登録 — nguồn: spec.xlsx v2, P45, xác nhận 2026-07-20
- EN: required field | VI: trường bắt buộc | JP: 必須項目 — nguồn: spec.xlsx v1, P10, xác nhận 2026-07-01
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


def test_finds_known_term_by_jp_form(tmp_path):
    out, code = run("ユーザーが登録ボタンを押下した場合", GLOSSARY, tmp_path)
    assert code == 0
    assert {"en": "register", "vi": "Lưu", "jp": "登録"} in out["matches"]


def test_finds_known_term_by_vi_form(tmp_path):
    out, code = run("Người dùng bấm nút Lưu.", GLOSSARY, tmp_path)
    assert {"en": "register", "vi": "Lưu", "jp": "登録"} in out["matches"]


def test_no_match_when_term_absent(tmp_path):
    out, _ = run("画面のレイアウトについて", GLOSSARY, tmp_path)
    assert out["matches"] == []


def test_finds_multiple_terms(tmp_path):
    out, _ = run("必須項目に登録ボタン", GLOSSARY, tmp_path)
    jp_terms = {m["jp"] for m in out["matches"]}
    assert jp_terms == {"登録", "必須項目"}


def test_schema_example_line_is_not_parsed_as_a_real_entry(tmp_path):
    """Regression: the placeholder line /brse-toolkit:init scaffolds at the
    top of every fresh glossary.md ("- EN: <term> | VI: <term> | JP: <term>
    — <source note>") used to match the same pattern as a real entry."""
    glossary = (
        "# Glossary EN-VI-JP\n\n"
        "Entry schema:\n"
        "- EN: <term> | VI: <term> | JP: <term> — <source note>\n\n"
        "- EN: screen | VI: màn hình | JP: 画面 — khởi tạo mặc định\n"
    )
    out, _ = run("画面の<term>について", glossary, tmp_path)
    assert {"en": "screen", "vi": "màn hình", "jp": "画面"} in out["matches"]
    assert len(out["matches"]) == 1


def test_missing_glossary_file_returns_empty_not_a_crash(tmp_path):
    """Regression: a project with no memory/glossary.md yet (not initialized,
    or initialized but no term confirmed yet) used to crash with
    FileNotFoundError instead of just reporting no known terms."""
    text_file = tmp_path / "text.txt"
    text_file.write_text("登録ボタン", encoding="utf-8")
    missing_glossary = tmp_path / "does-not-exist.md"
    result = subprocess.run(
        [sys.executable, str(SCRIPT), str(text_file), str(missing_glossary)],
        capture_output=True, text=True, encoding="utf-8",
    )
    out = json.loads(result.stdout)
    assert result.returncode == 0
    assert out["matches"] == []
