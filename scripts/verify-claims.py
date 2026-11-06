#!/usr/bin/env python3
"""Check that cited evidence really says what the answer claims — by opening the source.

Usage: verify-claims.py <claims.json> [project_dir]
claims.json = [{"claim": "...", "file": "<path, relative to the workspace>",
                "locator": {...}, "expect": "<value or quote the claim relies on>"}, ...]
Locators:
  {"cell": "Sheet!D4"}   .xlsx: the cell's value must equal `expect` (after normalising)
  {"line": 42}           text / code: that line must contain `expect`
  {"part": "slide 3"}    docx / pptx / pdf / xlsx: that part (as kb-ingest names it) must contain `expect`
  {} (or omitted)        anywhere in the file
Text is compared after Unicode NFKC + whitespace collapsing. Prints per-claim
status (ok / mismatch / not_found / file_missing / error) and a summary;
exit 1 if any claim is not ok.
"""
import sys

sys.dont_write_bytecode = True
import importlib.util
import json
import re
import unicodedata
from pathlib import Path

import brse_common


def norm(s) -> str:
    return re.sub(r"\s+", " ", unicodedata.normalize("NFKC", str(s))).strip()


def converter():
    spec = importlib.util.spec_from_file_location("kb", brse_common.ROOT / "scripts" / "kb-ingest.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.convert


def check(claim: dict, root: Path, convert) -> dict:
    out = {"claim": claim.get("claim", ""), "file": claim.get("file")}
    path = (root / claim.get("file", "")).resolve()
    if not path.is_file():
        return {**out, "status": "file_missing"}
    loc, expect = claim.get("locator") or {}, norm(claim.get("expect", ""))
    if not expect:
        return {**out, "status": "error", "detail": "no `expect` given — nothing to verify"}
    if "cell" in loc:
        import openpyxl
        sheet, cell = loc["cell"].rsplit("!", 1)
        wb = openpyxl.load_workbook(path, data_only=True)
        if sheet not in wb.sheetnames:
            return {**out, "status": "not_found", "detail": f"no sheet {sheet!r}"}
        actual = wb[sheet][cell].value
        ok = norm(actual) == expect or (expect in norm(actual))
        return {**out, "status": "ok" if ok else "mismatch", "actual": None if actual is None else str(actual)}
    if "line" in loc:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        n = int(loc["line"])
        if not 1 <= n <= len(lines):
            return {**out, "status": "not_found", "detail": f"file has {len(lines)} lines"}
        return {**out, "status": "ok" if expect in norm(lines[n - 1]) else "mismatch", "actual": lines[n - 1].strip()}
    chunks, _ = convert(path)
    if "part" in loc:
        chunks = [(r, t) for r, t in chunks if norm(r).startswith(norm(loc["part"]))]
        if not chunks:
            return {**out, "status": "not_found", "detail": f"no part {loc['part']!r}"}
    hits = [r for r, t in chunks if expect in norm(t)]
    return {**out, "status": "ok" if hits else "not_found", "found_in": hits}


def main() -> None:
    if len(sys.argv) < 2:
        print(__doc__, file=sys.stderr)
        sys.exit(2)
    claims = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    root, _ = brse_common.workspace(sys.argv[2] if len(sys.argv) > 2 else ".")
    root = root or Path(sys.argv[2] if len(sys.argv) > 2 else ".").resolve()
    convert = converter()
    results = []
    for c in claims:
        try:
            results.append(check(c, root, convert))
        except Exception as e:
            results.append({"claim": c.get("claim", ""), "file": c.get("file"), "status": "error",
                            "detail": f"{type(e).__name__}: {e}"})
    summary = {}
    for r in results:
        summary[r["status"]] = summary.get(r["status"], 0) + 1
    print(json.dumps({"summary": summary, "results": results}, ensure_ascii=False, indent=2))
    sys.exit(0 if summary.keys() <= {"ok"} else 1)


if __name__ == "__main__":
    main()
