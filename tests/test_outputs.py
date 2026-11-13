"""The output folder keeps deliverables and their versions; clutter is listed and moved out, never deleted."""
import json

from brse_testkit import run_cli


def test_versions_are_grouped_and_clutter_is_moved_not_deleted(ws, tmp_path):
    out = ws / "output"
    out.mkdir(exist_ok=True)
    for n in ["見積書_v1.0.xlsx", "見積書_v1.1.xlsx", "見積書_v1.0_前提条件修正版.xlsx", "QA_bak_書換前.xlsx",
              "overview.drawio", "overview.drawio.sources.md", "overview.drawio.claims.json", "overview.png",
              "overview.model.json", "overview-preview.png", "build.mjs", "old-system-flow.drawio"]:
        (out / n).write_text("x")
    r = json.loads(run_cli("outputs", cwd=ws, tmp=tmp_path).stdout)
    clutter = {c["file"] for c in r["clutter"]}
    assert clutter == {"見積書_v1.0_前提条件修正版.xlsx", "QA_bak_書換前.xlsx", "overview.model.json",
                       "overview-preview.png", "build.mjs"}
    est = next(d for d in r["deliverables"] if d["name"] == "見積書.xlsx")
    assert est["versions"] == ["見積書_v1.0.xlsx", "見積書_v1.1.xlsx"]  # latest last
    r = json.loads(run_cli("outputs", "tidy", cwd=ws, tmp=tmp_path).stdout)
    assert len(r["moved"]) == 5 and r["clutter"] == []
    assert all((ws / m).is_file() for m in r["moved"])  # moved into .brse/work/old, not deleted
    assert (out / "overview.drawio.claims.json").is_file() and (out / "old-system-flow.drawio").is_file()
