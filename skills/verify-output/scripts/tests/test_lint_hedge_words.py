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


def test_hedge_word_inside_a_question_is_not_flagged():
    """spec mục 6.1: hedge words are only banned in conclusions, not when asking."""
    out, code = run("- Trường email có thể bắt buộc không?")
    assert code == 0
    assert out["violations"] == []
