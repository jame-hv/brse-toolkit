#!/usr/bin/env python3
"""Report which tools brse-toolkit can use on this machine, and how to install the rest.

Usage: doctor.py [project_dir]
Prints {"os", "python", "venv", "tools": [...], "python_packages": [...], "config_error"}.
A tool is found via `tools.paths.<id>` in the merged config, then PATH, then the
manifest's per-OS extra_paths. Read-only: never installs anything.
"""
import importlib.util
import json
import os
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "config" / "dependencies.json"
OS_NAME = {"win32": "windows", "darwin": "darwin"}.get(sys.platform, "linux")


def load_config(start: Path):
    spec = importlib.util.spec_from_file_location("brse_config", ROOT / "scripts" / "brse-config.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    try:
        return mod.resolve(start)["config"], None
    except ValueError as e:
        return {}, str(e)


def venv_dir() -> Path:
    base = os.environ.get("LOCALAPPDATA") if OS_NAME == "windows" else None
    base = Path(base) if base else Path(os.environ.get("XDG_DATA_HOME") or Path.home() / ".local" / "share")
    return base / "brse-toolkit" / "venv"


def venv_python(venv: Path) -> Path:
    return venv / ("Scripts/python.exe" if OS_NAME == "windows" else "bin/python")


def find_tool(tool: dict, overrides: dict):
    override = overrides.get(tool["id"])
    if override:
        return override if Path(override).is_file() else None
    for name in tool["check"]:
        hit = shutil.which(name)
        if hit:
            return hit
    for p in tool.get("extra_paths", {}).get(OS_NAME, []):
        if Path(p).is_file():
            return p
    return None


def install_command(tool: dict):
    inst = tool.get("install")
    if not inst:
        return None
    return inst.get(OS_NAME) or inst.get("all")


def python_packages(manifest: dict) -> list:
    req = (ROOT / manifest["python_requirements"]).read_text(encoding="utf-8").splitlines()
    out = []
    for line in req:
        name = line.split(">=")[0].split("==")[0].strip()
        if not name or name.startswith("#"):
            continue
        module = manifest["python_import_names"].get(name, name)
        out.append({"package": name, "found": importlib.util.find_spec(module) is not None})
    return out


def main() -> None:
    start = Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    config, config_error = load_config(start)
    overrides = config.get("tools", {}).get("paths", {})
    tools = []
    for t in manifest["tools"]:
        path = find_tool(t, overrides)
        tools.append({
            "id": t["id"], "level": t["level"], "found": path is not None, "path": path,
            "required_for": t["required_for"], "needs": t.get("needs", []),
            "install": None if path else install_command(t),
            "manual": None if path else t.get("manual"),
        })
    venv = venv_dir()
    print(json.dumps({
        "os": OS_NAME,
        "python": sys.executable,
        "venv": {"path": str(venv), "exists": venv_python(venv).is_file(),
                 "python": str(venv_python(venv))},
        "tools": tools,
        "python_packages": python_packages(manifest),
        "config_error": config_error,
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
