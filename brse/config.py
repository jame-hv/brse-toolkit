"""Merged config (plugin defaults < user < workspace < workspace-local), workspace lookup, secrets, data dir."""
import json
import os
import sys
from pathlib import Path


class ConfigError(ValueError):
    """A config file is broken or holds a secret."""


PLUGIN_ROOT = Path(__file__).resolve().parents[1]
LAYOUT_VERSION = 2
DEFAULTS = PLUGIN_ROOT / "config" / "defaults.json"
SECRET_HINTS = ("api_key", "apikey", "token", "secret", "password")


def load(path: Path) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise ConfigError(f"{path}: JSON không hợp lệ ở dòng {e.lineno}, cột {e.colno}: {e.msg}")
    if not isinstance(data, dict):
        raise ConfigError(f"{path}: phải là một object JSON {{...}}")
    return data


def merge(base: dict, over: dict, prefix: str, warnings: list) -> dict:
    out = dict(base)
    for k, v in over.items():
        key = f"{prefix}{k}"
        if k not in base:
            warnings.append(f"khóa lạ '{key}' (gõ sai tên?)")
        if isinstance(v, dict) and isinstance(base.get(k), dict):
            if not base[k]:  # an empty default ({}) is a free-form map: any key is valid
                out[k] = {**base[k], **v}
            else:
                out[k] = merge(base[k], v, key + ".", warnings)
        else:
            out[k] = v
    return out


def find_secrets(d: dict, prefix: str = "") -> list:
    hits = []
    for k, v in d.items():
        key = f"{prefix}{k}"
        if isinstance(v, dict):
            hits += find_secrets(v, key + ".")
        elif any(h in k.lower() for h in SECRET_HINTS) and not k.endswith("_env") and v:
            hits.append(key)
    return hits


def find_workspace(start: Path):
    start = Path(start)
    for d in [start, *start.parents]:
        if (d / ".brse" / "config.json").is_file():
            return d
    return None


def resolve(start: Path) -> dict:
    """Merged config for `start`. Raises ValueError on a broken or secret-bearing file."""
    xdg = os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config"
    user = Path(xdg) / "brse-toolkit" / "config.json"
    root = find_workspace(start)
    layers = [DEFAULTS, user] + ([root / ".brse" / "config.json", root / ".brse" / "config.local.json"] if root else [])
    config, loaded, warnings = {}, [], []
    for i, path in enumerate(layers):
        if not path.is_file():
            continue
        data = load(path)
        secrets = find_secrets({k: v for k, v in data.items() if not (path.name == "config.local.json" and k == "secrets")})
        if path.name != "config.local.json" and data.get("secrets"):
            secrets.append("secrets")
        if secrets:
            raise ConfigError(f"{path}: không ghi secret vào config ({', '.join(secrets)}) "
                             "— đặt key vào biến môi trường, config chỉ ghi tên biến (*_env)")
        config = data if i == 0 else merge(config, data, "", warnings)
        loaded.append(str(path))
    out_dir = str(config.get("paths", {}).get("outputs") or "")
    if any(part.startswith(".") and part not in (".", "..") for part in Path(out_dir).parts):
        # results the user must open never go into a hidden folder (older init versions wrote .brse/work/)
        default = json.loads(DEFAULTS.read_text(encoding="utf-8"))["paths"]["outputs"]
        config["paths"]["outputs"] = default
        warnings.append(f"paths.outputs '{out_dir}' is a hidden folder — using '{default}' instead; "
                        "fix it in .brse/config.json")
    return {"config": config, "loaded": loaded,
            "workspace_root": str(root) if root else None, "warnings": warnings}


def masked(out: dict) -> dict:
    """Never print a key: secrets are shown as set / not set only."""
    shown = json.loads(json.dumps(out))
    shown["config"]["secrets"] = {k: "(set)" if v else "(empty)" for k, v in out["config"].get("secrets", {}).items()}
    return shown


def workspace(start):
    """(workspace root or None, merged config). Raises ValueError on a broken config."""
    out = resolve(Path(start).resolve())
    root = out["workspace_root"]
    return (Path(root) if root else None), out["config"]


def plugin_version() -> str:
    return json.loads((PLUGIN_ROOT / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))["version"]


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
    """API key lookup: environment variable → plugin userConfig (Claude Code exposes it
    as CLAUDE_PLUGIN_OPTION_<NAME>, stored in the OS keychain) → the workspace's
    .brse/config.local.json "secrets" (git-ignored, never printed by brse.py config)
    → ~/.config/brse-toolkit/secrets.env (written by brse.py set-key)."""
    if not env_name:
        return None
    for name in (env_name, f"CLAUDE_PLUGIN_OPTION_{env_name.upper()}"):
        if os.environ.get(name):
            return os.environ[name]
    try:
        local = resolve(Path.cwd())["config"].get("secrets", {}).get(env_name)
        if local:
            return local
    except ValueError:
        pass
    f = secrets_file()
    if f.is_file():
        for line in f.read_text(encoding="utf-8").splitlines():
            k, _, v = line.partition("=")
            if k.strip() == env_name and v.strip():
                return v.strip()
    return None


def main() -> None:
    start = Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
    try:
        out = resolve(start)
    except ValueError as e:
        print(json.dumps({"error": str(e)}, ensure_ascii=False))
        sys.exit(1)
    print(json.dumps(masked(out), ensure_ascii=False, indent=2))

