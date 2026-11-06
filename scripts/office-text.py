#!/usr/bin/env python3
"""Pull the translatable text out of an Office file, and write translations back
into a COPY, keeping formatting — the fixed tool for translating documents.

Usage:
  office-text.py extract <file> [--max-chars N]            → JSON units (+ parts for long files)
  office-text.py apply <file> <translations.json> <out> [project_dir]
translations.json = {"<unit id>": "<translated text>", ...}; ids from extract.

Covered: .docx body, tables, text boxes, headers, footers (every <w:p> in those
parts); .pptx every text frame, table cell and speaker notes; .xlsx every
non-formula string cell. Not touched: sheet names (formulas refer to them),
formulas, numbers, fields' instruction codes.
Formatting: the paragraph keeps the formatting of its first run; paragraphs whose
runs had DIFFERENT formatting (e.g. one bold word) are listed under
"mixed_formatting" so they get a visual check. .xlsx is written through the office
CLI when one is configured and its round-trip check passes; otherwise openpyxl, with
a warning if the file holds drawings (openpyxl drops shapes and charts).
Never writes over the input file.
"""
import sys

sys.dont_write_bytecode = True
import importlib.util
import json
import zipfile
from pathlib import Path

import brse_common

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"


def office_module():
    spec = importlib.util.spec_from_file_location("office", brse_common.ROOT / "scripts" / "office.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


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


def run_format(r):
    rpr = r.find(W + "rPr")
    return b"" if rpr is None else __import__("lxml.etree", fromlist=["tostring"]).tostring(rpr)


def extract_docx(path):
    import docx
    doc = docx.Document(path)
    units, mixed = [], []
    for uid, _, runs, text in docx_paragraphs(doc):
        units.append({"id": uid, "text": text})
        if len({run_format(r) for r in runs}) > 1:
            mixed.append(uid)
    return units, mixed


def set_runs_text(runs, text, t_tag):
    """First run gets the whole text; the other runs are emptied (their formatting stays harmlessly)."""
    first = True
    for r in runs:
        ts = list(r.iter(t_tag))
        for i, t in enumerate(ts):
            t.text = text if first and i == 0 else ""
            if first and i == 0:
                t.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
        first = False


def apply_docx(path, tr, out):
    import docx
    doc = docx.Document(path)
    applied = []
    for uid, _, runs, _ in docx_paragraphs(doc):
        if uid in tr:
            set_runs_text(runs, tr[uid], W + "t")
            applied.append(uid)
    doc.save(out)
    return applied, None


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


def extract_pptx(path):
    from pptx import Presentation
    units, mixed = [], []
    for uid, p in pptx_paragraphs(Presentation(path)):
        units.append({"id": uid, "text": p.text})
        fmts = {(r.font.bold, r.font.italic, r.font.size, str(r.font.color.rgb if r.font.color and r.font.color.type else None))
                for r in p.runs}
        if len(fmts) > 1:
            mixed.append(uid)
    return units, mixed


def apply_pptx(path, tr, out):
    from pptx import Presentation
    prs = Presentation(path)
    applied = []
    for uid, p in pptx_paragraphs(prs):
        if uid in tr and p.runs:
            p.runs[0].text = tr[uid]
            for r in p.runs[1:]:
                r.text = ""
            applied.append(uid)
    prs.save(out)
    return applied, None


# ---------- xlsx ----------
def xlsx_cells(wb):
    for ws in wb.worksheets:
        for row in ws.iter_rows():
            for c in row:
                if isinstance(c.value, str) and c.value.strip() and not c.value.startswith("="):
                    yield f"{ws.title}!{c.coordinate}", ws, c


def extract_xlsx(path):
    import openpyxl
    wb = openpyxl.load_workbook(path)
    return [{"id": uid, "text": c.value} for uid, _, c in xlsx_cells(wb)], []


def has_drawings(path) -> bool:
    with zipfile.ZipFile(path) as z:
        return any(n.startswith(("xl/drawings/", "xl/charts/")) for n in z.namelist())


def apply_xlsx(path, tr, out, config):
    office = office_module()
    name, cli = office.find_cli("xlsx", config)
    if name:
        check = office.op_check(Path(path), config)
        if check.get("round_trip_ok"):
            cmds = []
            for uid, text in tr.items():
                sheet, cell = uid.rsplit("!", 1)
                cmds += ["--cmd", "range.setValues=" + json.dumps(
                    {"range": f"{sheet}!{cell}", "values": [[text]], "parse": False}, ensure_ascii=False)]
            office.run([cli, "run", "--in", path, *cmds, "--out", out, "--quiet"])
            return list(tr), f"written with {name} (round-trip check passed)"
        note = f"{name} round-trip check failed ({check.get('would_lose')}) — used openpyxl"
    else:
        note = None
    import openpyxl
    wb = openpyxl.load_workbook(path)
    applied = []
    for uid, _, c in xlsx_cells(wb):
        if uid in tr:
            c.value = tr[uid]
            applied.append(uid)
    wb.save(out)
    if has_drawings(path):
        note = (note + "; " if note else "") + "WARNING: file has drawings/charts — openpyxl drops them; check the copy"
    return applied, note


EXTRACT = {".docx": extract_docx, ".pptx": extract_pptx, ".xlsx": extract_xlsx, ".xlsm": extract_xlsx}


def parts(units, max_chars):
    out, cur, size = [], [], 0
    for u in units:
        if cur and size + len(u["text"]) > max_chars:
            out.append(cur)
            cur, size = [], 0
        cur.append(u["id"])
        size += len(u["text"])
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
        dup = {}
        for u in units:
            dup.setdefault(u["text"], []).append(u["id"])
        print(json.dumps({"file": str(path), "units": units, "mixed_formatting": mixed,
                          "duplicates": {t: ids for t, ids in dup.items() if len(ids) > 1},
                          "parts": parts(units, max_chars),
                          "total_chars": sum(len(u["text"]) for u in units)}, ensure_ascii=False, indent=2))
        return
    tr_path, out = Path(args[2]), Path(args[3])
    if out.resolve() == path.resolve():
        print(json.dumps({"error": "refusing to overwrite the input file — write to a copy"}))
        sys.exit(2)
    _, config = brse_common.workspace(args[4] if len(args) > 4 else ".")
    tr = json.loads(tr_path.read_text(encoding="utf-8"))
    known = {u["id"] for u in EXTRACT[ext](path)[0]}
    unknown = sorted(set(tr) - known)
    tr = {k: v for k, v in tr.items() if k in known}
    out.parent.mkdir(parents=True, exist_ok=True)
    if ext in (".xlsx", ".xlsm"):
        applied, note = apply_xlsx(path, tr, out, config)
    else:
        applied, note = (apply_docx if ext == ".docx" else apply_pptx)(path, tr, out)
    print(json.dumps({"out": str(out), "applied": len(applied), "untranslated": sorted(known - set(applied)),
                      "unknown_ids": unknown, "note": note}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
