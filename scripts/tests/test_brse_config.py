import json
import os
import subprocess
import sys
import pathlib

SCRIPT = pathlib.Path(__file__).resolve().parents[1] / "brse-config.py"


def run(project, home):
    env = {**os.environ, "XDG_CONFIG_HOME": str(home)}
    r = subprocess.run([sys.executable, str(SCRIPT), str(project)],
                       capture_output=True, text=True, encoding="utf-8", env=env)
    return json.loads(r.stdout), r.returncode


def write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(data if isinstance(data, str) else json.dumps(data), encoding="utf-8")


def test_defaults_only(tmp_path):
    out, code = run(tmp_path, tmp_path / "home")
    assert code == 0
    assert out["workspace_root"] is None
    assert out["config"]["paths"]["sources"] == ["documents/"]


def test_workspace_overrides_user_overrides_defaults(tmp_path):
    home, proj = tmp_path / "home", tmp_path / "proj"
    write(home / "brse-toolkit" / "config.json", {"project": {"reply_language": "en"},
                                                   "paths": {"outputs": "user-out/"}})
    write(proj / ".brse" / "config.json", {"paths": {"outputs": "ws-out/", "sources": ["input/"]}})
    out, code = run(proj / "sub" / "deeper", home)  # found by walking up
    assert code == 0
    c = out["config"]
    assert c["project"]["reply_language"] == "en"       # from user
    assert c["paths"]["outputs"] == "ws-out/"           # workspace wins
    assert c["paths"]["sources"] == ["input/"]          # list replaced, not appended
    assert c["paths"]["templates"] == ["templates/"]    # default kept
    assert out["workspace_root"] == str(proj)
    assert len(out["loaded"]) == 3


def test_unknown_key_warns(tmp_path):
    proj = tmp_path / "proj"
    write(proj / ".brse" / "config.json", {"paths": {"sourcse": ["x/"]}})
    out, code = run(proj, tmp_path / "home")
    assert code == 0
    assert any("paths.sourcse" in w for w in out["warnings"])


def test_invalid_json_reports_line(tmp_path):
    proj = tmp_path / "proj"
    write(proj / ".brse" / "config.json", '{\n  "paths": {,}\n}')
    out, code = run(proj, tmp_path / "home")
    assert code == 1
    assert "dòng 2" in out["error"]


def test_secret_value_rejected(tmp_path):
    proj = tmp_path / "proj"
    write(proj / ".brse" / "config.json", {"providers": {"openai": {"api_key": "sk-abc"}}})
    out, code = run(proj, tmp_path / "home")
    assert code == 1
    assert "providers.openai.api_key" in out["error"]
    assert "sk-abc" not in out["error"]


def test_env_var_name_is_allowed(tmp_path):
    proj = tmp_path / "proj"
    write(proj / ".brse" / "config.json", {"providers": {"openai": {"api_key_env": "MY_KEY"}}})
    out, code = run(proj, tmp_path / "home")
    assert code == 0
    assert out["config"]["providers"]["openai"]["api_key_env"] == "MY_KEY"
