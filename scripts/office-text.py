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

sys.dont_write_bytecode = True
import copy
import importlib.util
import json
import re
import zipfile
from pathlib import Path

import brse_common

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
A = "{http://schemas.openxmlformats.org/drawingml/2006/main}"
MARK_RE = re.compile(r"⟦(\d+)⟧(.*?)⟦/\1⟧", re.S)
VOLATILE_RPR = ("lang", "altLang", "dirty", "err", "noProof")


def office_module():
    spec = importlib.util.spec_from_file_location("office", brse_common.ROOT / "scripts" / "office.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


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


def extract_docx(path):
    import docx
    units, marked = [], []
    for uid, _, runs, text in docx_paragraphs(docx.Document(path)):
        groups = group_runs(runs, W + "rPr")
        t = marked_text(groups, W + "t") if len(groups) > 1 else text
        units.append({"id": uid, "text": t})
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
        units.append({"id": uid, "text": t})
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
        for row in ws.iter_rows():
            for c in row:
                if isinstance(c.value, str) and c.value.strip() and not c.value.startswith("="):
                    yield f"{ws.title}!{c.coordinate}", ws, c


def extract_xlsx(path):
    import openpyxl
    wb = openpyxl.load_workbook(path)
    return [{"id": uid, "text": c.value} for uid, _, c in xlsx_cells(wb)], []  # cells: one format each


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
        print(json.dumps({"file": str(path), "units": units, "marked": mixed,
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
    errors, note = [], None
    if ext in (".xlsx", ".xlsm"):
        applied, note = apply_xlsx(path, tr, out, config)
    else:
        applied, errors = (apply_docx if ext == ".docx" else apply_pptx)(path, tr, out)
    print(json.dumps({"out": str(out), "applied": len(applied), "untranslated": sorted(known - set(applied)),
                      "unknown_ids": unknown, "marker_errors": errors, "note": note}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
