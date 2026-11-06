import json
import os
import subprocess
import sys
import pathlib

import pytest

SCRIPTS = pathlib.Path(__file__).resolve().parents[1]


@pytest.fixture
def ws(tmp_path):
    """A minimal brse-toolkit workspace with isolated user config/data dirs."""
    root = tmp_path / "proj"
    (root / ".brse" / "memory" / "long").mkdir(parents=True)
    (root / ".brse" / "memory" / "short").mkdir(parents=True)
    (root / "src-docs").mkdir()
    cfg = {"layout_version": 2, "project": {"name": "demo"}, "paths": {"sources": ["src-docs/"]}}
    (root / ".brse" / "config.json").write_text(json.dumps(cfg), encoding="utf-8")
    return root


def run_script(name, *args, stdin=None, env=None, tmp=None, cwd=None):
    e = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}
    if tmp is not None:
        e.update({"XDG_CONFIG_HOME": str(tmp / "cfg"), "XDG_DATA_HOME": str(tmp / "data"),
                  "LOCALAPPDATA": str(tmp / "data")})
    e.update(env or {})
    return subprocess.run([sys.executable, str(SCRIPTS / name), *map(str, args)], input=stdin,
                          capture_output=True, text=True, encoding="utf-8", env=e, cwd=cwd)
