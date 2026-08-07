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
