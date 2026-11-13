import json
import os
import subprocess
import sys
import pathlib

SCRIPT = pathlib.Path(__file__).resolve().parents[1] / "scripts" / "brse.py"


def run(project, home):
    env = {**os.environ, "XDG_CONFIG_HOME": str(home)}
    r = subprocess.run([sys.executable, str(SCRIPT), 'config', str(project)],
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


def test_free_form_map_children_are_not_unknown_keys(tmp_path):
    """tools.paths defaults to {} — any tool id under it is legitimate, not a typo."""
    home = tmp_path / "home"
    write(home / "brse-toolkit" / "config.json", {"tools": {"paths": {"gridcraft-cli": "/x/gridcraft-cli"}}})
    out, code = run(tmp_path, home)
    assert code == 0
    assert out["warnings"] == []
    assert out["config"]["tools"]["paths"]["gridcraft-cli"] == "/x/gridcraft-cli"


def test_local_config_overrides_shared_workspace_config(tmp_path):
    proj = tmp_path / "proj"
    write(proj / ".brse" / "config.json", {"project": {"reply_language": "vi"}, "paths": {"outputs": "out/"}})
    write(proj / ".brse" / "config.local.json", {"project": {"reply_language": "en"}})
    out, code = run(proj, tmp_path / "home")
    assert code == 0
    assert out["config"]["project"]["reply_language"] == "en"
    assert out["config"]["paths"]["outputs"] == "out/"
    assert out["loaded"][-1].endswith("config.local.json")


def test_local_config_may_hold_keys_but_they_are_never_printed(tmp_path):
    proj = tmp_path / "proj"
    write(proj / ".brse" / "config.json", {})
    write(proj / ".brse" / "config.local.json", {"secrets": {"OPENAI_API_KEY": "sk-very-secret"}})
    r = subprocess.run([sys.executable, str(SCRIPT), 'config', str(proj)], capture_output=True, text=True, encoding="utf-8",
                       env={**os.environ, "XDG_CONFIG_HOME": str(tmp_path / "home")})
    assert r.returncode == 0 and "sk-very-secret" not in r.stdout
    assert json.loads(r.stdout)["config"]["secrets"] == {"OPENAI_API_KEY": "(set)"}


def test_shared_config_still_refuses_keys(tmp_path):
    proj = tmp_path / "proj"
    write(proj / ".brse" / "config.json", {"secrets": {"OPENAI_API_KEY": "sk-x"}})
    out, code = run(proj, tmp_path / "home")
    assert code == 1 and "sk-x" not in out["error"]


def test_outputs_inside_the_hidden_folder_fall_back_to_the_visible_default(tmp_path):
    import json as j
    from brse import config as c
    (tmp_path / ".brse").mkdir()
    (tmp_path / ".brse" / "config.json").write_text(j.dumps({"paths": {"outputs": ".brse/work/"}}))
    out = c.resolve(tmp_path)
    assert out["config"]["paths"]["outputs"] == "output/" and "hidden" in out["warnings"][-1]
