"""Every openpyxl workbook load in the toolkit goes through load_workbook() here.

extract-cells: Extract cell values + formatting (color, strike, fill, comment) from an xlsx file.

Usage: brse.py extract-cells <xlsx_path>
Prints JSON: {"<sheet name>": [{"cell": "A1", "value": ..., "font_color": ..., "strike": ..., "fill_color": ..., "comment": ...}, ...]}

extract-images: Extract embedded pictures from an xlsx file, with their anchor cell range.

Usage: brse.py extract-images <xlsx_path> <out_dir>
Note: anchor is a CELL RANGE (images float over cells), not a single exact cell —
report this limitation when citing an image as a source.
"""
import os
import datetime
import json
import sys



def _json_default(obj):
    if isinstance(obj, (datetime.datetime, datetime.date, datetime.time)):
        return obj.isoformat()
    raise TypeError(f"Object of type {obj.__class__.__name__} is not JSON serializable")


def _rgb(color_obj):
    if color_obj is None:
        return None
    rgb = getattr(color_obj, "rgb", None)
    return rgb if isinstance(rgb, str) else None


def read_cells(path: str) -> dict:
    # Two loads on purpose: data_only=True resolves formulas to their cached
    # value, but once resolved a cell's data_type no longer says "formula" —
    # there is no way to tell "formula with no cached value" apart from "truly
    # empty cell" from this load alone. The data_only=False load keeps the raw
    # formula string so that distinction can be made explicit instead of the
    # cell silently vanishing (a real bug this replaced: an unopened/
    # unrecalculated file — e.g. written by a script, never opened in Excel/
    # LibreOffice — would drop every formula cell with zero warning).
    wb_values = load_workbook(path, values=True)
    wb_formulas = load_workbook(path)
    sheets = {}
    for ws in wb_values.worksheets:
        ws_formulas = wb_formulas[ws.title]
        cells = []
        known = {(c.row, c.column) for c in filled_cells(ws)} | {(c.row, c.column) for c in filled_cells(ws_formulas)}
        for row_col in sorted(known):
            for cell in (ws.cell(*row_col),):
                raw = ws_formulas.cell(*row_col).value
                is_formula = isinstance(raw, str) and raw.startswith("=")
                if cell.value is None:
                    if not is_formula:
                        continue
                    # Formula cell, no cached value available.
                    cells.append({
                        "cell": cell.coordinate,
                        "value": None,
                        "formula": raw,
                        "warning": "formula has no cached value — source file was "
                                   "likely never opened/saved in Excel or LibreOffice; "
                                   "re-save it there to populate a cached value",
                    })
                    continue
                font = cell.font
                fill = cell.fill
                cells.append({
                    "cell": cell.coordinate,
                    "value": cell.value,
                    "formula": raw if is_formula else None,
                    "font_color": _rgb(font.color) if font else None,
                    "strike": bool(font.strike) if font else False,
                    "fill_color": _rgb(fill.fgColor) if fill else None,
                    "comment": cell.comment.text.strip() if cell.comment else None,
                })
        sheets[ws.title] = cells
    return sheets


def cells_main() -> None:
    if len(sys.argv) != 2:
        print("usage: brse.py extract-cells <xlsx_path>", file=sys.stderr)
        sys.exit(2)
    print(json.dumps(read_cells(sys.argv[1]), ensure_ascii=False, indent=2, default=_json_default))



def filled_cells(ws) -> list:
    """Cells that exist, row by row. Never ws.iter_rows()/ws.cell() on a whole sheet: they create every
    cell of the used range, and a sheet formatted out to the last column then needs gigabytes."""
    return [ws._cells[k] for k in sorted(ws._cells)]


def sheet_rows(ws) -> list:
    """Non-empty rows as lists of values, trimmed to the columns that hold data."""
    cells = [c for c in filled_cells(ws) if c.value is not None and str(c.value).strip()]
    if not cells:
        return []
    first, last = min(c.column for c in cells), max(c.column for c in cells)
    rows = {}
    for c in cells:
        rows.setdefault(c.row, [None] * (last - first + 1))[c.column - first] = c.value
    return [rows[r] for r in sorted(rows)]


EXCEL_ERRORS = {"#NUM!", "#REF!", "#N/A", "#DIV/0!", "#VALUE!", "#NAME?", "#NULL!"}


def stream_rows(path):
    """(sheet title, visibility, non-empty rows trimmed to their data columns, rows dropped), read row
    by row: memory stays flat however far a sheet is formatted. A row holding nothing but Excel error
    values (a formula filled down to the last row) is dropped and counted. Text only; never written back."""
    import openpyxl
    wb = openpyxl.load_workbook(path, data_only=True, read_only=True)
    try:
        for ws in wb.worksheets:
            ws.reset_dimensions()  # the file's own <dimension> can claim the whole grid
            rows, dropped = [], 0
            for values in ws.iter_rows(values_only=True):
                row = list(values)
                while row and (row[-1] is None or not str(row[-1]).strip()):
                    row.pop()
                filled = [v for v in row if v is not None and str(v).strip()]
                if filled and all(str(v) in EXCEL_ERRORS for v in filled):
                    dropped += 1
                elif filled:
                    rows.append(row)
            lead = min((next(i for i, v in enumerate(r) if v is not None and str(v).strip()) for r in rows), default=0)
            yield ws.title, ws.sheet_state, [r[lead:] for r in rows], dropped
    finally:
        wb.close()


def load_workbook(path, values: bool = False):
    import openpyxl
    return openpyxl.load_workbook(path, data_only=values)



def extract_images(path: str, out_dir: str) -> list[dict]:
    wb = load_workbook(path)
    os.makedirs(out_dir, exist_ok=True)
    results = []
    for ws in wb.worksheets:
        for i, img in enumerate(getattr(ws, "_images", [])):
            anchor = img.anchor
            from_marker = getattr(anchor, "_from", None)
            to_marker = getattr(anchor, "to", None)
            from_cell = f"col{from_marker.col},row{from_marker.row}" if from_marker else "unknown"
            to_cell = f"col{to_marker.col},row{to_marker.row}" if to_marker else "unknown"
            ext = (getattr(img, "format", None) or "png").lower()
            filename = f"{ws.title}_{i}.{ext}"
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


def images_main() -> None:
    if len(sys.argv) != 3:
        print("usage: brse.py extract-images <xlsx_path> <out_dir>", file=sys.stderr)
        sys.exit(2)
    print(json.dumps({"images": extract_images(sys.argv[1], sys.argv[2])}, ensure_ascii=False, indent=2))

