#!/usr/bin/env python3
"""Extract embedded pictures from an xlsx file, with their anchor cell range.

Usage: extract-images.py <xlsx_path> <out_dir>
Note: anchor is a CELL RANGE (images float over cells), not a single exact cell —
report this limitation when citing an image as a source.
"""
import json
import os
import sys

import openpyxl


def extract(path: str, out_dir: str) -> list[dict]:
    wb = openpyxl.load_workbook(path)
    os.makedirs(out_dir, exist_ok=True)
    results = []
    for ws in wb.worksheets:
        for i, img in enumerate(getattr(ws, "_images", [])):
            anchor = img.anchor
            from_marker = getattr(anchor, "_from", None)
            to_marker = getattr(anchor, "to", None)
            from_cell = f"col{from_marker.col},row{from_marker.row}" if from_marker else "unknown"
            to_cell = f"col{to_marker.col},row{to_marker.row}" if to_marker else "unknown"
            filename = f"{ws.title}_{i}.png"
            out_path = os.path.join(out_dir, filename)
            with open(out_path, "wb") as f:
                f.write(img._data())
            results.append({
                "sheet": ws.title,
                "file": out_path,
                "anchor_from": from_cell,
                "anchor_to": to_cell,
            })
    return results


def main() -> None:
    if len(sys.argv) != 3:
        print("usage: extract-images.py <xlsx_path> <out_dir>", file=sys.stderr)
        sys.exit(2)
    print(json.dumps({"images": extract(sys.argv[1], sys.argv[2])}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
