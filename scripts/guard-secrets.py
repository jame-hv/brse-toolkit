#!/usr/bin/env python3
"""Hook for PreToolUse: stop the agent from opening files that hold API keys.

Blocks Read / Grep / Glob / Edit / Write on .brse/config.local.json or
brse-toolkit/secrets.env, and Bash commands that mention them — except the
plugin scripts that read keys without printing them (brse-config.py masks
them, set-key.py asks the user directly). Exit code 2 = the tool call is
refused and the reason is shown to the agent. Anything unexpected → allow
(exit 0), so a broken hook never blocks normal work.
"""
import sys

sys.dont_write_bytecode = True
import json
import re

PROTECTED = re.compile(r"config\.local\.json|brse-toolkit[/\\\\]secrets\.env|(?<![\w-])secrets\.env")
ALLOWED_SCRIPTS = re.compile(r"(brse-config|set-key)\.py")


def main() -> None:
    try:
        data = json.loads(sys.stdin.read() or "{}")
    except ValueError:
        sys.exit(0)
    tool, inp = data.get("tool_name", ""), data.get("tool_input") or {}
    if tool == "Bash":
        text = inp.get("command", "")
        if PROTECTED.search(text) and not ALLOWED_SCRIPTS.search(text):
            print("Blocked: this command touches a file that holds API keys. Use "
                  "scripts/brse-config.py (it shows keys only as '(set)'); never print a key.", file=sys.stderr)
            sys.exit(2)
    else:
        target = " ".join(str(inp.get(k, "")) for k in ("file_path", "path", "pattern", "notebook_path"))
        if PROTECTED.search(target):
            print(f"Blocked: {tool} on a file that holds API keys. Use scripts/brse-config.py, which never "
                  "shows the key.", file=sys.stderr)
            sys.exit(2)
    sys.exit(0)


if __name__ == "__main__":
    main()
