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


def test_no_duplicate_keys_no_warning(tmp_path):
    old = [{"key": "受注No", "value": "要"}]
    new = [{"key": "受注No", "value": "不要"}]
    out, _ = run(old, new, tmp_path)
    assert "warning" not in out


def test_duplicate_key_in_source_is_flagged_not_silently_dropped(tmp_path):
    """Regression: a repeated key in the source sheet (e.g. a merged-header
    artifact, or two rows with the same item name) used to silently collapse
    to whichever occurrence the dict comprehension kept last, with no signal
    that a row had been dropped from the comparison."""
    old = [{"key": "受注No", "value": "要"}, {"key": "受注No", "value": "不要"}]
    new = [{"key": "受注No", "value": "不要"}]
    out, _ = run(old, new, tmp_path)
    assert "warning" in out
    assert out["duplicate_keys_old"] == ["受注No"]
    assert "duplicate_keys_new" not in out
