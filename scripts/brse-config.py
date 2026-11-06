#!/usr/bin/env python3
"""Merge brse-toolkit config: plugin defaults < user < workspace < workspace-local.

Usage: brse-config.py [project_dir]
  plugin defaults: <plugin>/config/defaults.json
  user:            $XDG_CONFIG_HOME/brse-toolkit/config.json (default ~/.config/...)
  workspace:       nearest .brse/config.json at or above project_dir (default cwd) — shared, committed
  workspace-local: .brse/config.local.json next to it — personal, git-ignored
Prints {"config", "loaded", "workspace_root", "warnings"}; exit 1 on {"error"}.
Objects merge key by key; any other value (lists included) replaces the lower layer.
"""
import json
import os
import sys
from pathlib import Path

DEFAULTS = Path(__file__).resolve().parents[1] / "config" / "defaults.json"
SECRET_HINTS = ("api_key", "apikey", "token", "secret", "password")


def load(path: Path) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise ValueError(f"{path}: JSON không hợp lệ ở dòng {e.lineno}, cột {e.colno}: {e.msg}")
    if not isinstance(data, dict):
        raise ValueError(f"{path}: phải là một object JSON {{...}}")
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
        secrets = find_secrets(data)
        if secrets:
            raise ValueError(f"{path}: không ghi secret vào config ({', '.join(secrets)}) "
                             "— đặt key vào biến môi trường, config chỉ ghi tên biến (*_env)")
        config = data if i == 0 else merge(config, data, "", warnings)
        loaded.append(str(path))
    return {"config": config, "loaded": loaded,
            "workspace_root": str(root) if root else None, "warnings": warnings}


def main() -> None:
    start = Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
    try:
        out = resolve(start)
    except ValueError as e:
        print(json.dumps({"error": str(e)}, ensure_ascii=False))
        sys.exit(1)
    print(json.dumps(out, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
