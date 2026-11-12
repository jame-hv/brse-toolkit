"""Pull the translatable text out of an Office file, and write translations back
into a COPY, keeping formatting — the fixed tool for translating documents.

Usage:
  brse.py office-text extract <file> [--max-chars N]            → JSON units (+ parts for long files)
  brse.py office-text apply <file> <translations.json> <out> [project_dir] [--beside | --to-column <letter>] [--allow-losing-drawings] [--keep-cell-style]
translations.json = {"<unit id>": "<translated text>", ...}; ids from extract.

Every unit carries "context" so it is never translated blind: .xlsx → sheet, the
nearest filled cell to the left in the same row ("left") and above in the same
column ("above") — e.g. 作成者 | 池 tells the translator 池 is a person's name;
.docx → the heading the paragraph sits under; .pptx → the slide number.
"parts" never cut a sheet, a slide or a heading section in two unless that one
piece alone is longer than --max-chars.
--beside (.xlsx): keep the source table and write the translated table to its
right (same rows, same column order, same formatting, one empty column between).
--to-column C (.xlsx): the sheet already has an empty column for the translation
(a bilingual estimate): each translated cell goes into column C of the same row,
the source cell stays; a target cell that already holds other text is refused.
.xlsx text inside shapes and text boxes is extracted too (ids <sheet>!drawing<k>/sp<n>/p<m>),
and "pictures" lists every picture on a sheet: text inside a picture cannot be
extracted — read each one (--pictures-dir DIR writes them out, EMF converted to PNG
with LibreOffice) and report what it says. In-place .xlsx writing edits the package
XML, so pictures, EMF, shapes and charts are kept. --beside goes through openpyxl
and is refused for a file with drawings unless --allow-losing-drawings is given.

Covered: .docx body, tables, text boxes, headers, footers (every <w:p> in those
parts); .pptx every text frame, table cell and speaker notes; .xlsx every
non-formula string cell. Not touched: sheet names (formulas refer to them),
formulas, numbers, fields' instruction codes.
Formatting: a paragraph whose runs carry different formatting (e.g. one bold
word) is extracted with markers — 新本番環境は⟦1⟧AWS東京リージョン⟦/1⟧に構築する。 —
and the translation must keep each ⟦n⟧…⟦/n⟧ pair around the matching words;
apply rebuilds the runs so every part gets its original formatting back. Ids of
such units are listed under "marked"; a translation that drops or invents a
marker is reported under "marker_errors" and falls back to plain text. .xlsx is written through the office
CLI when one is configured and its round-trip check passes; otherwise openpyxl, with
a warning if the file holds drawings (openpyxl drops shapes and charts).
Never writes over the input file.
"""
import sys
import copy
import json
import re
import zipfile
from pathlib import Path

from brse import config as brse_config
from brse.cli import take
from brse.office.xlsx import filled_cells, load_workbook

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
A = "{http://schemas.openxmlformats.org/drawingml/2006/main}"
MARK_RE = re.compile(r"⟦(\d+)⟧(.*?)⟦/\1⟧", re.S)
VOLATILE_RPR = ("lang", "altLang", "dirty", "err", "noProof")


# ---------- runs with mixed formatting ----------
def fmt_key(run, rpr_tag):
    rpr = run.find(rpr_tag)
    if rpr is None:
        return b""
    rpr = copy.deepcopy(rpr)
    for k in VOLATILE_RPR:
        rpr.attrib.pop(k, None)
    from lxml import etree
    return etree.tostring(rpr)


def group_runs(runs, rpr_tag):
    """Consecutive runs with the same formatting → [(fmt, [runs])]."""
    groups = []
    for r in runs:
        k = fmt_key(r, rpr_tag)
        if groups and groups[-1][0] == k:
            groups[-1][1].append(r)
        else:
            groups.append((k, [r]))
    return groups


