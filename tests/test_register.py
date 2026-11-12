import json

from brse_testkit import run_script


def reg(ws, tmp_path, *args):
    r = run_script("register.py", "--root", ws, *args, tmp=tmp_path)
    return r.returncode, json.loads(r.stdout)


def test_ids_links_and_supersede(ws, tmp_path):
    assert reg(ws, tmp_path, "add", "R", "--title", "注文検索")[1]["added"]["id"] == "R-001"
    reg(ws, tmp_path, "add", "R", "--title", "CSV出力")
    rc, out = reg(ws, tmp_path, "add", "D", "--title", "Build new", "--links", "R-001,R-002")
    assert rc == 0 and out["added"]["id"] == "D-001"
    rc, out = reg(ws, tmp_path, "add", "D", "--title", "Reuse old module", "--supersedes", "D-001",
                  "--links", "R-001", "--source", "M-2026-11-09")
    assert out["added"]["supersedes"] == "D-001" and "D-001" in out["added"]["links"]
    _, got = reg(ws, tmp_path, "get", "D-001")
    assert got["item"]["status"] == "superseded" and got["item"]["superseded_by"] == "D-002"
    assert "D-002" in got["linked_from"]


def test_impact_walks_both_directions(ws, tmp_path):
    reg(ws, tmp_path, "add", "R", "--title", "r1")
    reg(ws, tmp_path, "add", "Q", "--title", "q1", "--links", "R-001")
    reg(ws, tmp_path, "add", "D", "--title", "d1", "--links", "R-001")
    reg(ws, tmp_path, "bump", "estimate", "--reason", "first", "--decisions", "D-001")
    _, out = reg(ws, tmp_path, "impact", "D-001")
    assert {x["id"] for x in out["impacted"]["R"]} == {"R-001"}
    assert {x["id"] for x in out["impacted"]["Q"]} == {"Q-001"}
    assert out["versions_based_on_these"][0]["version"] == "1.0"


def test_versions_increment(ws, tmp_path):
    reg(ws, tmp_path, "bump", "estimate", "--reason", "a")
    _, out = reg(ws, tmp_path, "bump", "estimate", "--reason", "b")
    assert out["bumped"]["version"] == "1.1" and out["bumped"]["previous"] == "1.0"


def test_qa_lifecycle_and_check(ws, tmp_path):
    reg(ws, tmp_path, "add", "Q", "--title", "license?", "--due", "2000-01-01", "--owner", "client")
    reg(ws, tmp_path, "update", "Q-001", "--status", "sent", "--set", "sent=2000-01-01")
    _, out = reg(ws, tmp_path, "check")
    probs = {p["problem"].split()[0] for p in out["problems"]}
    assert not out["ok"] and {"overdue", "sent"} <= probs
    reg(ws, tmp_path, "update", "Q-001", "--status", "answered", "--set", "answer=yes")
    _, out = reg(ws, tmp_path, "check")
    assert any("no decision" in p["problem"] for p in out["problems"])
    reg(ws, tmp_path, "add", "D", "--title", "license ok", "--links", "Q-001")
    _, st = reg(ws, tmp_path, "status")
    assert st["counts"]["qa"] == {"answered": 1}


def test_errors(ws, tmp_path):
    rc, out = reg(ws, tmp_path, "add", "Q", "--title", "x", "--status", "bogus")
    assert rc == 2 and "invalid" in out["error"]
    rc, out = reg(ws, tmp_path, "get", "Q-099")
    assert rc == 2
    rc, out = run_script("register.py", "--root", tmp_path, "status", tmp=tmp_path).returncode, None
    assert rc == 2


def test_meeting_ids_and_render(ws, tmp_path):
    a = reg(ws, tmp_path, "add", "M", "--title", "kickoff")[1]["added"]["id"]
    b = reg(ws, tmp_path, "add", "M", "--title", "follow-up")[1]["added"]["id"]
    assert a.startswith("M-") and b == a + "-2"
    _, out = reg(ws, tmp_path, "render")
    text = (ws / ".brse" / "registers" / "REGISTER.md").read_text(encoding="utf-8")
    assert "kickoff" in text and "## Versions" in text
