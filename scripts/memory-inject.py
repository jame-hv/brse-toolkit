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
import subprocess
from pathlib import Path

import brse_common

CAP = 6000


def active_entries(md: Path) -> list:
    if not md.is_file():
        return []
    lines = [l.rstrip() for l in md.read_text(encoding="utf-8").splitlines()]
    return [l for l in lines if l.startswith("- ") and "<" not in l and "superseded" not in l]


def load_script(name):
    spec = importlib.util.spec_from_file_location(name.replace("-", "_"), brse_common.ROOT / "scripts" / name)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def sync_sources(root: Path, config: dict) -> list:
    """Compare source files with the knowledge manifest; re-ingest a few changes,
    flag memory entries that cite a changed file."""
    manifest_path = root / ".brse" / "knowledge" / "manifest.json"
    if not manifest_path.is_file():
        return ["Source documents are not in the knowledge base yet — run /brse-toolkit:ingest."]
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    kb = load_script("kb-ingest.py")
    current, changed = set(), []
    for origin, src, f in kb.source_files(root, config):
        if f is None:
            continue
        rel = f.relative_to(root).as_posix()
        current.add(rel)
        st, old = f.stat(), manifest.get(rel)
        if not old or old.get("size") != st.st_size or abs(old.get("mtime", 0) - st.st_mtime) > 1:
            changed.append(("new" if not old else "changed", rel))
    changed += [("deleted", rel) for rel, v in manifest.items() if rel not in current and v.get("sha256")]
    if not changed:
        return []
    out = ["Source documents changed since the last ingest: "
           + ", ".join(f"{rel} ({kind})" for kind, rel in changed[:15]) + (" …" if len(changed) > 15 else "")]
    if len(changed) <= 5:
        py = config.get("runtime", {}).get("python") or sys.executable
        try:
            subprocess.run([py, str(brse_common.ROOT / "scripts" / "kb-ingest.py"), str(root)],
                           capture_output=True, timeout=60, check=True)
            out.append("Re-ingested them, so .brse/knowledge is current.")
        except Exception:
            out.append("Automatic re-ingest failed — run /brse-toolkit:ingest before analysing.")
    else:
        out.append("Run /brse-toolkit:ingest before analysing anything that depends on them.")
    names = {Path(rel).name for _, rel in changed}
    stale = []
    for md in sorted((root / ".brse" / "memory" / "long").glob("*.md")):
        for line in md.read_text(encoding="utf-8").splitlines():
            if line.startswith("- ") and "superseded" not in line and any(n in line for n in names):
                stale.append(f"{md.name}: {line[:160]}")
    if stale:
        out.append("These memory entries cite a changed document and may be stale — re-verify before relying on them:\n"
                   + "\n".join(stale[:10]))
    return out


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
    out += sync_sources(root, config)
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
