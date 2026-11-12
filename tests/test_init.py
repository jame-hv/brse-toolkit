"""init asks nothing: it infers from the folder and the user corrects with flags."""
import json

from brse_testkit import run_cli


def test_init_infers_everything_from_the_folder(tmp_path):
    proj = tmp_path / "sample-project"
    (proj / "client-docs").mkdir(parents=True)
    (proj / "client-docs" / "画面仕様書.xlsx").write_bytes(b"x")
    (proj / "テンプレート").mkdir()
    (proj / "テンプレート" / "見積.xlsx").write_bytes(b"x")
    (proj / "output").mkdir()
    (proj / "output" / "a.xlsx").write_bytes(b"x")
    (proj / "CLAUDE.md").write_text("my own notes\n", encoding="utf-8")
    r = run_cli("init", proj, tmp=tmp_path, cwd=proj)
    out = json.loads(r.stdout)
    assert r.returncode == 0, r.stdout
    inf = {k: v["value"] for k, v in out["inferred"].items()}
    assert inf == {"name": "sample-project", "sources": ["client-docs/"], "templates": ["テンプレート/"],
                   "client_language": "ja", "reply_language": "vi"}
    cfg = json.loads((proj / ".brse" / "config.json").read_text(encoding="utf-8"))
    assert cfg["paths"]["sources"] == ["client-docs/"] and "secrets" not in cfg
    md = (proj / "CLAUDE.md").read_text(encoding="utf-8")
    assert md.startswith("my own notes") and "not set yet" not in md and len(md.splitlines()) < 40
    for f in ("parties.md", "glossary.md", "conventions.md", "decisions-log.md", "feedback-log.md",
              "deliverables-log.md"):
        assert (proj / ".brse" / "memory" / "long" / f).is_file()
    assert "config.local.json" in (proj / ".brse" / ".gitignore").read_text()
    c = json.loads(run_cli("config", cwd=proj, tmp=tmp_path).stdout)
    assert c["workspace_root"] == str(proj) and c["warnings"] == []

    # a second run without --force leaves it alone; with flags it corrects only what was given
    assert run_cli("init", proj, tmp=tmp_path, cwd=proj).returncode == 2
    out = json.loads(run_cli("init", proj, "--force", "--name", "Sample", "--sources", "docs",
                             tmp=tmp_path, cwd=proj).stdout)
    assert out["inferred"]["name"] == {"value": "Sample", "from": "given"}
    assert out["inferred"]["sources"]["value"] == ["docs/"]
    assert (proj / "CLAUDE.md").read_text(encoding="utf-8").count("brse-toolkit:start") == 1
