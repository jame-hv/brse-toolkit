import json

import docx
import openpyxl
from openpyxl.drawing.image import Image as XLImage
from PIL import Image
from pptx import Presentation

from conftest import run_script

NO_CLI = {"PATH": "/usr/bin:/bin"}  # no office CLIs on PATH → Python paths are exercised


def make_docx(path):
    d = docx.Document()
    d.sections[0].header.paragraphs[0].text = "社外秘"
    d.sections[0].footer.paragraphs[0].text = "株式会社サンプル"
    d.add_heading("概要", 1)
    p = d.add_paragraph("本書は")
    p.add_run("検索機能").bold = True
    p.add_run("の設計を示す。")
    t = d.add_table(rows=1, cols=2)
    t.cell(0, 0).text = "項目"
    t.cell(0, 1).text = "必須"
    d.save(path)


def test_docx_extract_covers_body_table_header_footer_and_flags_mixed_runs(tmp_path):
    make_docx(tmp_path / "a.docx")
    out = json.loads(run_script("office-text.py", "extract", tmp_path / "a.docx", tmp=tmp_path, env=NO_CLI).stdout)
    texts = {u["text"] for u in out["units"]}
    assert {"社外秘", "株式会社サンプル", "概要", "本書は⟦1⟧検索機能⟦/1⟧の設計を示す。", "項目", "必須"} <= texts
    mixed = [u["id"] for u in out["units"] if u["text"].startswith("本書は")]
    assert mixed[0] in out["marked"]


def test_docx_apply_writes_copy_keeps_first_run_format_and_reports_gaps(tmp_path):
    make_docx(tmp_path / "a.docx")
    units = json.loads(run_script("office-text.py", "extract", tmp_path / "a.docx", tmp=tmp_path, env=NO_CLI).stdout)["units"]
    ids = {u["text"]: u["id"] for u in units}
    tr = {ids["社外秘"]: "Confidential", ids["概要"]: "Overview", "bogus#p9": "x"}
    (tmp_path / "tr.json").write_text(json.dumps(tr, ensure_ascii=False), encoding="utf-8")
    r = json.loads(run_script("office-text.py", "apply", tmp_path / "a.docx", tmp_path / "tr.json",
                              tmp_path / "out" / "a_en.docx", tmp=tmp_path, env=NO_CLI).stdout)
    assert r["applied"] == 2 and r["unknown_ids"] == ["bogus#p9"] and len(r["untranslated"]) == len(units) - 2
    d = docx.Document(tmp_path / "out" / "a_en.docx")
    assert d.sections[0].header.paragraphs[0].text == "Confidential"
    assert d.paragraphs[0].text == "Overview" and d.paragraphs[0].style.name == "Heading 1"
    assert docx.Document(tmp_path / "a.docx").paragraphs[0].text == "概要"  # original untouched


def test_apply_refuses_to_overwrite_input(tmp_path):
    make_docx(tmp_path / "a.docx")
    (tmp_path / "tr.json").write_text("{}", encoding="utf-8")
    r = run_script("office-text.py", "apply", tmp_path / "a.docx", tmp_path / "tr.json", tmp_path / "a.docx",
                   tmp=tmp_path, env=NO_CLI)
    assert r.returncode == 2 and "overwrite" in r.stdout


def test_pptx_extract_and_apply_text_table_and_notes(tmp_path):
    prs = Presentation()
    s = prs.slides.add_slide(prs.slide_layouts[5])
    s.shapes.title.text = "現行構成"
    tbl = s.shapes.add_table(1, 1, 0, 0, 2000000, 500000).table
    tbl.cell(0, 0).text = "バッチ"
    s.notes_slide.notes_text_frame.text = "補足説明"
    prs.save(tmp_path / "d.pptx")
    units = json.loads(run_script("office-text.py", "extract", tmp_path / "d.pptx", tmp=tmp_path, env=NO_CLI).stdout)["units"]
    ids = {u["text"]: u["id"] for u in units}
    assert set(ids) == {"現行構成", "バッチ", "補足説明"}
    tr = {ids["現行構成"]: "Kiến trúc hiện tại", ids["補足説明"]: "Ghi chú"}
    (tmp_path / "tr.json").write_text(json.dumps(tr, ensure_ascii=False), encoding="utf-8")
    run_script("office-text.py", "apply", tmp_path / "d.pptx", tmp_path / "tr.json", tmp_path / "d_vi.pptx",
               tmp=tmp_path, env=NO_CLI)
    s2 = Presentation(tmp_path / "d_vi.pptx").slides[0]
    assert s2.shapes.title.text == "Kiến trúc hiện tại" and s2.notes_slide.notes_text_frame.text == "Ghi chú"


