"""Read and write a .xlsx at the package (zip + XML) level, so nothing the library
does not understand — pictures, EMF, shapes, text boxes, charts — is lost.

Translation units it adds to the cell units:
  <sheet>!drawing<k>/sp<n>/p<m>   a paragraph of text inside a shape or text box
Writing: a translated cell becomes an inline string in its own <c> element; a
drawing paragraph keeps its runs' formatting (⟦n⟧ markers); a formula cell that is a
plain reference to a translated cell (=変更履歴!G1) gets the translated value as its
cached result, and the workbook is marked to recalculate on open (fullCalcOnLoad) for
any other formula that reads a translated cell; every other part is copied byte for byte.
Fit: a translated cell whose text cannot spill to the right — the next cell holds a
value, or the cell is merged — gets "shrink to fit" (a copy of its own cell style with
shrinkToFit), because translated text is usually longer than the source and would be
cut off. Cells that can spill into empty cells keep their style. fit=False turns this off.
"""
import posixpath
import re
import zipfile
from pathlib import Path

NS = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
      "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
      "xdr": "http://schemas.openxmlformats.org/drawingml/2006/spreadsheetDrawing",
      "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
      "rel": "http://schemas.openxmlformats.org/package/2006/relationships"}
M, A = "{%s}" % NS["m"], "{%s}" % NS["a"]
IMAGE_TYPE = NS["r"] + "/image"


def _xml(z, name):
    from lxml import etree
    return etree.fromstring(z.read(name))


def _rels(z, part):
    rp = posixpath.join(posixpath.dirname(part), "_rels", posixpath.basename(part) + ".rels")
    if rp not in z.namelist():
        return {}
    def target(t):  # absolute ("/xl/...", as openpyxl writes) or relative to the part
        return t.lstrip("/") if t.startswith("/") else posixpath.normpath(posixpath.join(posixpath.dirname(part), t))
    return {r.get("Id"): (r.get("Type"), target(r.get("Target"))) for r in _xml(z, rp)}


def sheets(z) -> list:
    """[(sheet name, sheet part, [drawing parts])] in workbook order."""
    wb = _xml(z, "xl/workbook.xml")
    rels = _rels(z, "xl/workbook.xml")
    out = []
    for s in wb.iter(M + "sheet"):
        part = rels[s.get("{%s}id" % NS["r"])][1]
        drawings = [t for typ, t in _rels(z, part).values() if typ.endswith("/drawing")]
        out.append((s.get("name"), part, drawings))
    return out


def drawing_paragraphs(root):
    """(shape index, paragraph index, <a:p>) for every paragraph with text in shapes / text boxes."""
    for n, sp in enumerate(root.iter("{%s}sp" % NS["xdr"])):
        body = sp.find("{%s}txBody" % NS["xdr"])
        if body is None:
            continue
        for m, p in enumerate(body.iter(A + "p")):
            if "".join(t.text or "" for t in p.iter(A + "t")).strip():
                yield n, m, p


def drawing_units(path: Path, group_runs, marked_text) -> list:
    units = []
    with zipfile.ZipFile(path) as z:
        for name, _, drawings in sheets(z):
            for k, d in enumerate(drawings, 1):
                root = _xml(z, d)
                for n, m, p in drawing_paragraphs(root):
                    runs = [r for r in p.iter(A + "r") if r.find(A + "t") is not None]
                    groups = group_runs(runs, A + "rPr")
                    text = "".join(t.text or "" for r in runs for t in r.iter(A + "t"))
                    shape = p.getparent().getparent()
                    label = shape.find(".//{%s}cNvPr" % NS["xdr"])
                    units.append({"id": f"{name}!drawing{k}/sp{n}/p{m}",
                                  "text": marked_text(groups, A + "t") if len(groups) > 1 else text,
                                  "context": {"sheet": name, "in": "shape or text box",
                                              "shape": label.get("name") if label is not None else ""}})
    return units


def drawing_counts(path: Path) -> dict:
    """{sheet: {"images": n, "charts": n}} from the package, without loading any cell."""
    out = {}
    with zipfile.ZipFile(path) as z:
        for name, _, drawings in sheets(z):
            types = [typ for d in drawings for typ, _ in _rels(z, d).values()]
            out[name] = {"images": sum(t == IMAGE_TYPE for t in types), "charts": sum(t.endswith("/chart") for t in types)}
    return out


def pictures(path: Path) -> list:
    """[{sheet, part}] for every picture placed on a sheet (text inside a picture is not extractable)."""
    out = []
    with zipfile.ZipFile(path) as z:
        for name, _, drawings in sheets(z):
            for d in drawings:
                out += [{"sheet": name, "part": t} for typ, t in _rels(z, d).values() if typ == IMAGE_TYPE]
    return out


REF = re.compile(r"^([A-Z]+)(\d+)$")
PLAIN_REF = re.compile(r"^=?(?:'([^']+)'|([^'!=]+))!\$?([A-Z]+)\$?(\d+)$")


def _col(letters: str) -> int:
    n = 0
    for ch in letters:
        n = n * 26 + ord(ch) - 64
    return n


