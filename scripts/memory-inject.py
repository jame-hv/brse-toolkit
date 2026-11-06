#!/usr/bin/env python3
"""Hook for SessionStart: print what the agent should know before working.

Inside a workspace: plugin version, project, active entry counts in
.brse/memory/long/, the active conventions (they are rules), the most frequent
correction categories of the last 30 days, the requests of the previous
session, and a warning when the workspace layout is older than the plugin's.
Outside one: a migration hint when a 1.x layout (memory/ at the root) is found.
Output is capped so it never floods the context. Never fails the session.
"""
import sys

sys.dont_write_bytecode = True
import importlib.util
import json
from pathlib import Path

import brse_common

CAP = 6000


def active_entries(md: Path) -> list:
    if not md.is_file():
        return []
    lines = [l.rstrip() for l in md.read_text(encoding="utf-8").splitlines()]
    return [l for l in lines if l.startswith("- ") and "<" not in l and "superseded" not in l]


def feedback_top(root: Path) -> dict:
    spec = importlib.util.spec_from_file_location("fs", brse_common.ROOT / "scripts" / "feedback-stats.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.stats(root / ".brse" / "memory" / "long" / "feedback-log.md", days=30)["by_category"]


def previous_session(root: Path, current: str):
    logs = sorted((root / ".brse" / "memory" / "short").glob("*.md"), key=lambda p: p.stat().st_mtime)
    logs = [p for p in logs if not (current and p.stem.endswith(current[:8]))]
    if not logs:
        return None
    text = logs[-1].read_text(encoding="utf-8")
    requests = text.split("## Files written")[0].strip()
    reply = text.split("## Last reply", 1)[1].strip() if "## Last reply" in text else ""
    if len(reply) > 800:
        reply = reply[:800] + " …"
    return logs[-1].name, f"{requests}\n\nOutcome (start of the last reply):\n{reply}" if reply else requests


def main() -> None:
    data = brse_common.read_hook_input()
    cwd = Path(data.get("cwd") or ".").resolve()
    root, config = brse_common.workspace(cwd)
    out = []
    if root is None:
        if (cwd / "memory" / "glossary.md").is_file():
            out.append("brse-toolkit: this folder has a 1.x workspace (memory/ at the root). "
                       "Run /brse-toolkit:init to migrate it to .brse/ (asks before moving anything).")
        print("\n".join(out))
        return
    raw = json.loads((root / ".brse" / "config.json").read_text(encoding="utf-8"))
    name = config.get("project", {}).get("name") or root.name
    out.append(f"brse-toolkit v{brse_common.plugin_version()} — workspace '{name}' at {root}. "
               "Follow the brse-toolkit block in CLAUDE.md.")
    if int(raw.get("layout_version", 1)) < brse_common.LAYOUT_VERSION:
        out.append("Workspace layout is older than this plugin — run /brse-toolkit:init to update it.")
    mem = root / ".brse" / "memory" / "long"
    counts = {f.stem: len(active_entries(f)) for f in sorted(mem.glob("*.md"))}
    out.append("Settled facts in .brse/memory/long (active entries): "
               + ", ".join(f"{k} {v}" for k, v in counts.items()) + ". Read the relevant file before working.")
    conventions = active_entries(mem / "conventions.md")
    if conventions:
        out.append("Project conventions (apply them):\n" + "\n".join(conventions))
    top = feedback_top(root)
    if top:
        out.append("Most frequent corrections in the last 30 days — be careful with: "
                   + ", ".join(f"{k} ({v})" for k, v in list(top.items())[:3]) + ".")
    prev = previous_session(root, data.get("session_id") or "")
    if prev:
        out.append(f"Previous session ({prev[0]}):\n{prev[1]}")
    text = "\n\n".join(out)
    print(text if len(text) <= CAP else text[:CAP] + "\n… (truncated — see .brse/memory/)")


if __name__ == "__main__":
    try:
        main()
    except Exception:  # a hook must never break the user's session
        pass
    sys.exit(0)
