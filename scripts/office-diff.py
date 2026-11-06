#!/usr/bin/env python3
"""Compare an Office file before and after it was written — the check that a
write changed exactly what was intended and kept the formatting.

Usage: office-diff.py <before> <after>     (same extension: .xlsx/.xlsm, .docx, .pptx)
.xlsx: sheets added/removed; per sheet the cells whose value changed, cells whose
       value is the same but whose style changed (font, fill, number format,
       alignment, border — the "formatting got lost" signal), max row/column,
       merged ranges, image count.
.docx: paragraph-level text diff, table count, inline image count.
.pptx: per-slide text diff, shape count, picture count.
Prints JSON; "identical_formatting": false whenever any style/merge/image count
moved. Lists are capped at 200 entries (with a total count).
"""
import sys

sys.dont_write_bytecode = True
import difflib
import json
from pathlib import Path

CAP = 200


def capped(items: list) -> dict:
    return {"total": len(items), "items": items[:CAP]}


def style_key(c):
    f, fl, a, b = c.font, c.fill, c.alignment, c.border
    return (f.name, f.sz, f.b, f.i, f.u, f.strike, str(f.color.rgb if f.color else None),
            fl.fill_type, str(fl.fgColor.rgb if fl.fgColor else None), c.number_format,
            a.horizontal, a.vertical, a.wrap_text,
            b.left.style, b.right.style, b.top.style, b.bottom.style)


def diff_xlsx(before: Path, after: Path) -> dict:
    import openpyxl
    a, b = openpyxl.load_workbook(before), openpyxl.load_workbook(after)
    out = {"sheets_added": [s for s in b.sheetnames if s not in a.sheetnames],
           "sheets_removed": [s for s in a.sheetnames if s not in b.sheetnames], "sheets": {}}
    formatting_same = not out["sheets_removed"]
    for name in [s for s in a.sheetnames if s in b.sheetnames]:
        wa, wb = a[name], b[name]
        values, styles = [], []
        rows = max(wa.max_row, wb.max_row)
        cols = max(wa.max_column, wb.max_column)
        for r in range(1, rows + 1):
            for c in range(1, cols + 1):
                ca, cb = wa.cell(r, c), wb.cell(r, c)
                if ca.value != cb.value:
                    values.append({"cell": ca.coordinate, "before": str(ca.value), "after": str(cb.value)})
                elif style_key(ca) != style_key(cb):
                    styles.append(ca.coordinate)
        merged_a = {str(m) for m in wa.merged_cells.ranges}
        merged_b = {str(m) for m in wb.merged_cells.ranges}
        sheet = {"values_changed": capped(values), "style_changed_same_value": capped(styles),
                 "size_before": [wa.max_row, wa.max_column], "size_after": [wb.max_row, wb.max_column],
                 "merged_removed": sorted(merged_a - merged_b), "merged_added": sorted(merged_b - merged_a),
                 "images_before": len(wa._images), "images_after": len(wb._images)}
        if styles or sheet["merged_removed"] or sheet["images_before"] != sheet["images_after"]:
            formatting_same = False
        out["sheets"][name] = sheet
    out["identical_formatting"] = formatting_same
    return out


def text_diff(a: list, b: list) -> list:
    return [l for l in difflib.unified_diff(a, b, "before", "after", lineterm="", n=0)
            if not l.startswith(("---", "+++", "@@"))]


def docx_texts(doc) -> dict:
    """Every paragraph with text — body, tables, text boxes, headers, footers — by office-text's ids."""
    import importlib.util
    spec = importlib.util.spec_from_file_location("ot", Path(__file__).resolve().parent / "office-text.py")
    ot = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(ot)
    return {uid: text for uid, _, _, text in ot.docx_paragraphs(doc)}


def diff_docx(before: Path, after: Path) -> dict:
    import docx
    a, b = docx.Document(before), docx.Document(after)
    ta, tb = docx_texts(a), docx_texts(b)
    changes = [{"id": k, "before": ta.get(k), "after": tb.get(k)} for k in sorted(set(ta) | set(tb))
               if ta.get(k) != tb.get(k)]
    out = {"paragraphs_before": len(ta), "paragraphs_after": len(tb),
           "text_changes": capped(changes),
           "tables_before": len(a.tables), "tables_after": len(b.tables),
           "images_before": len(a.inline_shapes), "images_after": len(b.inline_shapes)}
    out["identical_formatting"] = out["images_before"] == out["images_after"] and out["tables_before"] == out["tables_after"]
    return out


def slide_texts(prs):
    return [[s.text_frame.text for s in sl.shapes if s.has_text_frame] for sl in prs.slides]


def diff_pptx(before: Path, after: Path) -> dict:
    from pptx import Presentation
    a, b = Presentation(before), Presentation(after)
    ta, tb = slide_texts(a), slide_texts(b)
    slides = {}
    for i in range(max(len(ta), len(tb))):
        sa = ta[i] if i < len(ta) else []
        sb = tb[i] if i < len(tb) else []
        sha = list(a.slides)[i].shapes if i < len(ta) else []
        shb = list(b.slides)[i].shapes if i < len(tb) else []
        changes = text_diff(sa, sb)
        pics_a = sum(1 for s in sha if s.shape_type == 13)
        pics_b = sum(1 for s in shb if s.shape_type == 13)
        if changes or len(sha) != len(shb) or pics_a != pics_b:
            slides[str(i + 1)] = {"text_changes": changes, "shapes_before": len(sha), "shapes_after": len(shb),
                                  "pictures_before": pics_a, "pictures_after": pics_b}
    return {"slides_before": len(ta), "slides_after": len(tb), "changed_slides": slides,
            "identical_formatting": all(v["pictures_before"] == v["pictures_after"] for v in slides.values())}


def main() -> None:
    if len(sys.argv) != 3:
        print("usage: office-diff.py <before> <after>", file=sys.stderr)
        sys.exit(2)
    before, after = Path(sys.argv[1]), Path(sys.argv[2])
    ext = before.suffix.lower()
    fn = {".xlsx": diff_xlsx, ".xlsm": diff_xlsx, ".docx": diff_docx, ".pptx": diff_pptx}.get(ext)
    if fn is None or after.suffix.lower() != ext:
        print(json.dumps({"error": f"need two files with the same supported extension, got {ext} / {after.suffix}"}))
        sys.exit(2)
    print(json.dumps(fn(before, after), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
