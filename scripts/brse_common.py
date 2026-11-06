"""Shared helpers for brse-toolkit scripts: plugin root, merged config, workspace lookup."""
import importlib.util
import json
import os
import sys
from pathlib import Path

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
LAYOUT_VERSION = 2


def _config_module():
    spec = importlib.util.spec_from_file_location("brse_config", ROOT / "scripts" / "brse-config.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def resolve(start) -> dict:
    """Merged config for `start` (see brse-config.py). Raises ValueError on a broken config."""
    return _config_module().resolve(Path(start).resolve())


def workspace(start):
    """(workspace root or None, merged config). Raises ValueError on a broken config."""
    out = resolve(start)
    root = out["workspace_root"]
    return (Path(root) if root else None), out["config"]


def plugin_version() -> str:
    return json.loads((ROOT / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))["version"]


def data_dir() -> Path:
    """Per-user data folder (venv, extracted CLIs, library)."""
    if sys.platform == "win32" and os.environ.get("LOCALAPPDATA"):
        return Path(os.environ["LOCALAPPDATA"]) / "brse-toolkit"
    return Path(os.environ.get("XDG_DATA_HOME") or Path.home() / ".local" / "share") / "brse-toolkit"


def read_hook_input() -> dict:
    try:
        return json.loads(sys.stdin.read() or "{}")
    except ValueError:
        return {}


def secrets_file() -> Path:
    return Path(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config") / "brse-toolkit" / "secrets.env"


def secret(env_name: str):
    """API key lookup, never from project files: environment variable → plugin
    userConfig (Claude Code exposes it as CLAUDE_PLUGIN_OPTION_<NAME>, stored in
    the OS keychain) → ~/.config/brse-toolkit/secrets.env (written by set-key.py)."""
    if not env_name:
        return None
    for name in (env_name, f"CLAUDE_PLUGIN_OPTION_{env_name.upper()}"):
        if os.environ.get(name):
            return os.environ[name]
    f = secrets_file()
    if f.is_file():
        for line in f.read_text(encoding="utf-8").splitlines():
            k, _, v = line.partition("=")
            if k.strip() == env_name and v.strip():
                return v.strip()
    return None
