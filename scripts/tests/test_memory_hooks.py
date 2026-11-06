import datetime
import json

from conftest import run_script


def transcript(path, user_msgs, written=("out/estimate.xlsx",), reply="Done: estimate updated."):
    lines = [{"type": "user", "timestamp": "2026-03-02T09:00:00Z",
              "message": {"role": "user", "content": "<system-reminder>ignore me</system-reminder>"}}]
    for m in user_msgs:
        lines.append({"type": "user", "message": {"role": "user", "content": [{"type": "text", "text": m}]}})
    lines.append({"type": "user", "message": {"role": "user", "content": [
        {"type": "tool_result", "tool_use_id": "x", "content": "tool output, not a request"}]}})
    lines.append({"type": "assistant", "message": {"role": "assistant", "content": [
        {"type": "tool_use", "name": "Write", "input": {"file_path": f}} for f in written]
        + [{"type": "text", "text": reply}]}})
    path.write_text("\n".join(json.dumps(l, ensure_ascii=False) for l in lines), encoding="utf-8")
    return path


def hook_input(ws, t, session="abcdef1234567890"):
    return json.dumps({"session_id": session, "transcript_path": str(t), "cwd": str(ws)})


def test_memory_log_writes_requests_files_and_reply(ws, tmp_path):
    t = transcript(tmp_path / "t.jsonl", ["Check the estimate sheet", "Shorter, please"])
    r = run_script("memory-log.py", stdin=hook_input(ws, t), tmp=tmp_path)
    assert r.returncode == 0
    log = ws / ".brse" / "memory" / "short" / "2026-03-02-abcdef12.md"
    text = log.read_text(encoding="utf-8")
    assert "1. Check the estimate sheet" in text and "2. Shorter, please" in text
    assert "out/estimate.xlsx" in text and "Done: estimate updated." in text
    assert "ignore me" not in text and "tool output" not in text


def test_memory_log_is_idempotent(ws, tmp_path):
    t = transcript(tmp_path / "t.jsonl", ["A request"])
    run_script("memory-log.py", stdin=hook_input(ws, t), tmp=tmp_path)
    first = (ws / ".brse" / "memory" / "short" / "2026-03-02-abcdef12.md").read_text(encoding="utf-8")
    run_script("memory-log.py", stdin=hook_input(ws, t), tmp=tmp_path)
    files = list((ws / ".brse" / "memory" / "short").glob("*.md"))
    assert len(files) == 1 and files[0].read_text(encoding="utf-8") == first


def test_memory_log_does_nothing_outside_a_workspace(tmp_path):
    plain = tmp_path / "plain"
    plain.mkdir()
    t = transcript(tmp_path / "t.jsonl", ["hello"])
    r = run_script("memory-log.py", stdin=json.dumps({"transcript_path": str(t), "cwd": str(plain)}), tmp=tmp_path)
    assert r.returncode == 0 and not (plain / ".brse").exists()


def test_memory_log_never_fails_on_garbage_input(ws, tmp_path):
    r = run_script("memory-log.py", stdin="not json", tmp=tmp_path)
    assert r.returncode == 0


def test_inject_shows_workspace_conventions_feedback_and_previous_session(ws, tmp_path):
    long = ws / ".brse" / "memory" / "long"
    (long / "conventions.md").write_text(
        "# Conventions\n\nEntry schema:\n- <what> → <rule>\n"
        "- estimate cells → short noun phrases — source: user, 2026-03-01 — status: active\n"
        "- old rule — status: superseded by 2026-03-02\n", encoding="utf-8")
    today = datetime.date.today().isoformat()
    (long / "feedback-log.md").write_text(
        f"- {today} | did-not-read-source | read the whole RFP | rule: none\n"
        f"- {today} | did-not-read-source | pptx skipped | rule: none\n", encoding="utf-8")
    (ws / ".brse" / "memory" / "short" / "2026-03-01-11111111.md").write_text(
        "# Session 11111111\n\n## Requests (1)\n1. Translate the Q&A\n\n## Files written\n- x\n", encoding="utf-8")
    r = run_script("memory-inject.py", stdin=json.dumps({"cwd": str(ws), "session_id": "22222222"}), tmp=tmp_path)
    out = r.stdout
    assert r.returncode == 0
    assert "workspace 'demo'" in out
    assert "estimate cells → short noun phrases" in out and "old rule" not in out
    assert "did-not-read-source (2)" in out
    assert "Translate the Q&A" in out


