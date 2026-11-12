"""Helpers shared by the tests (a unique module name, so it never clashes with another conftest)."""
import json
import os
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def make_ws(tmp_path):
    """A minimal brse-toolkit workspace."""
    root = tmp_path / "proj"
    (root / ".brse" / "memory" / "long").mkdir(parents=True)
    (root / ".brse" / "memory" / "short").mkdir(parents=True)
    (root / "src-docs").mkdir()
    cfg = {"layout_version": 2, "project": {"name": "demo"}, "paths": {"sources": ["src-docs/"]}}
    (root / ".brse" / "config.json").write_text(json.dumps(cfg), encoding="utf-8")
    return root


def run_cli(*args, stdin=None, env=None, tmp=None, cwd=None):
    e = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}
    if tmp is not None:
        e.update({"XDG_CONFIG_HOME": str(tmp / "cfg"), "XDG_DATA_HOME": str(tmp / "data"),
                  "LOCALAPPDATA": str(tmp / "data")})
    e.update(env or {})
    return subprocess.run([sys.executable, str(ROOT / "scripts" / "brse.py"), *map(str, args)], input=stdin,
                          capture_output=True, text=True, encoding="utf-8", env=e, cwd=cwd)


ALIAS = {"brse-config": ["config"], "memory-log": ["hook", "stop"], "memory-inject": ["hook", "session-start"],
         "guard-secrets": ["hook", "guard"]}


def run_script(name, *args, **kw):
    """Old tests name a script ("kb-ingest.py"); run the matching brse.py command."""
    stem = name[:-3] if name.endswith(".py") else name
    return run_cli(*ALIAS.get(stem, [stem]), *args, **kw)
