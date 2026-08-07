#!/usr/bin/env python3
"""Extract cell values + formatting (color, strike, fill, comment) from an xlsx file.

Usage: extract-cells.py <xlsx_path>
Prints JSON: {"<sheet name>": [{"cell": "A1", "value": ..., "font_color": ..., "strike": ..., "fill_color": ..., "comment": ...}, ...]}
"""
import json
import sys

import openpyxl


def _rgb(color_obj):
    if color_obj is None:
        return None
    rgb = getattr(color_obj, "rgb", None)
    return rgb if isinstance(rgb, str) else None


def extract(path: str) -> dict:
    wb = openpyxl.load_workbook(path, data_only=True)
    sheets = {}
    for ws in wb.worksheets:
        cells = []
        for row in ws.iter_rows():
            for cell in row:
                if cell.value is None:
                    continue
                font = cell.font
                fill = cell.fill
                cells.append({
                    "cell": cell.coordinate,
                    "value": cell.value,
                    "font_color": _rgb(font.color) if font else None,
                    "strike": bool(font.strike) if font else False,
                    "fill_color": _rgb(fill.fgColor) if fill else None,
                    "comment": cell.comment.text.strip() if cell.comment else None,
                })
        sheets[ws.title] = cells
    return sheets


def main() -> None:
    if len(sys.argv) != 2:
        print("usage: extract-cells.py <xlsx_path>", file=sys.stderr)
        sys.exit(2)
    print(json.dumps(extract(sys.argv[1]), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
