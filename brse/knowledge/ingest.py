"""Convert the workspace's source documents into searchable Markdown + an index.

Usage: brse.py kb-ingest [project_dir] [--force]
For every file under config.paths.sources (origin "client"), paths.internal
("internal") and paths.deliverables ("delivered"):
  .brse/knowledge/docs/<source path>.md   readable Markdown copy, with a header
  .brse/knowledge/manifest.json           per file: sha256, status, parts, what could NOT be read
  .brse/knowledge/index.sqlite            FTS5 index of chunks (sheet / slide / page / block)
Only files whose sha256 changed are converted again (--force: all).
Status: "ok" | "partial" (some content needs visual reading: images, shapes,
charts) | "unreadable" (format not supported or conversion failed) — never
silently skipped. Needs openpyxl / python-docx / python-pptx (run with the
Python recorded by /brse-toolkit:setup).
"""
import sys
import datetime
import hashlib
import json
import shutil
import sqlite3
import subprocess
from pathlib import Path

from brse import config as brse_config
from brse import markdown

TEXT_EXT = {".md", ".txt", ".csv", ".tsv", ".json", ".xml", ".html", ".htm", ".sql", ".yaml", ".yml"}
IMAGE_EXT = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp", ".tif", ".tiff"}


def cell_text(v) -> str:
    if v is None:
        return ""
    if isinstance(v, (datetime.date, datetime.datetime)):
        return v.isoformat()
    return str(v).replace("|", "\\|").replace("\n", "<br>")


def md_table(rows: list) -> str:
    """rows = list of cell-text lists; first row is treated as the header."""
    return markdown.table(rows[0], rows[1:]) if rows else "(empty)"


def convert_xlsx(path: Path):
    from brse.office.xlsx import stream_rows
    from brse.office.xlsx_package import drawing_counts
    counts = drawing_counts(path)
    chunks, notes = [], []
    for title, sheet_state, rows, dropped in stream_rows(path):
        state = "" if sheet_state == "visible" else f" ({sheet_state})"
        chunks.append((f"sheet {title}{state}", md_table([[cell_text(c) for c in r] for r in rows])))
        if dropped:
            notes.append(f"sheet {title}: {dropped} row(s) holding only Excel error values (#NUM! …) left out")
        found = counts.get(title, {})
        if found.get("images"):
            notes.append(f"sheet {title}: {found['images']} image(s) — read with excel-analyze")
        if found.get("charts"):
            notes.append(f"sheet {title}: {found['charts']} chart(s) — read with excel-analyze")
    notes.append("shapes/text boxes are not extracted from .xlsx — render with excel-analyze if the sheet has any")
    return chunks, notes


def convert_docx(path: Path):
    import docx
    d = docx.Document(path)
    chunks, block, n = [], [], 0
    for p in d.paragraphs:
        if p.style.name.lower().startswith("heading") and block:
            chunks.append((f"paragraphs {n - len(block) + 1}-{n}", "\n".join(block)))
            block = []
        if p.text.strip():
            n += 1
            prefix = "#" * min(int(p.style.name[-1]) if p.style.name[-1].isdigit() else 1, 6) + " " \
                if p.style.name.lower().startswith("heading") else ""
            block.append(prefix + p.text)
    if block:
        chunks.append((f"paragraphs {n - len(block) + 1}-{n}", "\n".join(block)))
    for i, t in enumerate(d.tables, 1):
        chunks.append((f"table {i}", md_table([[cell_text(c.text) for c in r.cells] for r in t.rows])))
    images = len(d.inline_shapes)
    notes = [f"{images} inline image(s) — read with image-analyze"] if images else []
    return chunks, notes


def convert_pptx(path: Path):
    from pptx import Presentation
    prs = Presentation(path)
    chunks, notes = [], []
    for i, slide in enumerate(prs.slides, 1):
        texts, pictures = [], 0
        for shape in slide.shapes:
            if shape.has_text_frame and shape.text_frame.text.strip():
                texts.append(shape.text_frame.text.strip())
            if getattr(shape, "has_table", False) and shape.has_table:
                texts.append(md_table([[cell_text(c.text) for c in r.cells] for r in shape.table.rows]))
            if shape.shape_type == 13:  # picture
                pictures += 1
        if slide.has_notes_slide and slide.notes_slide.notes_text_frame.text.strip():
            texts.append("Notes: " + slide.notes_slide.notes_text_frame.text.strip())
        chunks.append((f"slide {i}", "\n".join(texts) or "(no text)"))
        if pictures:
            notes.append(f"slide {i}: {pictures} picture(s) — read with image-analyze")
    return chunks, notes


def convert_pdf(path: Path):
    if not shutil.which("pdftotext"):
        raise RuntimeError("pdftotext not installed")
    text = subprocess.run(["pdftotext", "-layout", str(path), "-"], capture_output=True,
                          text=True, encoding="utf-8", errors="replace", check=True).stdout
    pages = text.split("\f")
    return [(f"page {i}", p.strip() or "(no text — scanned page?)") for i, p in enumerate(pages, 1) if p.strip() or i < len(pages)], []


def convert_text(path: Path):
    raw = path.read_bytes()
    for enc in ("utf-8", "cp932"):
        try:
            return [("text", raw.decode(enc))], []
        except UnicodeDecodeError:
            continue
    return [("text", raw.decode("utf-8", errors="replace"))], ["undecodable bytes replaced"]


CONVERTERS = {".xlsx": convert_xlsx, ".xlsm": convert_xlsx, ".docx": convert_docx,
              ".pptx": convert_pptx, ".pdf": convert_pdf}