def marked_text(groups, t_tag):
    """Text with ⟦n⟧…⟦/n⟧ around every group whose formatting differs from the first."""
    base = groups[0][0]
    out = []
    for i, (k, rs) in enumerate(groups):
        text = "".join(t.text or "" for r in rs for t in r.iter(t_tag))
        out.append(text if k == base or not text else f"⟦{i}⟧{text}⟦/{i}⟧")
    return "".join(out)


def segments(text, n_groups):
    """'a⟦2⟧b⟦/2⟧c' → [(0,'a'), (2,'b'), (0,'c')]; None when markers are unusable."""
    segs, pos = [], 0
    for m in MARK_RE.finditer(text):
        if m.start() > pos:
            segs.append((0, text[pos:m.start()]))
        idx = int(m.group(1))
        if not 0 < idx < n_groups:
            return None
        segs.append((idx, m.group(2)))
        pos = m.end()
    if pos < len(text):
        segs.append((0, text[pos:]))
    if "⟦" in "".join(t for _, t in segs):
        return None
    return segs


def write_runs(runs, groups, text, t_tag):
    """Put `text` into the paragraph's runs; with markers, rebuild runs per segment."""
    segs = segments(text, len(groups)) if len(groups) > 1 else None
    first = runs[0]
    parent = first.getparent()
    if segs is None or any(r.getparent() is not parent for r in runs):  # nested runs (hyperlinks): plain text
        clean = MARK_RE.sub(lambda m: m.group(2), text)
        for i, r in enumerate(runs):
            for j, t in enumerate(r.iter(t_tag)):
                t.text = clean if i == 0 and j == 0 else ""
        return segs is not None or len(groups) == 1
    at = parent.index(first)
    new_runs = []
    for idx, seg in segs:
        if not seg:
            continue
        r = copy.deepcopy(groups[idx][1][0])
        ts = list(r.iter(t_tag))
        for t in ts[1:]:
            t.getparent().remove(t)
        ts[0].text = seg
        ts[0].set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
        new_runs.append(r)
    for r in runs:
        parent.remove(r)
    for k, r in enumerate(new_runs):
        parent.insert(at + k, r)
    return True


# ---------- docx ----------
def docx_parts(doc):
    yield "body", doc.element.body
    seen = set()
    for i, s in enumerate(doc.sections):
        for kind in ("header", "footer", "first_page_header", "first_page_footer",
                     "even_page_header", "even_page_footer"):
            part = getattr(s, kind)
            if part.is_linked_to_previous:
                continue
            el = part._element
            if id(el) in seen:
                continue
            seen.add(id(el))
            yield f"s{i}.{kind}", el


def docx_paragraphs(doc):
    for name, root in docx_parts(doc):
        for n, p in enumerate(root.iter(W + "p")):
            runs = [r for r in p.iter(W + "r") if r.find(W + "t") is not None]
            text = "".join(t.text or "" for r in runs for t in r.iter(W + "t"))
            if text.strip():
                yield f"{name}#p{n}", p, runs, text


def is_heading(p) -> bool:
    style = p.find(f"{W}pPr/{W}pStyle")
    name = (style.get(W + "val") if style is not None else "") or ""
    return name.lower().startswith(("heading", "title")) or "見出し" in name


def extract_docx(path):
    import docx
    units, marked, heading = [], [], ""
    for uid, p, runs, text in docx_paragraphs(docx.Document(path)):
        groups = group_runs(runs, W + "rPr")
        t = marked_text(groups, W + "t") if len(groups) > 1 else text
        if is_heading(p):
            heading = text
        units.append({"id": uid, "text": t, "context": {"heading": heading}})
        if t != text:
            marked.append(uid)
    return units, marked


def apply_docx(path, tr, out):
    import docx
    doc = docx.Document(path)
    applied, errors = [], []
    for uid, _, runs, _ in docx_paragraphs(doc):
        if uid in tr:
            if not write_runs(runs, group_runs(runs, W + "rPr"), tr[uid], W + "t"):
                errors.append(uid)
            applied.append(uid)
    doc.save(out)
    return applied, errors


