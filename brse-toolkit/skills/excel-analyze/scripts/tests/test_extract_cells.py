import json
import subprocess
import sys
import pathlib

import openpyxl
from openpyxl.styles import Font, PatternFill
from openpyxl.comments import Comment

SCRIPT = pathlib.Path(__file__).resolve().parents[1] / "extract-cells.py"


def make_fixture(path):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "ScreenA"
    ws["A1"] = "必須項目"
    ws["A1"].font = Font(color="FFFF0000", strike=True)
    ws["A1"].fill = PatternFill(fill_type="solid", fgColor="FFFFFF00")
    ws["A1"].comment = Comment("cần xác nhận lại", "brse")
    ws["B1"] = "登録"
    wb.save(path)


def run(xlsx_path):
    result = subprocess.run(
        [sys.executable, str(SCRIPT), str(xlsx_path)],
        capture_output=True, text=True, encoding="utf-8",
    )
    return json.loads(result.stdout), result.returncode


def test_extracts_value_format_and_comment(tmp_path):
    xlsx = tmp_path / "fixture.xlsx"
    make_fixture(xlsx)
    out, code = run(xlsx)
    assert code == 0
    cells = {c["cell"]: c for c in out["ScreenA"]}
    assert cells["A1"]["value"] == "必須項目"
    assert cells["A1"]["strike"] is True
    assert cells["A1"]["comment"] == "cần xác nhận lại"
    assert cells["B1"]["value"] == "登録"
    assert cells["B1"]["strike"] is False


def test_empty_cells_are_skipped(tmp_path):
    xlsx = tmp_path / "fixture.xlsx"
    make_fixture(xlsx)
    out, _ = run(xlsx)
    coords = {c["cell"] for c in out["ScreenA"]}
    assert "C1" not in coords
