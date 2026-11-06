#!/usr/bin/env python3
"""Ask a second, independent agent (a different model) to review or back-translate.

Usage: ask-agent.py <prompt_file> [project_dir] [--timeout SECONDS]
Tries config.review.second_agent in order:
  codex   → `codex exec --skip-git-repo-check -s read-only -o <file>` (prompt on stdin)
  gemini  → `gemini -p ...` (prompt on stdin)
  openai  → Chat Completions API; needs providers.openai.model and the key in the
            env var named by providers.openai.api_key_env
  claude-subagent → not callable from a script: stop and report provider "none"
A tool's path comes from config.tools.paths.<id>, else PATH.
Prints {"provider", "output", "tried": [...]}; provider "none" means the caller
must fall back to a Claude subagent and say the check was not model-independent.
Read-only: the second agent gets no write access.
"""
import sys

sys.dont_write_bytecode = True
import json
import os
import shutil
import subprocess
import tempfile
import urllib.request
from pathlib import Path

import brse_common

OPENAI_URL = os.environ.get("BRSE_OPENAI_URL", "https://api.openai.com/v1/chat/completions")


def tool_path(name: str, config: dict):
    override = config.get("tools", {}).get("paths", {}).get(name)
    return override if override and Path(override).is_file() else shutil.which(name)


def run_codex(exe, prompt, timeout):
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "last.txt"
        r = subprocess.run([exe, "exec", "--skip-git-repo-check", "-s", "read-only", "-o", str(out)],
                           input=prompt, capture_output=True, text=True, encoding="utf-8", timeout=timeout)
        if r.returncode != 0:
            raise RuntimeError((r.stderr or r.stdout).strip()[-500:])
        return out.read_text(encoding="utf-8").strip() if out.is_file() else r.stdout.strip()


def run_gemini(exe, prompt, timeout):
    r = subprocess.run([exe, "-p", "Respond to the request given on stdin."], input=prompt,
                       capture_output=True, text=True, encoding="utf-8", timeout=timeout)
    if r.returncode != 0:
        raise RuntimeError((r.stderr or r.stdout).strip()[-500:])
    return r.stdout.strip()


def run_openai(prompt, config, timeout):
    p = config.get("providers", {}).get("openai", {})
    key, model = brse_common.secret(p.get("api_key_env", "OPENAI_API_KEY")), p.get("model")
    if not key or not model:
        raise LookupError(f"needs env var {p.get('api_key_env')} and providers.openai.model")
    body = json.dumps({"model": model, "messages": [{"role": "user", "content": prompt}]}).encode()
    req = urllib.request.Request(OPENAI_URL, data=body, headers={
        "Authorization": f"Bearer {key}", "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read())["choices"][0]["message"]["content"].strip()


def ask(prompt: str, config: dict, timeout: int) -> dict:
    tried = []
    for name in config.get("review", {}).get("second_agent", []):
        if name == "claude-subagent":
            tried.append({"provider": name, "skipped": "not callable from a script — use a Claude subagent"})
            break
        try:
            if name == "openai":
                return {"provider": name, "output": run_openai(prompt, config, timeout), "tried": tried}
            exe = tool_path(name, config)
            if not exe:
                tried.append({"provider": name, "skipped": "not installed"})
                continue
            runner = {"codex": run_codex, "gemini": run_gemini}.get(name)
            if runner is None:
                tried.append({"provider": name, "skipped": "unknown provider"})
                continue
            return {"provider": name, "output": runner(exe, prompt, timeout), "tried": tried}
        except LookupError as e:
            tried.append({"provider": name, "skipped": str(e)})
        except Exception as e:  # timeout, auth failure, network: try the next one
            tried.append({"provider": name, "error": f"{type(e).__name__}: {str(e)[:300]}"})
    return {"provider": "none", "output": None, "tried": tried}


def main() -> None:
    args = sys.argv[1:]
    timeout = 300
    if "--timeout" in args:
        i = args.index("--timeout")
        timeout = int(args[i + 1])
        del args[i:i + 2]
    if not args:
        print("usage: ask-agent.py <prompt_file> [project_dir] [--timeout SECONDS]", file=sys.stderr)
        sys.exit(2)
    prompt = Path(args[0]).read_text(encoding="utf-8")
    _, config = brse_common.workspace(args[1] if len(args) > 1 else ".")
    print(json.dumps(ask(prompt, config, timeout), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