# ---------- pptx ----------
def pptx_paragraphs(prs):
    for si, slide in enumerate(prs.slides, 1):
        frames = []
        for shape in slide.shapes:
            if shape.has_text_frame:
                frames.append((f"s{si}/sh{shape.shape_id}", shape.text_frame))
            if getattr(shape, "has_table", False) and shape.has_table:
                for ri, row in enumerate(shape.table.rows):
                    for ci, cell in enumerate(row.cells):
                        frames.append((f"s{si}/sh{shape.shape_id}/r{ri}c{ci}", cell.text_frame))
        if slide.has_notes_slide:
            frames.append((f"s{si}/notes", slide.notes_slide.notes_text_frame))
        for prefix, tf in frames:
            for pi, p in enumerate(tf.paragraphs):
                if p.text.strip():
                    yield f"{prefix}/p{pi}", p


def pptx_runs(p):
    return [r for r in p._p.iter(A + "r") if r.find(A + "t") is not None]


def extract_pptx(path):
    from pptx import Presentation
    units, marked = [], []
    for uid, p in pptx_paragraphs(Presentation(path)):
        runs = pptx_runs(p)
        groups = group_runs(runs, A + "rPr") if runs else []
        t = marked_text(groups, A + "t") if len(groups) > 1 else p.text
        units.append({"id": uid, "text": t, "context": {"slide": int(uid.split("/")[0][1:])}})
        if t != p.text:
            marked.append(uid)
    return units, marked


def apply_pptx(path, tr, out):
    from pptx import Presentation
    prs = Presentation(path)
    applied, errors = [], []
    for uid, p in pptx_paragraphs(prs):
        runs = pptx_runs(p)
        if uid in tr and runs:
            if not write_runs(runs, group_runs(runs, A + "rPr"), tr[uid], A + "t"):
                errors.append(uid)
            applied.append(uid)
    prs.save(out)
    return applied, errors


# ---------- xlsx ----------
def xlsx_cells(wb):
    for ws in wb.worksheets:
        for c in filled_cells(ws):
            if isinstance(c.value, str) and c.value.strip() and not c.value.startswith("="):
                yield f"{ws.title}!{c.coordinate}", ws, c


def nearest(filled: dict, r: int, c: int, dr: int, dc: int):
    r, c = r + dr, c + dc
    while r > 0 and c > 0:
        if (r, c) in filled:
            return filled[(r, c)]
        r, c = r + dr, c + dc
    return None


def extract_xlsx(path):
    # ponytail: "left"/"above" = nearest filled cell; a merged header is found only from its own first column
    wb = load_workbook(path)
    units = []
    for ws in wb.worksheets:
        filled = {(c.row, c.column): str(c.value) for c in filled_cells(ws)
                  if c.value is not None and str(c.value).strip()}
        for uid, _, c in ((u, w, c) for u, w, c in xlsx_cells(wb) if w is ws):
            units.append({"id": uid, "text": c.value, "context": {
                "sheet": ws.title, "left": nearest(filled, c.row, c.column, 0, -1),
                "above": nearest(filled, c.row, c.column, -1, 0)}})
    from brse.office import xlsx_package
    units += xlsx_package.drawing_units(Path(path), group_runs, marked_text)
    marked = [u["id"] for u in units if "⟦" in u["text"]]
    return units, marked


def has_drawings(path) -> bool:
    with zipfile.ZipFile(path) as z:
        return any(n.startswith(("xl/drawings/", "xl/charts/")) for n in z.namelist())


