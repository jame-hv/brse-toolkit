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
