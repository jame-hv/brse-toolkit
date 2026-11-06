#!/usr/bin/env python3
"""Hook for Stop / PreCompact: write this session's short-term log.

Reads the hook JSON on stdin ({session_id, transcript_path, cwd}) and rewrites
.brse/memory/short/<date>-<session8>.md from the transcript: the user's
requests, files written, and the last reply. Computed, not summarised by an
LLM; regenerated in full each time, so running it twice never duplicates.
Also deletes short logs older than memory.short_retention_days.
Does nothing outside a brse-toolkit workspace. Never fails the session: any
error is swallowed and the exit code is 0.
"""
import sys

sys.dont_write_bytecode = True
import json
import re
import time
from pathlib import Path

import brse_common

SKIP_PREFIXES = ("<system-reminder", "<command-", "<local-command", "<task-notification",
                 "Caveat:", "[Request interrupted", "Base directory for this skill")
WRITE_TOOLS = {"Write", "Edit", "MultiEdit", "NotebookEdit"}
COMMAND_RE = re.compile(r"<command-name>\s*(.*?)\s*</command-name>.*?(?:<command-args>(.*?)</command-args>|$)", re.S)


def as_request(text: str):
    """A typed slash command → "/name args"; injected or system text → None."""
    m = COMMAND_RE.search(text)
    if m:
        return f"{m.group(1)} {(m.group(2) or '').strip()}".strip()
    text = text.strip()
    return text if text and not text.startswith(SKIP_PREFIXES) else None


def parse(transcript: Path):
    requests, files, last_reply, first_ts = [], [], "", None
    for line in transcript.open(encoding="utf-8", errors="ignore"):
        try:
            d = json.loads(line)
        except ValueError:
            continue
        first_ts = first_ts or d.get("timestamp")
        m = d.get("message")
        if not isinstance(m, dict):
            continue
        c = m.get("content")
        if d.get("type") == "user" and not d.get("isMeta"):  # isMeta = command/skill body injected by Claude Code
            texts = [c] if isinstance(c, str) else [
                b.get("text", "") for b in c or [] if isinstance(b, dict) and b.get("type") == "text"]
            requests += [r for r in map(as_request, texts) if r]
        elif d.get("type") == "assistant" and isinstance(c, list):
            for b in c:
                if not isinstance(b, dict):
                    continue
                if b.get("type") == "text" and b.get("text", "").strip():
                    last_reply = b["text"].strip()
                elif b.get("type") == "tool_use" and b.get("name") in WRITE_TOOLS:
                    inp = b.get("input") or {}
                    p = inp.get("file_path") or inp.get("notebook_path")
                    if p and p not in files:
                        files.append(p)
    return requests, files, last_reply, first_ts


def render(session_id: str, date: str, requests, files, last_reply) -> str:
    out = [f"# Session {session_id[:8]} — {date}", "", f"## Requests ({len(requests)})"]
    out += [f"{i}. {r[:500].replace(chr(10), ' ')}" for i, r in enumerate(requests, 1)] or ["(none)"]
    out += ["", "## Files written"] + ([f"- {f}" for f in files] or ["(none)"])
    out += ["", "## Last reply", last_reply[:1500] or "(none)", ""]
    return "\n".join(out)


def cleanup(short_dir: Path, days: int) -> None:
    cutoff = time.time() - days * 86400
    for f in short_dir.glob("*.md"):
        if f.stat().st_mtime < cutoff:
            f.unlink()


def main() -> None:
    data = brse_common.read_hook_input()
    transcript = Path(data.get("transcript_path") or "")
    root, config = brse_common.workspace(data.get("cwd") or ".")
    if root is None or not transcript.is_file():
        return
    requests, files, last_reply, first_ts = parse(transcript)
    if not requests:
        return
    session = data.get("session_id") or transcript.stem
    date = (first_ts or time.strftime("%Y-%m-%d"))[:10]
    short_dir = root / ".brse" / "memory" / "short"
    short_dir.mkdir(parents=True, exist_ok=True)
    (short_dir / f"{date}-{session[:8]}.md").write_text(
        render(session, date, requests, files, last_reply), encoding="utf-8")
    cleanup(short_dir, int(config.get("memory", {}).get("short_retention_days", 30)))


if __name__ == "__main__":
    try:
        main()
    except Exception:  # a hook must never break the user's session
        pass
    sys.exit(0)
