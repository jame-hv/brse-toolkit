"""Claude Code hooks: `brse.py hook session-start | stop | precompact | guard | agent-done` (stdin = the hook's JSON).

session-start, stop, precompact and agent-done never break the session (errors are swallowed, exit 0);
guard exits 2 to refuse a tool call.
session-start records the session (transcript path) in .brse/runs/current.json for `brse.py gate`.
stop refuses to end the turn once per version of a deliverable file the agent changed in this session
without a valid gate stamp, or of a translated copy not passed `brse.py translation-check`; then it stays quiet.
tool-done (with guard before Bash) records which Office files the agent's own tool calls changed.
agent-done stores the plugin's wording-reviewer answer for `brse.py gate check`.
"""
import datetime
import io
import json
import sys
import time
from pathlib import Path

HOOKS = {"session-start": "brse.project.memory_inject", "stop": "brse.project.memory_log",
         "precompact": "brse.project.memory_log", "guard": "brse.project.guard", "agent-done": None, "tool-done": None}


def session_start_time(transcript: str) -> float:
    from brse.project import memory_log
    first = memory_log.parse(Path(transcript))[3] if transcript and Path(transcript).is_file() else None
    if not first:
        return 0.0
    return datetime.datetime.fromisoformat(first.replace("Z", "+00:00")).timestamp()


def unchecked_translations(data: dict) -> list:
    from brse.translate import record
    return record.pending(session_start_time(data.get("transcript_path") or ""), Path(data.get("cwd") or "."))


def unstamped_files(data: dict) -> list:
    from brse import config as brse_config
    from brse.harness import gate
    root, config = brse_config.workspace(data.get("cwd") or ".")
    if not root:
        return []
    return gate.unstamped(root, config, data.get("session_id") or "")


def record_session(data: dict) -> None:
    from brse import config as brse_config
    root = brse_config.find_workspace(Path(data.get("cwd") or ".").resolve())
    if root and data.get("transcript_path"):
        d = root / ".brse" / "runs"
        d.mkdir(parents=True, exist_ok=True)
        (d / "current.json").write_text(json.dumps({"session_id": data.get("session_id"),
                                                    "transcript_path": data["transcript_path"],
                                                    "at": time.time()}), encoding="utf-8")


def stop_decision(data: dict):
    """Refuse the turn end ONCE per version of each unchecked file, then stay quiet about it: the user's
    other questions must not be held hostage by a file they may not want reviewed yet."""
    from brse import config as brse_config
    files, translations = unstamped_files(data), unchecked_translations(data)
    root = brse_config.find_workspace(Path(data.get("cwd") or ".").resolve())
    if not root or not (files or translations):
        return None
    f = root / ".brse" / "runs" / f"stop-{data.get('session_id') or 'none'}.json"
    try:
        seen = json.loads(f.read_text()).get("seen", {}) if f.is_file() else {}
    except ValueError:
        seen = {}
    version = lambda rel: str((root / rel).stat().st_mtime) if (root / rel).exists() else rel
    files = [x for x in files if seen.get(x) != version(x)]
    translations = [x for x in translations if seen.get(x) != version(x)]
    if not files and not translations:
        return None
    seen.update({x: version(x) for x in files + translations})
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(json.dumps({"seen": seen}, ensure_ascii=False))
    what = []
    if files:
        what.append("deliverable files changed in this session without a valid gate stamp: " + ", ".join(files)
                    + " — run `brse.py gate check <file> [--original <file>] [--kind estimate-cell|text]` on each")
    if translations:
        what.append("translated copies not passed `brse.py translation-check`: " + ", ".join(translations))
    return {"decision": "block", "reason": "Not handed back yet — " + "; ".join(what) + ". (Shown once per "
            "file version; if the user asked about something else, answer that and tell them in one line "
            "that this file has not passed the final check.)"}


def agent_done(data: dict) -> None:
    """Store a reviewer's answer for `gate check` / `judge`. A reviewer run in the background only has a
    launch notice here; then its transcript is recorded and read once it has finished."""
    import re
    from brse.harness import gate
    inp = data.get("tool_input") or {}
    if not str(inp.get("subagent_type", "")).endswith("reviewer"):  # wording-reviewer and reviewer
        return
    prompt, cwd, resp = str(inp.get("prompt", "")), data.get("cwd") or ".", data.get("tool_response")
    if isinstance(resp, dict) and isinstance(resp.get("handbackReport"), dict):  # Claude Code 2.1.3xx
        gate.capture(prompt, str(resp["handbackReport"].get("text", "")), cwd)
        return
    agent_id = resp.get("agentId") if isinstance(resp, dict) else None
    if isinstance(resp, dict):
        resp = resp.get("content", resp)
    if isinstance(resp, list):
        resp = "\n".join(b.get("text", "") for b in resp if isinstance(b, dict))
    resp = str(resp)
    m = None if agent_id else re.search(r"agentId:\s*([\w-]+)", resp)
    agent_id = agent_id or (m.group(1) if m else None)
    t = data.get("transcript_path")
    if not agent_id or not t:
        gate.capture(prompt, resp, cwd)
        return
    sub = gate.subagent_file(t, agent_id)
    finished, report = gate.subagent_reply(sub)
    if finished:
        gate.capture(prompt, report or resp, cwd)
    else:
        gate.capture(prompt, "", cwd, agent=str(sub))


def run_with_stdin(module: str, raw: str) -> None:
    import importlib
    old = sys.stdin
    sys.stdin = io.StringIO(raw)
    try:
        importlib.import_module(module).main()
    finally:
        sys.stdin = old


def main():
    name = sys.argv[1] if len(sys.argv) > 1 else ""
    if name not in HOOKS:
        print(f"usage: brse.py hook {'|'.join(HOOKS)}", file=sys.stderr)
        return 2
    raw = sys.stdin.read()
    if name in ("guard", "tool-done"):
        try:  # which Office files the agent's own tool calls change — the Stop hook checks only those
            from brse import config as brse_config
            from brse.harness import gate
            d = json.loads(raw or "{}")
            root = brse_config.find_workspace(Path(d.get("cwd") or ".").resolve())
            if root and name == "guard" and d.get("tool_name") == "Bash":
                gate.snapshot(root, d.get("session_id") or "")
            elif root and name == "tool-done":
                gate.after_tool(root, d.get("session_id") or "", d.get("tool_name") or "", d.get("tool_input") or {})
        except Exception:
            pass
        if name == "tool-done":
            return 0
    if name == "guard":
        run_with_stdin(HOOKS[name], raw)  # exits 0 or 2 itself
        return 0
    try:
        data = json.loads(raw or "{}")
    except ValueError:
        data = {}
    if name == "agent-done":
        try:
            agent_done(data)
        except Exception:
            pass
        return 0
    try:
        run_with_stdin(HOOKS[name], raw)
    except BaseException:  # a hook must never break the user's session
        pass
    if name == "session-start":
        try:
            record_session(data)
        except Exception:
            pass
    if name == "stop":
        try:
            out = stop_decision(data)
        except Exception:
            out = None
        if out:
            print(json.dumps(out, ensure_ascii=False))
    return 0