def write_beside(wb, tr):
    """Translated table to the right of each sheet's used range: same rows, same formatting."""
    from openpyxl.utils import get_column_letter
    applied = []
    for ws in wb.worksheets:
        ids = {f"{ws.title}!{c.coordinate}": c for c in filled_cells(ws)}
        if not any(i in tr for i in ids):
            continue
        off = ws.max_column + 1
        for uid, c in ids.items():
            if c.value is None and not c.has_style:
                continue
            dst = ws.cell(row=c.row, column=c.column + off)
            dst.value = tr.get(uid, c.value)
            if c.has_style:
                dst._style = copy.copy(c._style)
            if uid in tr:
                applied.append(uid)
        for m in list(ws.merged_cells.ranges):
            ws.merge_cells(start_row=m.min_row, end_row=m.max_row,
                           start_column=m.min_col + off, end_column=m.max_col + off)
        for col in range(1, off):
            w = ws.column_dimensions[get_column_letter(col)].width
            if w:
                ws.column_dimensions[get_column_letter(col + off)].width = w
    return applied


def write_to_column(wb, tr, col):
    from openpyxl.utils.cell import coordinate_from_string
    applied = []
    for uid, text in tr.items():
        sheet, _, coord = uid.partition("!")
        if sheet not in wb.sheetnames or "/" in coord:
            continue
        ws = wb[sheet]
        dst = ws[f"{col}{coordinate_from_string(coord)[1]}"]
        if dst.value not in (None, "", text):
            raise Refused(f"{sheet}!{dst.coordinate} already holds text — not overwritten")
        dst.value = text
        applied.append(uid)
    return applied


def apply_xlsx(path, tr, out, config, beside=False, allow_losing_drawings=False, keep_style=False, to_column=None):
    from brse.office import xlsx_package
    if not beside and not to_column:  # in place: edit the package XML, so pictures, EMF and shapes stay as they are
        same = {u["id"] for u in extract_xlsx(path)[0] if tr.get(u["id"]) == u["text"]}  # nothing to rewrite
        written = xlsx_package.write(Path(path), Path(out), {k: v for k, v in tr.items() if k not in same},
                                     write_runs, group_runs, fit=not keep_style)
        return written + sorted(same), \
            "written at package level: everything not translated is copied unchanged" + (
                "" if keep_style else "; translated cells that would be cut off are set to shrink to fit")
    note = None
    if has_drawings(path) and not allow_losing_drawings:
        raise Refused("the file has drawings/charts (shapes, images) and writing it through openpyxl would drop "
                      "them — configure an office CLI (/brse-toolkit:setup) or pass --allow-losing-drawings "
                      "and tell the user what will be missing")
    wb = load_workbook(path)
    if to_column:
        applied = write_to_column(wb, tr, to_column.upper())
    elif beside:
        applied = write_beside(wb, tr)
    else:
        applied = []
        for uid, _, c in xlsx_cells(wb):
            if uid in tr:
                c.value = tr[uid]
                applied.append(uid)
    wb.save(out)
    if has_drawings(path):
        note = (note + "; " if note else "") + "WARNING: file has drawings/charts — openpyxl drops them; check the copy"
    return applied, note


class Refused(Exception):
    pass


EXTRACT = {".docx": extract_docx, ".pptx": extract_pptx, ".xlsx": extract_xlsx, ".xlsm": extract_xlsx}


def dump_pictures(path, pics, out_dir):
    import shutil
    import subprocess
    import tempfile
    out_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path) as z:
        for i, pic in enumerate(pics, 1):
            name = f"{i:02d}-{pic['sheet']}-{Path(pic['part']).name}"
            dest = out_dir / name
            dest.write_bytes(z.read(pic["part"]))
            pic["file"] = str(dest)
            exe = shutil.which("soffice") or shutil.which("libreoffice")
            if dest.suffix.lower() in (".emf", ".wmf") and exe:
                with tempfile.TemporaryDirectory() as tmp:
                    subprocess.run([exe, "--headless", "--convert-to", "png", "--outdir", tmp, str(dest)],
                                   capture_output=True, timeout=120)
                    png = Path(tmp) / (dest.stem + ".png")
                    if png.is_file():
                        shutil.copy2(png, dest.with_suffix(".png"))
                        pic["file"] = str(dest.with_suffix(".png"))
    return pics


