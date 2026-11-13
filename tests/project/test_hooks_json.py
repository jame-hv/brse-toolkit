"""Run the exact commands written in hooks/hooks.json, the way Claude Code runs them."""
import json
import shutil
import subprocess

import pytest

from brse_testkit import ROOT

pytestmark = pytest.mark.skipif(shutil.which("bash") is None, reason="bash not available")


def hook_command(event):
    h = json.loads((ROOT / "hooks" / "hooks.json").read_text(encoding="utf-8"))
    return h["hooks"][event][0]["hooks"][0]["command"].replace("${CLAUDE_PLUGIN_ROOT}", str(ROOT))


def run(event, payload, cwd):
    return subprocess.run(["bash", "-c", hook_command(event)], input=json.dumps(payload),
                          capture_output=True, text=True, encoding="utf-8", cwd=cwd)


def test_hooks_json_guard_command_blocks(tmp_path):
    r = run("PreToolUse", {"tool_name": "Read", "tool_input": {"file_path": "/x/.brse/config.local.json"}}, tmp_path)
    assert r.returncode == 2
    assert "Blocked" in r.stderr


def test_hooks_json_guard_command_allows_normal_work(tmp_path):
    r = run("PreToolUse", {"tool_name": "Read", "tool_input": {"file_path": "/x/README.md"}}, tmp_path)
    assert r.returncode == 0


@pytest.mark.parametrize("event", ["SessionStart", "Stop", "PreCompact"])
def test_hooks_json_other_hooks_exit_0(event, tmp_path):
    assert run(event, {}, tmp_path).returncode == 0


def test_stop_hook_blocks_while_a_translation_is_unchecked(ws, tmp_path):
    import openpyxl
    wb = openpyxl.Workbook()
    wb.active["A1"] = "項目"
    wb.save(ws / "src-docs" / "a.xlsx")
    transcript = tmp_path / "t.jsonl"
    transcript.write_text(json.dumps({"type": "user", "timestamp": "2020-01-01T00:00:00Z",
                                      "message": {"role": "user", "content": "dịch file a.xlsx"}}) + "\n",
                          encoding="utf-8")
    (ws / "tr.json").write_text(json.dumps({"Sheet!A1": "Hạng mục"}, ensure_ascii=False), encoding="utf-8")
    out = ws / ".brse" / "work" / "a_vi.xlsx"
    from brse_testkit import run_cli
    assert run_cli("office-text", "apply", ws / "src-docs" / "a.xlsx", ws / "tr.json", out, ws, cwd=ws).returncode == 0
    stop = {"session_id": "s1", "transcript_path": str(transcript), "cwd": str(ws)}
    blocked = run("Stop", stop, ws)
    assert blocked.returncode == 0 and json.loads(blocked.stdout)["decision"] == "block"
    assert "a_vi.xlsx" in json.loads(blocked.stdout)["reason"]
    assert run("Stop", {**stop, "stop_hook_active": True}, ws).stdout.strip() == ""  # shown once per version
    assert run_cli("translation-check", ws / "src-docs" / "a.xlsx", ws / "tr.json", out, "--lang", "vi",
                   cwd=ws).returncode == 0
    assert run("Stop", stop, ws).stdout.strip() == ""
