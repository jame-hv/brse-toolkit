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