def test_xlsx_skips_formulas_and_warns_about_drawings_without_cli(tmp_path):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "見積"
    ws["A1"], ws["B1"], ws["C1"] = "項目", 3, "=B1*2"
    Image.new("RGB", (5, 5)).save(tmp_path / "i.png")
    ws.add_image(XLImage(str(tmp_path / "i.png")), "E5")
    wb.save(tmp_path / "e.xlsx")
    units = json.loads(run_script("office-text.py", "extract", tmp_path / "e.xlsx", tmp=tmp_path, env=NO_CLI).stdout)["units"]
    assert [u["id"] for u in units] == ["見積!A1"]
    (tmp_path / "tr.json").write_text(json.dumps({"見積!A1": "Hạng mục"}, ensure_ascii=False), encoding="utf-8")
    r = json.loads(run_script("office-text.py", "apply", tmp_path / "e.xlsx", tmp_path / "tr.json", tmp_path / "e_vi.xlsx",
                              tmp_path, tmp=tmp_path, env=NO_CLI).stdout)
    assert "drawings" in r["note"]
    out = openpyxl.load_workbook(tmp_path / "e_vi.xlsx")["見積"]
    assert out["A1"].value == "Hạng mục" and out["C1"].value == "=B1*2"


def test_extract_splits_long_documents_into_parts(tmp_path):
    d = docx.Document()
    for i in range(10):
        d.add_paragraph(f"段落{i} " + "あ" * 100)
    d.save(tmp_path / "long.docx")
    out = json.loads(run_script("office-text.py", "extract", tmp_path / "long.docx", "--max-chars", "300",
                                tmp=tmp_path, env=NO_CLI).stdout)
    assert len(out["parts"]) >= 3 and sum(len(p) for p in out["parts"]) == 10


def test_office_py_falls_back_to_python_and_says_why(tmp_path):
    make_docx(tmp_path / "a.docx")
    info = json.loads(run_script("office.py", "info", tmp_path / "a.docx", tmp_path, tmp=tmp_path, env=NO_CLI).stdout)
    assert info["tool"] == "python" and "no office CLI" in info["fallback_reason"]
    wb = openpyxl.Workbook()
    wb.save(tmp_path / "x.xlsx")
    chk = json.loads(run_script("office.py", "check", tmp_path / "x.xlsx", tmp_path, tmp=tmp_path, env=NO_CLI).stdout)
    assert chk["tool"] is None and "office-diff" in chk["note"]


def test_docx_bold_word_keeps_its_formatting_after_translation(tmp_path):
    make_docx(tmp_path / "a.docx")
    units = json.loads(run_script("office-text.py", "extract", tmp_path / "a.docx", tmp=tmp_path, env=NO_CLI).stdout)["units"]
    uid = next(u["id"] for u in units if u["text"].startswith("本書は"))
    bad = next(u["id"] for u in units if u["text"] == "概要")
    tr = {uid: "Tài liệu này mô tả thiết kế của ⟦1⟧chức năng tìm kiếm⟦/1⟧.", bad: "Tổng quan ⟦7⟧x⟦/7⟧"}
    (tmp_path / "tr.json").write_text(json.dumps(tr, ensure_ascii=False), encoding="utf-8")
    r = json.loads(run_script("office-text.py", "apply", tmp_path / "a.docx", tmp_path / "tr.json", tmp_path / "b.docx",
                              tmp=tmp_path, env=NO_CLI).stdout)
    assert r["marker_errors"] == [] or r["marker_errors"] == [bad]
    p = next(p for p in docx.Document(tmp_path / "b.docx").paragraphs if p.text.startswith("Tài liệu"))
    assert p.text == "Tài liệu này mô tả thiết kế của chức năng tìm kiếm."
    assert [(run.text, bool(run.bold)) for run in p.runs] == [
        ("Tài liệu này mô tả thiết kế của ", False), ("chức năng tìm kiếm", True), (".", False)]
    heading = docx.Document(tmp_path / "b.docx").paragraphs[0].text
    assert "⟦" not in heading  # an invented marker never leaks into the document


def test_office_diff_docx_sees_tables_and_headers(tmp_path):
    make_docx(tmp_path / "a.docx")
    d = docx.Document(tmp_path / "a.docx")
    d.sections[0].header.paragraphs[0].text = "Confidential"
    d.tables[0].cell(0, 0).text = "Item"
    d.save(tmp_path / "b.docx")
    out = json.loads(run_script("office-diff.py", tmp_path / "a.docx", tmp_path / "b.docx").stdout)
    changed = {c["id"]: c for c in out["text_changes"]["items"]}
    assert any(c["before"] == "社外秘" and c["after"] == "Confidential" for c in changed.values())
    assert any(c["before"] == "項目" and c["after"] == "Item" for c in changed.values())


def test_lang_lint_reads_translation_json(tmp_path):
    f = tmp_path / "tr.json"
    f.write_text(json.dumps({"body#p0": "Tổng quan", "body#p1": "Còn sót 注文 ở đây"}, ensure_ascii=False), encoding="utf-8")
    out = json.loads(run_script("lang-lint.py", f, "--lang", "vi", "--source-lang", "ja").stdout)
    assert out["errors"] == 1 and out["findings"][0]["id"] == "body#p1"
