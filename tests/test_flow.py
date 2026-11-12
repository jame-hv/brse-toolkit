"""The estimate run: the gate refuses to stamp the estimate until every step holds."""
import json

import openpyxl

from brse_testkit import run_cli
from test_gate import answer, gate, setup


def run(ws, tmp_path, *args):
    r = run_cli("run", *args, tmp=tmp_path, cwd=ws)
    return r.returncode, json.loads(r.stdout)


def reg(ws, tmp_path, *args):
    r = run_cli("register", *args, tmp=tmp_path, cwd=ws)
    assert r.returncode == 0, r.stdout + r.stderr


def test_estimate_run_steps_gate_the_stamp(ws, tmp_path):
    t = setup(ws, tmp_path)
    (ws / "src-docs" / "画面仕様_v1.md").write_text("# 画面A\n- F2: 再印刷\n", encoding="utf-8")
    (ws / "src-docs" / "画面仕様_v2.md").write_text("# 画面A\n- F2: 再印刷\n- F3: 保留 ※新規\n", encoding="utf-8")
    assert run_cli("kb-ingest", ws, tmp=tmp_path, cwd=ws).returncode == 0
    f = ws / "output" / "est.xlsx"
    wb = openpyxl.Workbook()
    sh = wb.active
    sh.title = "明細"
    sh["B1"], sh["B2"], sh["B3"] = "作業項目", "画面A：F3保留ボタン追加", "画面A：F2再印刷ボタン追加"
    wb.save(f)

    code, out = run(ws, tmp_path, "start", "estimate", "--file", f)
    assert code == 1 and "not paired" in out["steps"]["versions"]
    code, out = run(ws, tmp_path, "pair", "src-docs/画面仕様_v1.md", "src-docs/画面仕様_v2.md")
    assert out["steps"]["versions"] == "pass" and "no requirements" in out["steps"]["requirements"]

    reg(ws, tmp_path, "add", "R", "--title", "F3保留ボタン", "--source", "src-docs/画面仕様_v2.md:3",
        "--set", "old_source=none")
    reg(ws, tmp_path, "add", "R", "--title", "F2再印刷", "--source", "src-docs/画面仕様_v2.md:2")
    code, out = run(ws, tmp_path, "status")
    assert "R-002: no old_source" in out["steps"]["requirements"]
    reg(ws, tmp_path, "update", "R-002", "--set", "old_source=src-docs/画面仕様_v1.md:2", "--status", "out")
    code, out = run(ws, tmp_path, "status")
    assert out["steps"]["requirements"] == "pass"

    # approval only counts after the user replied
    code, out = run(ws, tmp_path, "approve")
    assert code == 2 and "not replied" in out["error"]
    with t.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps({"type": "user", "message": {"role": "user", "content": "ok, duyệt"}}) + "\n")
    code, out = run(ws, tmp_path, "approve")
    assert out["steps"]["approved"] == "pass"

    # a row for something the old spec already had (R-002 is out) and a row with no basis are refused
    (ws / "rows.json").write_text(json.dumps({"明細!B2": "R-001", "明細!B3": "R-002"}))
    code, out = run(ws, tmp_path, "rows", ws / "rows.json", "--column", "B", "--from", "2")
    assert "R-002: that requirement is out of scope" in out["steps"]["rows"]
    _, out = gate(ws, tmp_path, "check", f, "--kind", "estimate-cell")
    answer(ws, tmp_path, out["next"], [])
    code, out = gate(ws, tmp_path, "check", f, "--kind", "estimate-cell")
    assert code == 1 and "rows" in out["estimate_steps_missing"]

    sh["B3"] = None
    wb.save(f)
    (ws / "rows.json").write_text(json.dumps({"明細!B2": "R-001"}))
    code, out = run(ws, tmp_path, "rows", ws / "rows.json", "--column", "B", "--from", "2")
    assert code == 0 and out["done"]
    code, out = gate(ws, tmp_path, "check", f, "--kind", "estimate-cell")
    assert code == 0 and out["pass"]


def test_version_families_from_file_names():
    from brse.harness.flow import family
    assert family("docs/画面仕様_v2.md") == family("docs/画面仕様_v1.md") == "docs/画面仕様.md"
    assert family("spec_Rev.3.pdf") == family("spec_Rev2.pdf") == "spec.pdf"
    assert family("設計書_第2版.xlsx") == "設計書.xlsx"
    assert family("設計資料_20240101.xlsx") is None
