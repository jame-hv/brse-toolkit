"""Ask a second, independent agent (a different model) to review or back-translate.

Usage: brse.py ask-agent <prompt_file> [project_dir] [--timeout SECONDS]
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
import json
import shutil
import subprocess
import tempfile
from pathlib import Path

from brse import config as brse_config
from brse.cli import take
from brse.providers import openai_chat

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
    return openai_chat([{"role": "user", "content": prompt}], config, timeout)


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
    timeout = int(take(args, "--timeout", timeout))
    if not args:
        print("usage: brse.py ask-agent <prompt_file> [project_dir] [--timeout SECONDS]", file=sys.stderr)
        sys.exit(2)
    prompt = Path(args[0]).read_text(encoding="utf-8")
    _, config = brse_config.workspace(args[1] if len(args) > 1 else ".")
    print(json.dumps(ask(prompt, config, timeout), ensure_ascii=False, indent=2))

