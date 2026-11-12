import json

import docx
import openpyxl
from openpyxl.styles import Font
from pptx import Presentation

from brse_testkit import run_script


def test_xlsx_reports_value_changes_and_lost_formatting(tmp_path):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Est"
    ws["A1"], ws["B1"], ws["C1"] = "Item", "Days", "Note"
    ws["A1"].font = Font(bold=True)
    ws.merge_cells("A3:C3")
    wb.save(tmp_path / "before.xlsx")
    ws["B1"] = "Effort"            # value change
    ws["A1"].font = Font(bold=False)  # same value, formatting lost
    ws.unmerge_cells("A3:C3")
    wb.save(tmp_path / "after.xlsx")
    out = json.loads(run_script("office-diff.py", tmp_path / "before.xlsx", tmp_path / "after.xlsx").stdout)
    sheet = out["sheets"]["Est"]
    assert sheet["values_changed"]["items"] == [{"cell": "B1", "before": "Days", "after": "Effort"}]
    assert sheet["style_changed_same_value"]["items"] == ["A1"]
    assert sheet["merged_removed"] == ["A3:C3"]
    assert out["identical_formatting"] is False


def test_xlsx_identical_files(tmp_path):
    wb = openpyxl.Workbook()
    wb.active["A1"] = 1
    wb.save(tmp_path / "a.xlsx")
    wb.save(tmp_path / "b.xlsx")
    out = json.loads(run_script("office-diff.py", tmp_path / "a.xlsx", tmp_path / "b.xlsx").stdout)
    assert out["identical_formatting"] is True
    assert out["sheets"]["Sheet"]["values_changed"]["total"] == 0


def test_docx_and_pptx_text_changes(tmp_path):
    for name, text in (("a", "Scope: search"), ("b", "Scope: search and order")):
        d = docx.Document()
        d.add_paragraph(text)
        d.save(tmp_path / f"{name}.docx")
        p = Presentation()
        p.slides.add_slide(p.slide_layouts[1]).shapes.title.text = text
        p.save(tmp_path / f"{name}.pptx")
    d = json.loads(run_script("office-diff.py", tmp_path / "a.docx", tmp_path / "b.docx").stdout)
    assert {"id": "body#p0", "before": "Scope: search", "after": "Scope: search and order"} in d["text_changes"]["items"]
    p = json.loads(run_script("office-diff.py", tmp_path / "a.pptx", tmp_path / "b.pptx").stdout)
    assert "1" in p["changed_slides"]


def test_office_diff_rejects_mismatched_types(tmp_path):
    (tmp_path / "a.xlsx").write_bytes(b"")
    (tmp_path / "b.docx").write_bytes(b"")
    assert run_script("office-diff.py", tmp_path / "a.xlsx", tmp_path / "b.docx").returncode == 2


def test_library_add_list_remove(tmp_path):
    f = tmp_path / "estimate.xlsx"
    f.write_bytes(b"data")
    added = json.loads(run_script("library.py", "add", f, "--kind", "estimate", "--note", "approved v2",
                                  tmp=tmp_path).stdout)
    assert added["kind"] == "estimate" and (tmp_path / "data").exists()
    listed = json.loads(run_script("library.py", "list", "--kind", "estimate", tmp=tmp_path).stdout)
    assert [i["id"] for i in listed] == [added["id"]]
    assert json.loads(run_script("library.py", "list", "--kind", "proposal", tmp=tmp_path).stdout) == []
    run_script("library.py", "remove", added["id"], tmp=tmp_path)
    assert json.loads(run_script("library.py", "list", tmp=tmp_path).stdout) == []