def convert(path: Path):
    ext = path.suffix.lower()
    if ext in CONVERTERS:
        return CONVERTERS[ext](path)
    if ext in TEXT_EXT:
        return convert_text(path)
    if ext in IMAGE_EXT:
        return [], ["image file — read with image-analyze"]
    raise RuntimeError(f"no converter for {ext or 'files without extension'}")


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


ORIGINS = (("sources", "client"), ("internal", "internal"), ("deliverables", "delivered"))


def source_files(root: Path, config: dict):
    """(origin, configured path, file or None) for every file the knowledge base covers."""
    paths = config.get("paths", {})
    for key, origin in ORIGINS:
        for src in paths.get(key, []) or []:
            base = (root / src).resolve()
            if not base.exists():
                yield origin, src, None
                continue
            files = [base] if base.is_file() else sorted(p for p in base.rglob("*") if p.is_file())
            for f in files:
                if not f.name.startswith(("~$", ".")) and ".brse" not in f.relative_to(root).parts:
                    yield origin, src, f


def open_index(db: Path):
    """FTS index; returns (connection, tokenizer, rebuilt). An index from before the
    `origin` column existed is rebuilt."""
    con = sqlite3.connect(db)
    cols = [r[1] for r in con.execute("PRAGMA table_info(chunks)")]
    rebuilt = bool(cols) and "origin" not in cols
    if rebuilt:
        con.execute("DROP TABLE chunks")
    try:
        con.execute("CREATE VIRTUAL TABLE IF NOT EXISTS chunks USING fts5(path, ref, text, origin UNINDEXED, tokenize='trigram')")
        tokenizer = "trigram"
    except sqlite3.OperationalError:  # SQLite < 3.34 has no trigram tokenizer
        con.execute("CREATE VIRTUAL TABLE IF NOT EXISTS chunks USING fts5(path, ref, text, origin UNINDEXED)")
        tokenizer = "unicode61"
    return con, tokenizer, rebuilt


def main() -> None:
    args = [a for a in sys.argv[1:] if a != "--force"]
    force = "--force" in sys.argv
    root, config = brse_config.workspace(args[0] if args else ".")
    if root is None:
        print(json.dumps({"error": "not inside a brse-toolkit workspace — run /brse-toolkit:init"}))
        sys.exit(1)
    kb = root / ".brse" / "knowledge"
    docs = kb / "docs"
    docs.mkdir(parents=True, exist_ok=True)
    manifest_path = kb / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.is_file() else {}
    con, tokenizer, rebuilt = open_index(kb / "index.sqlite")
    force = force or rebuilt

    seen, changed = set(), []
    for origin, src, f in source_files(root, config):
        if f is None:
            manifest[src] = {"status": "unreadable", "origin": origin, "error": "configured path does not exist"}
            seen.add(src)
            continue
        rel = f.relative_to(root).as_posix()
        seen.add(rel)
        st = f.stat()
        old = manifest.get(rel, {})
        digest = sha256(f)
        if not force and old.get("sha256") == digest:
            old.update({"mtime": st.st_mtime, "size": st.st_size, "origin": origin})
            continue
        con.execute("DELETE FROM chunks WHERE path = ?", (rel,))
        entry = {"sha256": digest, "origin": origin, "mtime": st.st_mtime, "size": st.st_size,
                 "converted_at": datetime.datetime.now().isoformat(timespec="seconds")}
        if old.get("sha256"):
            entry["previous_sha256"] = old["sha256"]
            entry["previous_converted_at"] = old.get("converted_at")
        try:
            chunks, notes = convert(f)
            out = docs / (rel + ".md")
            out.parent.mkdir(parents=True, exist_ok=True)
            body = [f"<!-- source: {rel} · sha256: {digest[:12]} · converted by kb-ingest -->", f"# {rel}", ""]
            for ref, text in chunks:
                body += [f"## {ref}", "", text, ""]
                con.execute("INSERT INTO chunks (path, ref, text, origin) VALUES (?, ?, ?, ?)", (rel, ref, text, origin))
            if notes:
                body += ["## Not read as text", ""] + [f"- {n}" for n in notes]
            out.write_text("\n".join(body), encoding="utf-8")
            visual = [n for n in notes if "image" in n or "chart" in n or "picture" in n]
            entry.update({"status": "partial" if visual or not chunks else "ok",
                          "markdown": out.relative_to(root).as_posix(),
                          "parts": [r for r, _ in chunks], "not_read": notes})
        except Exception as e:
            entry.update({"status": "unreadable", "error": f"{type(e).__name__}: {e}"})
        manifest[rel] = entry
        changed.append(rel)
        con.commit()  # a crash on a later file must not lose this one
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    for gone in set(manifest) - seen:
        con.execute("DELETE FROM chunks WHERE path = ?", (gone,))
        md = docs / (gone + ".md")
        if md.is_file():
            md.unlink()
        del manifest[gone]
    con.commit()
    con.close()
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    summary = {}
    for v in manifest.values():
        summary[v["status"]] = summary.get(v["status"], 0) + 1
    print(json.dumps({"files": len(manifest), "converted_now": changed, "by_status": summary,
                      "tokenizer": tokenizer,
                      "unreadable": {k: v.get("error") for k, v in manifest.items() if v["status"] == "unreadable"},
                      "partial": {k: v.get("not_read") for k, v in manifest.items() if v["status"] == "partial"}},
                     ensure_ascii=False, indent=2))

