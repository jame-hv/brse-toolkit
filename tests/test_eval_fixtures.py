"""The eval cases' synthetic workspaces build, and hold what the graders expect."""
import subprocess

import openpyxl
import pytest

from brse_testkit import ROOT


@pytest.mark.parametrize("case,kind", [("diagram-system-from-spec", "diagram"),
                                       ("ingest-answer-and-remember", "ingest"),
                                       ("intent-check-without-editing", "intent")])
def test_case_workspace_builds(case, kind, tmp_path):
    r = subprocess.run(["bash", str(ROOT / "evals" / case / "setup.sh")], cwd=tmp_path, capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    claude_md = (tmp_path / "CLAUDE.md").read_text(encoding="utf-8")
    assert claude_md.startswith("<!-- brse-toolkit:start -->") and "demo-order" in claude_md
    assert "<project name>" not in claude_md
    assert (tmp_path / ".brse" / "config.json").is_file()
    if kind == "intent":
        est = openpyxl.load_workbook(tmp_path / "documents" / "見積_v1.xlsx")["見積"]
        qa = openpyxl.load_workbook(tmp_path / "documents" / "QA一覧_回答済.xlsx")["QA"]
        assert est["C2"].value == 4 and "5画面" in qa["C2"].value and "範囲外" in qa["C3"].value
