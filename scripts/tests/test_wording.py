import json

from conftest import run_script


def test_prompt_carries_project_conventions_and_text(ws, tmp_path):
    (ws / ".brse" / "memory" / "long" / "conventions.md").write_text(
        '- wording: "có cột cần khay" → "mỗi mặt hàng có ghi có cần đặt lên khay hay không" — status: active\n', encoding="utf-8")
    cfg = json.loads((ws / ".brse" / "config.json").read_text(encoding="utf-8"))
    cfg["review"] = {"second_agent": ["claude-subagent"]}
    (ws / ".brse" / "config.json").write_text(json.dumps(cfg), encoding="utf-8")
    t = tmp_path / "a.txt"
    t.write_text("Có cột cần khay.", encoding="utf-8")
    r = run_script("wording.py", "run", t, "--project", ws, tmp=tmp_path)
    out = json.loads(r.stdout)
    assert r.returncode == 1 and out["provider"] == "none"
    prompt = open(out["prompt_file"], encoding="utf-8").read()
    assert "có cột cần khay" in prompt and "Có cột cần khay." in prompt and "translated-feel" in prompt


def test_parse_passes_only_with_no_issues_and_rejects_vague_replies(tmp_path):
    ok = tmp_path / "ok.txt"
    ok.write_text('{"issues": []}', encoding="utf-8")
    assert run_script("wording.py", "parse", ok).returncode == 0
    bad = tmp_path / "bad.txt"
    bad.write_text(json.dumps({"issues": [{"text": "Có cột cần khay.", "type": "unclear",
                                           "problem": "cột không cần khay", "rewrite": "Mỗi mặt hàng có ghi…"}]},
                              ensure_ascii=False), encoding="utf-8")
    out = json.loads(run_script("wording.py", "parse", bad).stdout)
    assert out["pass"] is False and out["issues"][0]["rewrite"].startswith("Mỗi")
    lazy = tmp_path / "lazy.txt"
    lazy.write_text('{"issues": [{"text": "x", "type": "style"}]}', encoding="utf-8")
    assert "malformed" in json.loads(run_script("wording.py", "parse", lazy).stdout)
