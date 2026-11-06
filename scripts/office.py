#!/usr/bin/env python3
"""One entry point for Office operations: use the office CLI the user has
(config.tools.office_order), fall back to LibreOffice / Python, and always say which.

Usage:
  office.py info   <file> [project_dir]          structure summary (sheets, pages, slides)
  office.py render <file> <out_dir> [project_dir]  every page / slide / sheet → PNG, for visual checks
  office.py check  <file> [project_dir]          .xlsx: does open → save keep everything? (round-trip)
Prints {"op", "tool", "fallback_reason", ...}. tool = the CLI name, "libreoffice", or "python".
"""
import sys

sys.dont_write_bytecode = True
import json
import shutil
import subprocess
import tempfile
from pathlib import Path

import brse_common

KIND = {".xlsx": "xlsx", ".xlsm": "xlsx", ".docx": "docx", ".pptx": "pptx",
        ".png": "image", ".jpg": "image", ".jpeg": "image"}


def kind_of(path: Path) -> str:
    k = KIND.get(path.suffix.lower())
    if not k:
        raise ValueError(f"unsupported file type: {path.suffix}")
    return k


def find_cli(kind: str, config: dict):
    """(cli name, path) of the first available office CLI for this kind, else (None, reason)."""
    tools = config.get("tools", {})
    tried = []
    for name in tools.get("office_order", {}).get(kind, []):
        if name == "python":
            break
        p = tools.get("paths", {}).get(name)
        p = p if p and Path(p).is_file() else shutil.which(name)
        if p:
            return name, p
        tried.append(name)
    return None, f"no office CLI found for .{kind} (tried: {', '.join(tried) or 'none configured'})"


def run(args, timeout=300) -> subprocess.CompletedProcess:
    r = subprocess.run([str(a) for a in args], capture_output=True, text=True,
                       encoding="utf-8", errors="replace", timeout=timeout)
    if r.returncode != 0:
        raise RuntimeError((r.stderr or r.stdout).strip()[-500:] or f"exit {r.returncode}")
    return r


def soffice():
    return shutil.which("soffice") or shutil.which("libreoffice")


def pdf_to_pngs(pdf: Path, out_dir: Path, stem: str) -> list:
    if not shutil.which("pdftoppm"):
        raise RuntimeError("pdftoppm not installed (poppler-utils)")
    run(["pdftoppm", "-png", "-r", "110", pdf, out_dir / stem])
    return sorted(str(p) for p in out_dir.glob(f"{stem}*.png"))


def render_with_libreoffice(path: Path, out_dir: Path) -> list:
    exe = soffice()
    if not exe:
        raise RuntimeError("LibreOffice not installed")
    with tempfile.TemporaryDirectory() as tmp:
        run([exe, "--headless", "--convert-to", "pdf", "--outdir", tmp, path], timeout=240)
        pdf = Path(tmp) / (path.stem + ".pdf")
        return pdf_to_pngs(pdf, out_dir, path.stem)


def op_info(path: Path, config: dict) -> dict:
    kind = kind_of(path)
    name, cli = find_cli(kind, config)
    if name and kind in ("xlsx", "docx", "pptx"):
        args = [cli, "info", path] + (["--json"] if kind == "xlsx" else [])
        return {"tool": name, "info": json.loads(run(args).stdout)}
    if kind == "xlsx":
        import openpyxl
        wb = openpyxl.load_workbook(path)
        info = {"sheets": [{"name": ws.title, "visibility": ws.sheet_state, "usedRange": ws.dimensions,
                            "images": len(ws._images), "charts": len(ws._charts)} for ws in wb.worksheets]}
    elif kind == "docx":
        import docx
        d = docx.Document(path)
        info = {"paragraphs": len(d.paragraphs), "tables": len(d.tables), "images": len(d.inline_shapes)}
    elif kind == "pptx":
        from pptx import Presentation
        info = {"slides": len(Presentation(path).slides)}
    else:
        from PIL import Image
        with Image.open(path) as im:
            info = {"size": im.size, "mode": im.mode}
    return {"tool": "python", "fallback_reason": cli if name is None else None, "info": info}


def op_render(path: Path, out_dir: Path, config: dict) -> dict:
    kind = kind_of(path)
    out_dir.mkdir(parents=True, exist_ok=True)
    name, cli = find_cli(kind, config)
    reason = cli if name is None else None
    if name:
        try:
            if kind == "pptx":
                run([cli, "render", path, "--all", out_dir])
                return {"tool": name, "images": sorted(str(p) for p in out_dir.glob("slide-*.png"))}
            if kind == "docx":
                pages = json.loads(run([cli, "info", path]).stdout).get("pages", 1)
                imgs = []
                for n in range(1, pages + 1):
                    out = out_dir / f"{path.stem}-page-{n:02d}.png"
                    run([cli, "render", path, out, "--page", n])
                    imgs.append(str(out))
                return {"tool": name, "images": imgs}
            if kind == "xlsx":
                with tempfile.TemporaryDirectory() as tmp:
                    pdf = Path(tmp) / (path.stem + ".pdf")
                    run([cli, "convert", path, pdf])
                    return {"tool": name, "images": pdf_to_pngs(pdf, out_dir, path.stem)}
        except Exception as e:  # CLI present but failed: fall back, and say why
            reason = f"{name} failed: {e}"
    if kind == "image":
        dest = out_dir / path.name
        shutil.copy2(path, dest)
        return {"tool": "copy", "images": [str(dest)]}
    return {"tool": "libreoffice", "fallback_reason": reason, "images": render_with_libreoffice(path, out_dir)}


def op_check(path: Path, config: dict) -> dict:
    if kind_of(path) != "xlsx":
        return {"tool": None, "fallback_reason": "round-trip check exists for .xlsx only"}
    name, cli = find_cli("xlsx", config)
    if name is None:
        return {"tool": None, "fallback_reason": name,
                "note": "no fidelity oracle: write to a copy and compare with office-diff.py"}
    data = json.loads(run([cli, "check", path, "--json"]).stdout)["files"][0]
    cats = data.get("roundTrip", {}).get("categories", {})
    lost = {k: v.get("examples", [])[:3] for k, v in cats.items() if not v.get("equal", True)}
    return {"tool": name, "opened": data.get("opened"), "error": data.get("error"),
            "round_trip_ok": not lost and data.get("error") is None, "would_lose": lost}


def main() -> None:
    args = sys.argv[1:]
    if len(args) < 2 or args[0] not in ("info", "render", "check"):
        print(__doc__, file=sys.stderr)
        sys.exit(2)
    op, path = args[0], Path(args[1])
    rest = args[2:]
    out_dir = None
    if op == "render":
        if not rest:
            print("render needs <out_dir>", file=sys.stderr)
            sys.exit(2)
        out_dir, rest = Path(rest[0]), rest[1:]
    _, config = brse_common.workspace(rest[0] if rest else ".")
    try:
        if op == "info":
            out = op_info(path, config)
        elif op == "render":
            out = op_render(path, out_dir, config)
        else:
            out = op_check(path, config)
    except Exception as e:
        print(json.dumps({"op": op, "error": f"{type(e).__name__}: {e}"}, ensure_ascii=False))
        sys.exit(1)
    print(json.dumps({"op": op, **out}, ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    main()
