"""Which translated copies were written, and whether translation-check passed on them since.

Stored in <workspace>/.brse/checks.json (outside a workspace: the per-user data dir),
keyed by the copy's absolute path. The Stop hook uses pending() to refuse ending a
session while a translated copy written in it has no passing check.
"""
import json
import time
from pathlib import Path

from brse import config as brse_config


def store(near: Path) -> Path:
    for start in (Path(near).resolve(), Path.cwd()):
        root = brse_config.find_workspace(start)
        if root:
            return root / ".brse" / "checks.json"
    return brse_config.data_dir() / "checks.json"


def _load(f: Path) -> dict:
    try:
        return json.loads(f.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def _save(f: Path, data: dict) -> None:
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")


def applied(out: Path, source: Path) -> None:
    out = Path(out).resolve()
    f = store(out.parent)
    data = _load(f)
    data[str(out)] = {"source": str(Path(source).resolve()), "applied_at": time.time(), "check": None}
    _save(f, data)


def checked(out: Path, passed: bool, problems: int) -> None:
    out = Path(out).resolve()
    f = store(out.parent)
    data = _load(f)
    entry = data.setdefault(str(out), {"source": None, "applied_at": 0})
    entry["check"] = {"pass": passed, "problems": problems, "at": time.time()}
    _save(f, data)


def pending(since: float, near: Path) -> list:
    """Copies written at or after `since` with no passing check after they were written — only copies that
    still exist inside the session's project (its workspace, else the folder itself): the per-user store
    also holds copies written elsewhere, e.g. by the plugin's own tests in /tmp."""
    near = Path(near).resolve()
    scope = brse_config.find_workspace(near) or near
    out = []
    for path, e in _load(store(near)).items():
        if e.get("applied_at", 0) < since or not Path(path).is_file() or not Path(path).is_relative_to(scope):
            continue
        c = e.get("check")
        if not c or not c.get("pass") or c.get("at", 0) < e["applied_at"]:
            out.append(path)
    return out