def group_key(u):
    ctx = u.get("context", {})
    return ctx.get("sheet") or ctx.get("slide") or ctx.get("heading") or ""


def parts(units, max_chars):
    """Whole groups (sheet / slide / heading section) packed up to max_chars; a group longer
    than max_chars on its own is split unit by unit."""
    groups = []
    for u in units:
        if groups and group_key(groups[-1][-1]) == group_key(u):
            groups[-1].append(u)
        else:
            groups.append([u])
    out, cur, size = [], [], 0
    for g in groups:
        g_size = sum(len(u["text"]) for u in g)
        if g_size > max_chars:
            for u in g:
                if cur and size + len(u["text"]) > max_chars:
                    out.append(cur)
                    cur, size = [], 0
                cur.append(u["id"])
                size += len(u["text"])
            continue
        if cur and size + g_size > max_chars:
            out.append(cur)
            cur, size = [], 0
        cur += [u["id"] for u in g]
        size += g_size
    return out + ([cur] if cur else [])


def main() -> None:
    args = sys.argv[1:]
    if not args or args[0] not in ("extract", "apply"):
        print(__doc__, file=sys.stderr)
        sys.exit(2)
    cmd, path = args[0], Path(args[1])
    ext = path.suffix.lower()
    if ext not in EXTRACT:
        print(json.dumps({"error": f"unsupported file type {ext}"}))
        sys.exit(2)
    if cmd == "extract":
        max_chars = int(args[args.index("--max-chars") + 1]) if "--max-chars" in args else 6000
        units, mixed = EXTRACT[ext](path)
        pics = []
        if ext in (".xlsx", ".xlsm"):
            from brse.office import xlsx_package
            pics = xlsx_package.pictures(path)
            if "--pictures-dir" in args:
                pics = dump_pictures(path, pics, Path(args[args.index("--pictures-dir") + 1]))
        dup = {}
        for u in units:
            dup.setdefault(u["text"], []).append(u["id"])
        print(json.dumps({"file": str(path), "units": units, "marked": mixed,
                          "duplicates": {t: ids for t, ids in dup.items() if len(ids) > 1},
                          "parts": parts(units, max_chars), "pictures": pics,
                          "total_chars": sum(len(u["text"]) for u in units)}, ensure_ascii=False, indent=2))
        return
    to_column = take(args, "--to-column")
    beside, allow, keep_style = "--beside" in args, "--allow-losing-drawings" in args, "--keep-cell-style" in args
    args = [a for a in args if a not in ("--beside", "--allow-losing-drawings", "--keep-cell-style")]
    tr_path, out = Path(args[2]), Path(args[3])
    if out.resolve() == path.resolve():
        print(json.dumps({"error": "refusing to overwrite the input file — write to a copy"}))
        sys.exit(2)
    _, config = brse_config.workspace(args[4] if len(args) > 4 else ".")
    tr = json.loads(tr_path.read_text(encoding="utf-8"))
    known = {u["id"] for u in EXTRACT[ext](path)[0]}
    unknown = sorted(set(tr) - known)
    tr = {k: v for k, v in tr.items() if k in known}
    out.parent.mkdir(parents=True, exist_ok=True)
    errors, note = [], None
    if ext in (".xlsx", ".xlsm"):
        try:
            applied, note = apply_xlsx(path, tr, out, config, beside, allow, keep_style, to_column)
        except Refused as e:
            print(json.dumps({"error": str(e)}, ensure_ascii=False))
            sys.exit(2)
    else:
        applied, errors = (apply_docx if ext == ".docx" else apply_pptx)(path, tr, out)
    from brse.translate import record
    record.applied(out, path)
    print(json.dumps({"out": str(out), "applied": len(applied), "untranslated": sorted(known - set(applied)),
                      "unknown_ids": unknown, "marker_errors": errors, "note": note,
                      "next": f"brse.py translation-check {path} <translations.json> {out}"}, ensure_ascii=False, indent=2))