def test_inject_warns_about_old_layout(ws, tmp_path):
    cfg = ws / ".brse" / "config.json"
    data = json.loads(cfg.read_text(encoding="utf-8"))
    del data["layout_version"]
    cfg.write_text(json.dumps(data), encoding="utf-8")
    r = run_script("memory-inject.py", stdin=json.dumps({"cwd": str(ws)}), tmp=tmp_path)
    assert "older than this plugin" in r.stdout


def test_inject_hints_migration_for_1x_layout(tmp_path):
    old = tmp_path / "old"
    (old / "memory").mkdir(parents=True)
    (old / "memory" / "glossary.md").write_text("# Glossary\n", encoding="utf-8")
    r = run_script("memory-inject.py", stdin=json.dumps({"cwd": str(old)}), tmp=tmp_path)
    assert "1.x workspace" in r.stdout


def test_feedback_stats_counts_and_filters(ws, tmp_path):
    old = (datetime.date.today() - datetime.timedelta(days=90)).isoformat()
    today = datetime.date.today().isoformat()
    (ws / ".brse" / "memory" / "long" / "feedback-log.md").write_text(
        f"- {today} | translation | too literal | rule: none\n"
        f"- {today} | made-up-cat | x | rule: none\n"
        f"- {old} | translation | old one | rule: none\n", encoding="utf-8")
    out = json.loads(run_script("feedback-stats.py", ws, tmp=tmp_path).stdout)
    assert out["total"] == 3 and out["by_category"]["translation"] == 2
    assert out["unknown_categories"] == ["made-up-cat"] and out["by_category"]["other"] == 1
    recent = json.loads(run_script("feedback-stats.py", ws, "--days", "30", tmp=tmp_path).stdout)
    assert recent["total"] == 2


def test_slash_command_is_logged_as_command_and_expansion_skipped(ws, tmp_path):
    t = tmp_path / "t.jsonl"
    lines = [
        {"type": "user", "timestamp": "2026-03-03T09:00:00Z", "message": {"role": "user", "content":
            "<command-message>brse-toolkit:ingest</command-message>\n<command-name>/brse-toolkit:ingest</command-name>\n"
            "<command-args>only the new files</command-args>"}},
        {"type": "user", "isMeta": True, "message": {"role": "user", "content": [
            {"type": "text", "text": "Run these steps in the current directory ... (command body)"}]}},
        {"type": "user", "isMeta": True, "message": {"role": "user", "content": [
            {"type": "text", "text": "Base directory for this skill: /x/skills/cross-check ..."}]}},
        {"type": "assistant", "message": {"role": "assistant", "content": [{"type": "text", "text": "Ingested 2 files."}]}},
    ]
    t.write_text("\n".join(json.dumps(l) for l in lines), encoding="utf-8")
    run_script("memory-log.py", stdin=hook_input(ws, t), tmp=tmp_path)
    text = (ws / ".brse" / "memory" / "short" / "2026-03-03-abcdef12.md").read_text(encoding="utf-8")
    assert "1. /brse-toolkit:ingest only the new files" in text
    assert "command body" not in text and "Base directory" not in text
    assert "## Requests (1)" in text


def test_inject_includes_outcome_of_previous_session(ws, tmp_path):
    (ws / ".brse" / "memory" / "short" / "2026-03-01-11111111.md").write_text(
        "# Session 11111111\n\n## Requests (1)\n1. Compare A and B\n\n## Files written\n(none)\n\n"
        "## Last reply\nVerdict: 3 items compared, 1 differs (会員登録).\n", encoding="utf-8")
    r = run_script("memory-inject.py", stdin=json.dumps({"cwd": str(ws), "session_id": "22222222"}), tmp=tmp_path)
    assert "Compare A and B" in r.stdout and "1 differs (会員登録)" in r.stdout
