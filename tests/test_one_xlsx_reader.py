import io
import json

import openpyxl
from openpyxl.drawing.image import Image as XLImage
from PIL import Image

from brse_testkit import run_cli


def test_ingest_and_extract_agree_on_xlsx(ws, tmp_path):
    wb = openpyxl.Workbook()
    sh = wb.active
    sh.title = "Data"
    sh["A1"], sh["B1"], sh["A2"], sh["B2"] = "項目", "値", 3, "=A2*2"
    png = io.BytesIO()
    Image.new("RGB", (10, 10), "red").save(png, format="PNG")
    sh.add_image(XLImage(png), "D4")
    xlsx = ws / "src-docs" / "spec.xlsx"
    wb.save(xlsx)
    ingest = json.loads(run_cli("kb-ingest", ws, tmp=tmp_path).stdout)
    assert ingest["by_status"] == {"partial": 1}
    units = {u["id"] for u in json.loads(run_cli("office-text", "extract", xlsx).stdout)["units"]}
    cells = json.loads(run_cli("extract-cells", xlsx).stdout)["Data"]
    text_cells = {f"Data!{c['cell']}" for c in cells if isinstance(c["value"], str) and c["formula"] is None}
    assert units == text_cells == {"Data!A1", "Data!B1"}


def test_sheet_formatted_far_out_stays_small(ws, tmp_path):
    """Real alarm sheets: a few cells of data, formatting out to the far corner. These used to need 4 GB."""
    from openpyxl.styles import Font
    wb = openpyxl.Workbook()
    sh = wb.active
    sh.title = "Alarm"
    sh["B2"], sh["C2"] = "異常", "コード"
    sh.cell(row=500000, column=8000).font = Font(bold=True)
    xlsx = ws / "src-docs" / "alarm.xlsx"
    wb.save(xlsx)
    r = run_cli("kb-ingest", ws, tmp=tmp_path)
    assert r.returncode == 0, r.stderr
    md = (ws / ".brse/knowledge/docs/src-docs/alarm.xlsx.md").read_text(encoding="utf-8")
    assert "異常" in md and len(md) < 500
    assert len(json.loads(run_cli("office-text", "extract", xlsx).stdout)["units"]) == 2
    assert len(json.loads(run_cli("extract-cells", xlsx).stdout)["Alarm"]) <= 3


def test_rows_of_only_excel_errors_are_left_out_and_counted(ws, tmp_path):
    wb = openpyxl.Workbook()
    sh = wb.active
    sh.title = "Alarm"
    sh["A1"] = "異常"
    for r in range(2, 6):
        sh.cell(r, 1, "#NUM!")
    wb.save(ws / "src-docs" / "e.xlsx")
    assert run_cli("kb-ingest", ws, tmp=tmp_path).returncode == 0
    md = (ws / ".brse/knowledge/docs/src-docs/e.xlsx.md").read_text(encoding="utf-8")
    assert "#NUM!" in md.split("Not read as text")[1] and "| #NUM! |" not in md and "4 row(s)" in md
