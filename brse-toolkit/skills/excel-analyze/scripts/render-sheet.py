#!/usr/bin/env python3
"""Fallback for shapes/textboxes/arrows openpyxl can't read structurally: render
the workbook to PNG via headless LibreOffice, then hand it to image-analyze.

Usage: render-sheet.py <xlsx_path> <out_dir>
Prints JSON {"file": "<path to rendered .png>"}.
PNG (not PDF) on purpose: image-analyze's `ocr-pass.py` opens the file with
Pillow, which cannot read PDFs — the fallback chain only works if this step
hands over a real image (spec mục 6.3/6.4).
Requires `libreoffice` on PATH. MVP renders the whole workbook (LibreOffice's
default active-sheet export) — per-sheet PNG splitting is a possible refinement,
not needed for the fallback's current scope (spec mục 6.3).
"""
import json
import subprocess
import sys
import os


def render_png(xlsx_path: str, out_dir: str) -> str:
    os.makedirs(out_dir, exist_ok=True)
    subprocess.run(
        ["libreoffice", "--headless", "--convert-to", "png", "--outdir", out_dir, xlsx_path],
        check=True, capture_output=True,
    )
    base = os.path.splitext(os.path.basename(xlsx_path))[0]
    return os.path.join(out_dir, f"{base}.png")


def main() -> None:
    if len(sys.argv) != 3:
        print("usage: render-sheet.py <xlsx_path> <out_dir>", file=sys.stderr)
        sys.exit(2)
    png_path = render_png(sys.argv[1], sys.argv[2])
    print(json.dumps({"file": png_path}, ensure_ascii=False))


if __name__ == "__main__":
    main()
