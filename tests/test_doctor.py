import json
import os
import subprocess
import sys
import pathlib

SCRIPT = pathlib.Path(__file__).resolve().parents[1] / "scripts" / "brse.py"


def fake_exe(folder, name):
    folder.mkdir(parents=True, exist_ok=True)
    p = folder / (name + (".exe" if os.name == "nt" else ""))
    p.write_text("#!/bin/sh\n", encoding="utf-8")
    p.chmod(0o755)
    return p


def run(tmp_path, path_dirs, project=None):
    env = {**os.environ, "PATH": os.pathsep.join(str(d) for d in path_dirs),
           "XDG_CONFIG_HOME": str(tmp_path / "cfg"), "XDG_DATA_HOME": str(tmp_path / "data"),
           "LOCALAPPDATA": str(tmp_path / "data")}
    r = subprocess.run([sys.executable, str(SCRIPT), 'doctor', str(project or tmp_path)],
                       capture_output=True, text=True, encoding="utf-8", env=env)
    assert r.returncode == 0, r.stderr
    out = json.loads(r.stdout)
    return out, {t["id"]: t for t in out["tools"]}


def test_tool_on_path_is_found_and_has_no_install_hint(tmp_path):
    bin_dir = tmp_path / "bin"
    exe = fake_exe(bin_dir, "rg")
    _, tools = run(tmp_path, [bin_dir])
    assert tools["ripgrep"]["found"] is True
    assert pathlib.Path(tools["ripgrep"]["path"]) == exe
    assert tools["ripgrep"]["install"] is None


def test_missing_tool_gets_install_command_for_this_os(tmp_path):
    out, tools = run(tmp_path, [tmp_path / "empty"])
    assert tools["ripgrep"]["found"] is False
    assert tools["ripgrep"]["install"]  # non-empty command for out["os"]
    assert out["os"] in ("linux", "darwin", "windows")


def test_tool_without_standard_installer_points_to_manual_page(tmp_path):
    _, tools = run(tmp_path, [tmp_path / "empty"])
    assert tools["gridcraft-cli"]["install"] is None
    assert tools["gridcraft-cli"]["manual"].startswith("https://")


def test_config_path_override_wins_over_path(tmp_path):
    exe = fake_exe(tmp_path / "custom", "gridcraft-cli-anyname")
    project = tmp_path / "proj"
    (project / ".brse").mkdir(parents=True)
    (project / ".brse" / "config.json").write_text(
        json.dumps({"tools": {"paths": {"gridcraft-cli": str(exe)}}}), encoding="utf-8")
    _, tools = run(tmp_path, [tmp_path / "empty"], project)
    assert tools["gridcraft-cli"]["found"] is True


def test_broken_override_path_is_reported_missing(tmp_path):
    project = tmp_path / "proj"
    (project / ".brse").mkdir(parents=True)
    (project / ".brse" / "config.json").write_text(
        json.dumps({"tools": {"paths": {"ripgrep": str(tmp_path / "nope")}}}), encoding="utf-8")
    bin_dir = tmp_path / "bin"
    fake_exe(bin_dir, "rg")
    _, tools = run(tmp_path, [bin_dir], project)
    assert tools["ripgrep"]["found"] is False  # an explicit override is never silently ignored


def test_reports_python_packages_and_venv_location(tmp_path):
    out, _ = run(tmp_path, [tmp_path / "empty"])
    names = {p["package"] for p in out["python_packages"]}
    assert {"openpyxl", "python-docx", "python-pptx"} <= names
    assert "pytest" not in names
    assert out["venv"]["path"].startswith(str(tmp_path / "data"))
    assert out["venv"]["exists"] is False
