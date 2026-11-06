import json

import docx
import openpyxl
import pytest
from pptx import Presentation
from pptx.util import Inches

from conftest import run_script


@pytest.fixture
def sources(ws):
    src = ws / "src-docs"
    wb = openpyxl.Workbook()
    wb.active.title = "Features"
    wb.active.append(["No", "Name"])
    wb.active.append([1, "注文登録"])
    hidden = wb.create_sheet("Calc")
    hidden["A1"] = "secret-formula-sheet"
    hidden.sheet_state = "hidden"
    wb.save(src / "features.xlsx")
    d = docx.Document()
    d.add_heading("Minutes", 1)
    d.add_paragraph("Decision: release one covers search only.")
    d.save(src / "minutes.docx")
    prs = Presentation()
    s = prs.slides.add_slide(prs.slide_layouts[5])
    s.shapes.title.text = "Current architecture"
    s.shapes.add_textbox(Inches(1), Inches(2), Inches(4), Inches(1)).text_frame.text = "Batch runs nightly"
    prs.save(src / "rfp.pptx")
    (src / "notes.txt").write_bytes("仕様メモ: 在庫確認".encode("cp932"))
    (src / "diagram.png").write_bytes(b"\x89PNG\r\n\x1a\n")
    (src / "blob.bin").write_bytes(b"\x00\x01")
    return src


def ingest(ws, tmp_path, *extra):
    r = run_script("kb-ingest.py", ws, *extra, tmp=tmp_path)
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout)


def test_ingest_converts_everything_and_reports_what_it_could_not_read(ws, sources, tmp_path):
    out = ingest(ws, tmp_path)
    manifest = json.loads((ws / ".brse" / "knowledge" / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["src-docs/features.xlsx"]["status"] == "ok"
    assert "sheet Calc (hidden)" in manifest["src-docs/features.xlsx"]["parts"]
    assert manifest["src-docs/minutes.docx"]["status"] == "ok"
    assert manifest["src-docs/rfp.pptx"]["parts"] == ["slide 1"]
    assert manifest["src-docs/notes.txt"]["status"] == "ok"
    assert manifest["src-docs/diagram.png"]["status"] == "partial"
    assert manifest["src-docs/blob.bin"]["status"] == "unreadable"
    assert "src-docs/blob.bin" in out["unreadable"]
    md = (ws / ".brse" / "knowledge" / "docs" / "src-docs" / "features.xlsx.md").read_text(encoding="utf-8")
    assert "| 1 | 注文登録 |" in md and "|---|---|" in md


def test_search_long_and_short_queries(ws, sources, tmp_path):
    ingest(ws, tmp_path)
    long_q = json.loads(run_script("kb-search.py", "Batch runs", ws, tmp=tmp_path).stdout)
    assert long_q["mode"] == "fts" and long_q["results"][0]["ref"] == "slide 1"
    short_q = json.loads(run_script("kb-search.py", "在庫", ws, tmp=tmp_path).stdout)
    assert short_q["mode"] == "substring" and short_q["results"][0]["path"] == "src-docs/notes.txt"


def test_only_changed_files_are_reconverted_and_deleted_files_dropped(ws, sources, tmp_path):
    ingest(ws, tmp_path)
    assert ingest(ws, tmp_path)["converted_now"] == []
    (sources / "notes.txt").write_text("changed text", encoding="utf-8")
    (sources / "blob.bin").unlink()
    out = ingest(ws, tmp_path)
    assert out["converted_now"] == ["src-docs/notes.txt"]
    manifest = json.loads((ws / ".brse" / "knowledge" / "manifest.json").read_text(encoding="utf-8"))
    assert "src-docs/blob.bin" not in manifest
    old = json.loads(run_script("kb-search.py", "在庫確認", ws, tmp=tmp_path).stdout)
    assert old["results"] == []


def test_ingest_outside_workspace_is_an_error(tmp_path):
    r = run_script("kb-ingest.py", tmp_path, tmp=tmp_path)
    assert r.returncode == 1 and "init" in json.loads(r.stdout)["error"]
