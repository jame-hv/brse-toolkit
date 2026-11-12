"""Hook for PreToolUse: refuse tool calls that must never happen.

1. Opening files that hold API keys: Read / Grep / Glob / Edit / Write on .brse/config.local.json or
   brse-toolkit/secrets.env, and Bash commands that mention them — except the plugin commands that
   read keys without printing them (brse.py config masks them, brse.py set-key asks the user).
2. Writing the gate's records by hand: Edit / Write under .brse/gate/, and Bash commands that mention
   .brse/gate except `brse.py gate` — the review result must come from the reviewer, not the agent.
3. Writing into the client's source documents (config.paths.sources) with Edit / Write — work on a copy.
Exit code 2 = the tool call is refused and the reason is shown to the agent. Anything unexpected →
allow (exit 0), so a broken hook never blocks normal work.
"""
import sys
import json
import re
from pathlib import Path

# a full path names the plugin's own key files anywhere; a bare name only counts inside a brse-toolkit
# workspace or the plugin's config folder (other projects have their own config.local.json / secrets.env)
PROTECTED = re.compile(r"\.brse[/\\\\]config\.local\.json|brse-toolkit[/\\\\]secrets\.env(?![\w.])")
BARE = re.compile(r"(?<![\w.-])(config\.local\.json|secrets\.env)(?![\w.])")
ALLOWED_SCRIPTS = re.compile(r"brse\.py\s+(config|set-key)\b")
GATE = re.compile(r"\.brse[/\\\\]gate\b")
GATE_SCRIPT = re.compile(r"brse\.py\s+gate\b")
WRITE_TOOLS = {"Edit", "Write", "MultiEdit", "NotebookEdit"}


def refuse(msg: str) -> None:
    print(msg, file=sys.stderr)
    sys.exit(2)


def protected(text: str, cwd: str) -> bool:
    if PROTECTED.search(text):
        return True
    if not BARE.search(text):
        return False
    try:
        from brse import config as brse_config
        here = Path(cwd or ".").resolve()
        return bool(brse_config.find_workspace(here)) or here.is_relative_to(brse_config.secrets_file().parent.resolve())
    except Exception:
        return False


def in_sources(target: str, cwd: str) -> bool:
    try:
        from brse import config as brse_config
        root, config = brse_config.workspace(cwd or ".")
        if not root or not target:
            return False
        p = Path(target) if Path(target).is_absolute() else Path(cwd or ".") / target
        p = p.resolve()
        return any(p.is_relative_to((root / s).resolve()) for s in config.get("paths", {}).get("sources", []))
    except Exception:
        return False


def main() -> None:
    try:
        data = json.loads(sys.stdin.read() or "{}")
    except ValueError:
        sys.exit(0)
    tool, inp = data.get("tool_name", ""), data.get("tool_input") or {}
    if tool == "Bash":
        text = inp.get("command", "")
        if protected(text, data.get("cwd") or ".") and not ALLOWED_SCRIPTS.search(text):
            refuse("Blocked: this command touches a file that holds API keys. Use "
                   "scripts/brse.py config (it shows keys only as '(set)'); never print a key.")
        if GATE.search(text) and not GATE_SCRIPT.search(text):
            refuse("Blocked: .brse/gate holds the final-check records; only `brse.py gate` may touch them.")
        sys.exit(0)
    target = " ".join(str(inp.get(k, "")) for k in ("file_path", "path", "pattern", "notebook_path"))
    if protected(target, data.get("cwd") or "."):
        refuse(f"Blocked: {tool} on a file that holds API keys. Use scripts/brse.py config, which never "
               "shows the key.")
    if tool in WRITE_TOOLS:
        if GATE.search(target):
            refuse("Blocked: .brse/gate holds the final-check records; only `brse.py gate` may write them.")
        f = inp.get("file_path") or inp.get("notebook_path") or ""
        if in_sources(f, data.get("cwd") or "."):
            refuse(f"Blocked: {f} is one of the client's source documents (config.paths.sources). "
                   "Write to a copy in config.paths.outputs instead.")
    sys.exit(0)
