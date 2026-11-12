"""Convert documents to Markdown with deterministic tools only (no AI).

Usage: brse.py doc2md <file-or-folder> [<file-or-folder> ...] --out <dir> [--force]

Engines, in order:
  .docx .xlsx .xlsm .pptx .pdf .html .csv .json .xml .epub -> markitdown
  .doc .xls .ppt .rtf .odt .ods .odp -> LibreOffice converts to OOXML first, then markitdown
  .pdf with no text from markitdown -> pdftotext -layout
Each output gets a front-matter header (source, sha256, engine, converted_at).
Unchanged sources (same sha256) are skipped unless --force.
Prints one JSON summary line on stdout.
"""
import argparse, datetime, hashlib, json, shutil, subprocess, sys, tempfile
from pathlib import Path

DIRECT = {".docx", ".xlsx", ".xlsm", ".pptx", ".pdf", ".html", ".htm", ".csv", ".json", ".xml", ".epub", ".txt", ".md"}
LEGACY = {".doc": "docx", ".rtf": "docx", ".odt": "docx", ".xls": "xlsx", ".ods": "xlsx", ".ppt": "pptx", ".odp": "pptx"}


def sha256(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def markitdown_bin():
    cand = Path(sys.executable).parent / "markitdown"
    return str(cand) if cand.exists() else shutil.which("markitdown")


def run_markitdown(src):
    exe = markitdown_bin()
    if not exe:
        raise RuntimeError("markitdown not installed (pip install 'markitdown[all]' in the toolkit venv)")
    r = subprocess.run([exe, str(src)], capture_output=True, text=True, timeout=600)
    if r.returncode != 0:
        raise RuntimeError(r.stderr.strip()[-500:])
    return r.stdout


def libreoffice_convert(src, fmt, tmp):
    exe = shutil.which("soffice") or shutil.which("libreoffice")
    if not exe:
        raise RuntimeError("LibreOffice not found for legacy format " + src.suffix)
    subprocess.run([exe, "--headless", "--convert-to", fmt, "--outdir", tmp, str(src)],
                   capture_output=True, text=True, timeout=600, check=True)
    out = Path(tmp) / (src.stem + "." + fmt)
    if not out.exists():
        raise RuntimeError("LibreOffice produced no output for " + src.name)
    return out


def pdftotext(src):
    exe = shutil.which("pdftotext")
    if not exe:
        return ""
    r = subprocess.run([exe, "-layout", str(src), "-"], capture_output=True, text=True, timeout=600)
    return r.stdout if r.returncode == 0 else ""


def convert(src, out_dir, base, force):
    rel = src.relative_to(base) if base and src.is_relative_to(base) else Path(src.name)
    dest = out_dir / rel.with_suffix(rel.suffix + ".md")
    digest = sha256(src)
    if dest.exists() and not force:
        head = dest.read_text(encoding="utf-8", errors="ignore")[:600]
        if f"sha256: {digest}" in head:
            return {"source": str(src), "output": str(dest), "status": "unchanged"}
    ext = src.suffix.lower()
    engine, warnings = None, []
    with tempfile.TemporaryDirectory() as tmp:
        if ext in LEGACY:
            conv = libreoffice_convert(src, LEGACY[ext], tmp)
            body, engine = run_markitdown(conv), "libreoffice+markitdown"
        elif ext in DIRECT:
            body, engine = run_markitdown(src), "markitdown"
        else:
            return {"source": str(src), "status": "skipped", "reason": "unsupported extension " + ext}
    if ext == ".pdf" and len(body.strip()) < 50:
        alt = pdftotext(src)
        if len(alt.strip()) > len(body.strip()):
            body, engine = "```text\n" + alt + "\n```\n", "pdftotext"
        if len(body.strip()) < 50:
            warnings.append("almost no text extracted: likely a scanned PDF, needs OCR")
    dest.parent.mkdir(parents=True, exist_ok=True)
    header = ("---\n"
              f"source: {src}\n"
              f"sha256: {digest}\n"
              f"engine: {engine}\n"
              f"converted_at: {datetime.datetime.now().isoformat(timespec='seconds')}\n"
              "---\n\n")
    dest.write_text(header + body, encoding="utf-8")
    return {"source": str(src), "output": str(dest), "status": "converted", "engine": engine,
            "chars": len(body), "warnings": warnings}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("inputs", nargs="+")
    ap.add_argument("--out", required=True)
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args()
    out_dir = Path(a.out).expanduser().resolve()
    results = []
    for item in a.inputs:
        p = Path(item).expanduser().resolve()
        files = [f for f in sorted(p.rglob("*")) if f.is_file() and not f.name.startswith(("~$", "."))] if p.is_dir() else [p]
        for f in files:
            try:
                results.append(convert(f, out_dir, p if p.is_dir() else None, a.force))
            except Exception as e:  # report and continue
                results.append({"source": str(f), "status": "error", "error": str(e)})
    summary = {k: sum(1 for r in results if r["status"] == k) for k in ("converted", "unchanged", "skipped", "error")}
    print(json.dumps({"out": str(out_dir), "summary": summary, "files": results}, ensure_ascii=False))
    return 1 if summary["error"] else 0

