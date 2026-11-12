"""The translation tools on the cases that broke real translations."""
import json

import docx
import openpyxl

from brse_testkit import run_cli


def sheet(tmp_path):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "変更履歴"
    ws["A1"], ws["B1"], ws["C1"], ws["D1"] = "作成者", "池", "作成日", "2026年7月16日"
    ws["A2"], ws["B2"] = "管理番号", "P401_特需更新"
    ws.column_dimensions["B"].width = 30
    f = tmp_path / "dd.xlsx"
    wb.save(f)
    return f


def test_each_cell_carries_its_row_and_column_context(tmp_path):
    units = {u["id"]: u for u in json.loads(run_cli("office-text", "extract", sheet(tmp_path)).stdout)["units"]}
    assert units["変更履歴!B1"]["context"] == {"sheet": "変更履歴", "left": "作成者", "above": None}
    assert units["変更履歴!B2"]["context"]["above"] == "池"


def test_parts_never_cut_a_sheet(tmp_path):
    wb = openpyxl.Workbook()
    for name in ("A", "B", "C"):
        ws = wb.create_sheet(name)
        for r in range(1, 6):
            ws.cell(r, 1, "あ" * 20)
    del wb["Sheet"]
    wb.save(tmp_path / "s.xlsx")
    parts = json.loads(run_cli("office-text", "extract", tmp_path / "s.xlsx", "--max-chars", "250").stdout)["parts"]
    assert [sorted({i.split("!")[0] for i in p}) for p in parts] == [["A", "B"], ["C"]]


def test_docx_paragraph_knows_its_heading(tmp_path):
    d = docx.Document()
    d.add_heading("処理概要", level=1)
    d.add_paragraph("在庫を引き当てる。")
    d.save(tmp_path / "a.docx")
    units = json.loads(run_cli("office-text", "extract", tmp_path / "a.docx").stdout)["units"]
    assert units[-1]["context"] == {"heading": "処理概要"}


def test_beside_keeps_source_and_writes_translated_table_to_the_right(tmp_path):
    src = sheet(tmp_path)
    tr = {"変更履歴!A1": "Người tạo", "変更履歴!B1": "Ike", "変更履歴!C1": "Ngày tạo",
          "変更履歴!D1": "16/7/2026", "変更履歴!A2": "Mã quản lý", "変更履歴!B2": "P401_Cập nhật nhu cầu đặc biệt"}
    (tmp_path / "tr.json").write_text(json.dumps(tr, ensure_ascii=False), encoding="utf-8")
    r = run_cli("office-text", "apply", src, tmp_path / "tr.json", tmp_path / "out.xlsx", tmp_path, "--beside")
    assert r.returncode == 0, r.stdout + r.stderr
    ws = openpyxl.load_workbook(tmp_path / "out.xlsx")["変更履歴"]
    assert ws["A1"].value == "作成者" and ws["F1"].value == "Người tạo" and ws["G1"].value == "Ike"
    assert ws.column_dimensions["G"].width == 30


def test_translation_check_catches_number_code_and_glossary_and_accepts_quoted_terms(tmp_path):
    src = sheet(tmp_path)
    glossary = tmp_path / "glossary.md"
    glossary.write_text("- EN: author | VI: người lập | JP: 作成者 — confirmed, 2026-11-01 — status: active\n",
                        encoding="utf-8")
    bad = {"変更履歴!A1": "Người tạo", "変更履歴!B1": "Ao", "変更履歴!C1": "Ngày tạo",
           "変更履歴!D1": "16/8/2026", "変更履歴!A2": "Mã quản lý", "変更履歴!B2": "Cập nhật nhu cầu đặc biệt"}
    (tmp_path / "bad.json").write_text(json.dumps(bad, ensure_ascii=False), encoding="utf-8")
    r = run_cli("translation-check", src, tmp_path / "bad.json", tmp_path / "out.xlsx", "--lang", "vi",
                "--source-lang", "ja", "--glossary", glossary)
    assert r.returncode == 1
    rules = {(p["id"], p["rule"]) for p in json.loads(r.stdout)["problems"]}
    assert rules == {("変更履歴!A1", "glossary"), ("変更履歴!D1", "number"),
                     ("変更履歴!B2", "code"), ("変更履歴!B2", "number")}
    good = dict(bad, **{"変更履歴!A1": "Người lập", "変更履歴!D1": "16/07/2026",
                        "変更履歴!B2": "P401_「特需更新」(cập nhật nhu cầu đặc biệt)"})
    (tmp_path / "good.json").write_text(json.dumps(good, ensure_ascii=False), encoding="utf-8")
    r = run_cli("translation-check", src, tmp_path / "good.json", tmp_path / "out.xlsx", "--lang", "vi",
                "--source-lang", "ja", "--glossary", glossary)
    assert r.returncode == 0, r.stdout


def test_translation_check_reports_missing_units(tmp_path):
    src = sheet(tmp_path)
    (tmp_path / "t.json").write_text(json.dumps({"変更履歴!A1": "Người tạo"}, ensure_ascii=False), encoding="utf-8")
    out = json.loads(run_cli("translation-check", src, tmp_path / "t.json", tmp_path / "o.xlsx", "--lang", "vi").stdout)
    assert {p["id"] for p in out["problems"] if p["rule"] == "missing"} == {
        "変更履歴!B1", "変更履歴!C1", "変更履歴!D1", "変更履歴!A2", "変更履歴!B2"}