def _letters(n: int) -> str:
    s = ""
    while n:
        n, r = divmod(n - 1, 26)
        s = chr(65 + r) + s
    return s


def _blocked(root, refs: set) -> set:
    """Refs among `refs` whose text cannot spill right: next cell has a value, or the cell is merged."""
    from lxml import etree  # noqa: F401
    filled = {c.get("r") for c in root.iter(M + "c")
              if c.find(M + "v") is not None or c.find(M + "is") is not None}
    merged = set()
    for m in root.iter(M + "mergeCell"):
        a, _, b = m.get("ref").partition(":")
        if b:
            (ca, ra), (cb, rb) = REF.match(a).groups(), REF.match(b).groups()
            merged |= {f"{_letters(c)}{r}" for c in range(_col(ca), _col(cb) + 1) for r in range(int(ra), int(rb) + 1)}
    out = set()
    for ref in refs:
        col, row = REF.match(ref).groups()
        if ref in merged or f"{_letters(_col(col) + 1)}{row}" in filled:
            out.add(ref)
    return out


class _Styles:
    """Adds shrink-to-fit copies of cell styles to xl/styles.xml, once per style."""
    def __init__(self, z):
        self.root = _xml(z, "xl/styles.xml") if "xl/styles.xml" in z.namelist() else None
        self.made, self.used = {}, False

    def shrink(self, s: str):
        if self.root is None:
            return s
        from lxml import etree
        import copy
        if s not in self.made:
            xfs = self.root.find(M + "cellXfs")
            xf = copy.deepcopy(list(xfs)[int(s or 0)])
            al = xf.find(M + "alignment")
            if al is not None and al.get("wrapText") == "1":
                self.made[s] = s  # wrapping already makes it fit
                return s
            if al is None:
                al = etree.SubElement(xf, M + "alignment")
            al.set("shrinkToFit", "1")
            xf.set("applyAlignment", "1")
            xfs.append(xf)
            xfs.set("count", str(len(xfs)))
            self.made[s] = str(len(xfs) - 1)
            self.used = True
        return self.made[s]


def write(path: Path, out: Path, translations: dict, write_runs, group_runs, fit: bool = True) -> list:
    """Copy the package, replacing translated cell values and drawing paragraphs. Returns applied ids."""
    from lxml import etree
    applied, changed = [], {}
    with zipfile.ZipFile(path) as z:
        styles = _Styles(z)
        cells = {k: v for k, v in translations.items() if "/" not in k.split("!", 1)[1]}
        for name, part, drawings in sheets(z):
            want = {k.split("!", 1)[1]: v for k, v in cells.items() if k.split("!", 1)[0] == name}
            root = _xml(z, part)
            touched = False
            for c in root.iter(M + "c"):  # formula = plain reference to a translated cell → translated cached value
                f = c.find(M + "f")
                m = PLAIN_REF.match(f.text or "") if f is not None and f.text else None
                if m and f"{m.group(1) or m.group(2)}!{m.group(3)}{m.group(4)}" in cells:
                    v = c.find(M + "v")
                    if v is None:
                        v = etree.SubElement(c, M + "v")
                    v.text = cells[f"{m.group(1) or m.group(2)}!{m.group(3)}{m.group(4)}"]
                    c.set("t", "str")
                    touched = True
            if want:
                blocked = _blocked(root, set(want)) if fit else set()
                for c in root.iter(M + "c"):
                    ref = c.get("r")
                    if ref in want:
                        if ref in blocked:
                            c.set("s", styles.shrink(c.get("s", "0")))
                        for child in list(c):
                            if child.tag in (M + "v", M + "is"):
                                c.remove(child)
                        c.set("t", "inlineStr")
                        is_ = etree.SubElement(c, M + "is")
                        t = etree.SubElement(is_, M + "t")
                        t.text = want[ref]
                        t.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
                        applied.append(f"{name}!{ref}")
                touched = True
            if touched:
                changed[part] = root
            for k, d in enumerate(drawings, 1):
                prefix = f"{name}!drawing{k}/"
                if not any(i.startswith(prefix) for i in translations):
                    continue
                root = _xml(z, d)
                for n, m, p in drawing_paragraphs(root):
                    uid = f"{prefix}sp{n}/p{m}"
                    if uid in translations:
                        runs = [r for r in p.iter(A + "r") if r.find(A + "t") is not None]
                        write_runs(runs, group_runs(runs, A + "rPr"), translations[uid], A + "t")
                        applied.append(uid)
                changed[d] = root
        if styles.used:
            changed["xl/styles.xml"] = styles.root
        if applied:  # formulas that read translated cells (lookups, arrays) are recalculated when the copy is opened
            wb = _xml(z, "xl/workbook.xml")
            calc = wb.find(M + "calcPr")
            if calc is None:
                calc = etree.SubElement(wb, M + "calcPr")
            calc.set("fullCalcOnLoad", "1")
            changed["xl/workbook.xml"] = wb
        with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as dst:
            for item in z.infolist():
                data = (etree.tostring(changed[item.filename], xml_declaration=True, encoding="UTF-8",
                                       standalone=True) if item.filename in changed else z.read(item.filename))
                dst.writestr(item, data)
    return applied
