import importlib.util
import json
import shutil
import subprocess
import sys
import pathlib

import pytest

SCRIPT = pathlib.Path(__file__).resolve().parents[1] / "extract-refs.py"

needs_rg = pytest.mark.skipif(shutil.which("rg") is None, reason="ripgrep (rg) not installed")


def _load_module():
    """Import extract-refs.py by path (hyphenated name isn't a valid module name)."""
    spec = importlib.util.spec_from_file_location("extract_refs", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


extract_refs = _load_module()


def run(path, *keywords):
    result = subprocess.run(
        [sys.executable, str(SCRIPT), str(path), *keywords],
        capture_output=True, text=True, encoding="utf-8",
    )
    return json.loads(result.stdout), result.returncode


# --- pure parsing logic: runs without the rg binary --------------------------

def test_parse_rg_output_extracts_file_line_content():
    out = extract_refs.parse_rg_output("src/order.py:12:    call_order_api()\n", "call_order_api")
    assert out == [{
        "keyword": "call_order_api",
        "file": "src/order.py",
        "line": 12,
        "content": "call_order_api()",
    }]


def test_parse_rg_output_handles_colons_inside_matched_content():
    out = extract_refs.parse_rg_output("a.py:3:d = {'k': 'v'}\n", "k")
    assert out[0]["line"] == 3
    assert out[0]["content"] == "d = {'k': 'v'}"


def test_parse_rg_output_skips_malformed_line_number_without_crashing():
    output = "good.py:7:hit\nbad.py:NOT_A_NUMBER:hit\nno-colons-at-all\n"
    out = extract_refs.parse_rg_output(output, "hit")
    assert [m["file"] for m in out] == ["good.py"]


def test_parse_rg_output_empty_input_returns_empty_list():
    assert extract_refs.parse_rg_output("", "anything") == []


# --- encoding fallback (spec mục 6.5) ---------------------------------------

def test_decode_output_reads_utf8():
    assert extract_refs.decode_output("在庫".encode("utf-8")) == "在庫"


def test_decode_output_falls_back_to_cp932_shift_jis():
    assert extract_refs.decode_output("在庫確認".encode("cp932")) == "在庫確認"


def test_decode_output_never_raises_on_undecodable_bytes():
    assert extract_refs.decode_output(b"\xff\xfe\x00garbage")  # replacement chars, no crash


# --- end-to-end through the real rg binary ----------------------------------

@needs_rg
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


@needs_rg
def test_multiple_keywords_searched_independently(tmp_path):
    src = tmp_path / "order.py"
    src.write_text("def get_inventory():\n    pass\n\ndef get_revenue():\n    pass\n", encoding="utf-8")
    out, _ = run(tmp_path, "get_inventory", "get_revenue")
    keywords_found = {m["keyword"] for m in out["matches"]}
    assert keywords_found == {"get_inventory", "get_revenue"}


@needs_rg
def test_no_match_returns_empty_list(tmp_path):
    src = tmp_path / "order.py"
    src.write_text("def unrelated():\n    pass\n", encoding="utf-8")
    out, _ = run(tmp_path, "nonexistent_symbol")
    assert out["matches"] == []


@needs_rg
def test_shift_jis_source_file_does_not_crash_the_run(tmp_path):
    """Legacy cp932 source file: must still grep, not raise UnicodeDecodeError."""
    legacy = tmp_path / "legacy.txt"
    legacy.write_bytes("# 在庫確認\ndef zaiko_check():\n    pass\n".encode("cp932"))
    out, code = run(tmp_path, "zaiko_check")
    assert code == 0
    assert len(out["matches"]) == 1
    assert out["matches"][0]["file"].endswith("legacy.txt")


@needs_rg
def test_bad_path_reports_error_instead_of_empty_matches(tmp_path):
    out, code = run(tmp_path / "does-not-exist", "anything")
    assert code == 1
    assert "error" in out