def test_text_in_shapes_is_extracted_written_back_and_checked(tmp_path):
    """A text box drawn on a sheet: extracted as its own unit, translated in place, the rest of the package kept."""
    import zipfile
    src = sheet(tmp_path)
    drawing = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
               '<xdr:wsDr xmlns:xdr="http://schemas.openxmlformats.org/drawingml/2006/spreadsheetDrawing" '
               'xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"><xdr:twoCellAnchor>'
               '<xdr:from><xdr:col>5</xdr:col><xdr:colOff>0</xdr:colOff><xdr:row>5</xdr:row><xdr:rowOff>0</xdr:rowOff></xdr:from>'
               '<xdr:to><xdr:col>8</xdr:col><xdr:colOff>0</xdr:colOff><xdr:row>8</xdr:row><xdr:rowOff>0</xdr:rowOff></xdr:to>'
               '<xdr:sp macro="" textlink=""><xdr:nvSpPr><xdr:cNvPr id="2" name="TextBox 1"/><xdr:cNvSpPr txBox="1"/></xdr:nvSpPr>'
               '<xdr:spPr><a:prstGeom prst="rect"><a:avLst/></a:prstGeom></xdr:spPr>'
               '<xdr:txBody><a:bodyPr/><a:lstStyle/><a:p><a:r><a:rPr lang="ja-JP"/><a:t>取込、抽出前</a:t></a:r></a:p></xdr:txBody>'
               '</xdr:sp><xdr:clientData/></xdr:twoCellAnchor></xdr:wsDr>')
    with_box = tmp_path / "box.xlsx"
    with zipfile.ZipFile(src) as zin, zipfile.ZipFile(with_box, "w") as zout:
        for item in zin.infolist():
            data = zin.read(item.filename)
            if item.filename == "xl/worksheets/sheet1.xml":
                data = data.replace(b"</worksheet>", b'<drawing r:id="rIdD1" xmlns:r="http://schemas.openxmlformats.org/'
                                    b'officeDocument/2006/relationships"/></worksheet>')
            if item.filename == "[Content_Types].xml":
                data = data.replace(b"</Types>", b'<Override PartName="/xl/drawings/drawing1.xml" ContentType="'
                                    b'application/vnd.openxmlformats-officedocument.drawing+xml"/></Types>')
            zout.writestr(item, data)
        zout.writestr("xl/worksheets/_rels/sheet1.xml.rels",
                      '<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="http://schemas.openxmlformats.org/'
                      'package/2006/relationships"><Relationship Id="rIdD1" Type="http://schemas.openxmlformats.org/'
                      'officeDocument/2006/relationships/drawing" Target="../drawings/drawing1.xml"/></Relationships>')
        zout.writestr("xl/drawings/drawing1.xml", drawing)
    units = {u["id"]: u for u in json.loads(run_cli("office-text", "extract", with_box).stdout)["units"]}
    box_id = "変更履歴!drawing1/sp0/p0"
    assert units[box_id]["text"] == "取込、抽出前"
    tr = {i: "x" for i in units}
    tr.update({"変更履歴!B1": "Ike", "変更履歴!D1": "16/7/2026", "変更履歴!B2": "P401_Cập nhật nhu cầu đặc biệt",
               box_id: "Trước khi nhập, trích xuất"})
    (tmp_path / "tr.json").write_text(json.dumps(tr, ensure_ascii=False), encoding="utf-8")
    assert run_cli("office-text", "apply", with_box, tmp_path / "tr.json", tmp_path / "out.xlsx").returncode == 0
    with zipfile.ZipFile(tmp_path / "out.xlsx") as z:
        assert "Trước khi nhập, trích xuất" in z.read("xl/drawings/drawing1.xml").decode()
    without_box = {k: v for k, v in tr.items() if k != box_id}
    (tmp_path / "partial.json").write_text(json.dumps(without_box, ensure_ascii=False), encoding="utf-8")
    r = run_cli("translation-check", with_box, tmp_path / "partial.json", tmp_path / "out.xlsx", "--lang", "vi")
    assert r.returncode == 1 and {"id": box_id, "rule": "missing", "source": "取込、抽出前"} in json.loads(r.stdout)["problems"]


def test_in_place_write_fits_blocked_cells_and_fills_reference_formulas(tmp_path):
    import zipfile
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "変更履歴"
    ws["A1"], ws["B1"], ws["A3"] = "更新者", "池", "概要の説明文"  # A1 is blocked by B1; A3 can spill into empty B3
    other = wb.create_sheet("仕様書")
    other["A1"] = "=変更履歴!B1"
    wb.save(tmp_path / "f.xlsx")
    tr = {"変更履歴!A1": "Người cập nhật", "変更履歴!B1": "Ike", "変更履歴!A3": "Câu mô tả tổng quan dài hơn"}
    (tmp_path / "tr.json").write_text(json.dumps(tr, ensure_ascii=False), encoding="utf-8")
    assert run_cli("office-text", "apply", tmp_path / "f.xlsx", tmp_path / "tr.json", tmp_path / "o.xlsx").returncode == 0
    out = openpyxl.load_workbook(tmp_path / "o.xlsx")
    assert out["変更履歴"]["A1"].alignment.shrink_to_fit is True
    assert not out["変更履歴"]["A3"].alignment.shrink_to_fit
    assert openpyxl.load_workbook(tmp_path / "o.xlsx", data_only=True)["仕様書"]["A1"].value == "Ike"
    with zipfile.ZipFile(tmp_path / "o.xlsx") as z:
        assert b'fullCalcOnLoad="1"' in z.read("xl/workbook.xml")
