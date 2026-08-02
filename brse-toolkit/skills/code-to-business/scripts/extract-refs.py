#!/usr/bin/env python3
"""Grep a codebase for business-domain keywords, returning exact file:line matches.

Usage: extract-refs.py <path> <keyword> [keyword2 ...]
Requires `rg` (ripgrep) on PATH.

Encoding (spec mục 6.5): legacy Japanese source/text files are often Shift-JIS
(cp932), not UTF-8 — so `rg` output is captured as raw bytes and decoded here
with a UTF-8 → cp932 → replace fallback chain instead of letting subprocess do a
strict UTF-8 decode that would crash the whole run on one legacy file.
"""
import json
import shutil
import subprocess
import sys

DECODE_CHAIN = ("utf-8", "cp932")


def decode_output(raw: bytes) -> str:
    """Decode rg output, tolerating Shift-JIS (cp932) legacy files."""
    for encoding in DECODE_CHAIN:
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="replace")


def parse_rg_output(output: str, keyword: str) -> list[dict]:
    """Parse `rg --line-number --no-heading` output into match dicts.

    Pure function — no subprocess, testable without the rg binary. A malformed
    line (no line number, unparseable line number) is skipped, not fatal.
    """
    results = []
    for line in output.splitlines():
        parts = line.split(":", 2)
        if len(parts) != 3:
            continue
        try:
            line_number = int(parts[1])
        except ValueError:
            continue
        results.append({
            "keyword": keyword,
            "file": parts[0],
            "line": line_number,
            "content": parts[2].strip(),
        })
    return results


def search(path: str, keywords: list[str]) -> tuple[list[dict], list[str]]:
    """Run rg per keyword. Returns (matches, errors).

    rg exit codes: 0 = matches found, 1 = no matches (not an error), 2+ = real
    error (bad path, bad regex, IO failure) — surfaced as an error string rather
    than silently returning zero matches.
    """
    results: list[dict] = []
    errors: list[str] = []
    for kw in keywords:
        proc = subprocess.run(
            ["rg", "--line-number", "--no-heading", "--fixed-strings", kw, path],
            capture_output=True,  # bytes, not text — see decode_output()
        )
        if proc.returncode not in (0, 1):
            stderr = decode_output(proc.stderr).strip()
            errors.append(f"rg exited {proc.returncode} for keyword {kw!r}: {stderr}")
            continue
        results.extend(parse_rg_output(decode_output(proc.stdout), kw))
    return results, errors


def main() -> None:
    if len(sys.argv) < 3:
        print("usage: extract-refs.py <path> <keyword> [keyword2 ...]", file=sys.stderr)
        sys.exit(2)
    if shutil.which("rg") is None:
        print(json.dumps({"error": "ripgrep (rg) not installed"}, ensure_ascii=False, indent=2))
        sys.exit(2)
    path, keywords = sys.argv[1], sys.argv[2:]
    matches, errors = search(path, keywords)
    payload: dict = {"matches": matches}
    if errors:
        payload["error"] = "; ".join(errors)
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
