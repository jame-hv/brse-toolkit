#!/usr/bin/env python3
"""Fallback for shapes/textboxes/arrows openpyxl can't read structurally: render
the workbook to PDF via headless LibreOffice, then hand it to image-analyze.

Usage: render-sheet.py <xlsx_path> <out_dir>
Prints the path to the rendered PDF.
Requires `libreoffice` on PATH. MVP renders the whole workbook (LibreOffice's
default active-sheet export) — per-sheet PNG splitting is a possible refinement,
not needed for the fallback's current scope (spec mục 6.3).
"""
import subprocess
import sys
import os


def render(xlsx_path: str, out_dir: str) -> str:
    os.makedirs(out_dir, exist_ok=True)
    subprocess.run(
        ["libreoffice", "--headless", "--convert-to", "pdf", "--outdir", out_dir, xlsx_path],
        check=True, capture_output=True,
    )
    base = os.path.splitext(os.path.basename(xlsx_path))[0]
    return os.path.join(out_dir, f"{base}.pdf")


def main() -> None:
    if len(sys.argv) != 3:
        print("usage: render-sheet.py <xlsx_path> <out_dir>", file=sys.stderr)
        sys.exit(2)
    print(render(sys.argv[1], sys.argv[2]))


if __name__ == "__main__":
    main()
