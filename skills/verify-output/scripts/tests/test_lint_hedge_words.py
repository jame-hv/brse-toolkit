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


def test_detects_missing_source_on_plain_prose_claim():
    """Regression: a concluding claim written as prose (no bullet marker) must
    be caught too — the original implementation only scanned "- " lines."""
    out, code = run("Doanh thu quý này tăng 20%.")
    assert code == 1
    assert any(v["type"] == "missing_source" for v in out["violations"])


def test_passes_clean_prose_claim_with_source():
    out, code = run("Doanh thu quý này tăng 20% (nguồn: báo cáo Q3.xlsx, sheet Tổng, dòng 5).")
    assert code == 0
    assert out["violations"] == []


def test_lead_in_line_without_terminal_punctuation_is_not_flagged():
    out, code = run("Kết quả kiểm tra:")
    assert code == 0
    assert out["violations"] == []


def test_headers_tables_and_code_fences_are_not_flagged():
    text = "\n".join([
        "## Kết quả",
        "| Cột A | Cột B |",
        "|---|---|",
        "```",
        "Doanh thu tăng 20%.",
        "```",
    ])
    out, code = run(text)
    assert code == 0
    assert out["violations"] == []


def test_japanese_fullwidth_question_mark_is_exempt():
    """Regression: detail-design-jp/jp-vi-translate output is sometimes
    Japanese — a genuine open question written with the real Japanese "？"
    used to be misread as an unsourced declarative claim."""
    out, code = run("入力手段はラジオボタンですか？")
    assert code == 0
    assert out["violations"] == []


def test_japanese_sentences_glued_without_space_are_split():
    """Regression: split_sentences required whitespace after the terminator,
    which Japanese prose never has between sentences — two JP sentences on
    one line used to be treated as one glued blob instead of two, so a
    source tag on the second sentence would have wrongly appeared to cover
    the first one too. Split correctly, each stands on its own — here
    neither has a real (nguồn: ...) tag, so both are correctly flagged."""
    out, _ = run("特需区分は0または1です。ソースはE0025のバリデーション定義です。")
    missing = {v["line"] for v in out["violations"] if v["type"] == "missing_source"}
    assert missing == {"特需区分は0または1です。", "ソースはE0025のバリデーション定義です。"}


def test_japanese_sentence_with_source_tag_is_not_flagged_by_neighbor():
    """The positive case for the split fix above: the first JP sentence is
    unsourced and must be flagged even though the very next sentence (glued,
    no space) does carry a real source tag — they must not be merged."""
    out, _ = run("特需区分は0または1です。テスト対象はE0025です (nguồn: 3.テストケース, B180)。")
    missing = {v["line"] for v in out["violations"] if v["type"] == "missing_source"}
    assert missing == {"特需区分は0または1です。"}


def test_multi_sentence_paragraph_flags_only_the_unsourced_sentence():
    text = "Trường A bắt buộc nhập. Trường B tùy chọn (nguồn: spec.xlsx, dòng 5)."
    out, code = run(text)
    assert code == 1
    missing = [v for v in out["violations"] if v["type"] == "missing_source"]
    assert len(missing) == 1
    assert missing[0]["line"].startswith("Trường A")
