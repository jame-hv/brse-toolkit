#!/usr/bin/env python3
"""Grep a codebase for business-domain keywords, returning exact file:line matches.

Usage: extract-refs.py <path> <keyword> [keyword2 ...]
Requires `rg` (ripgrep) on PATH.
"""
import json
import subprocess
import sys


def search(path: str, keywords: list[str]) -> list[dict]:
    results = []
    for kw in keywords:
        proc = subprocess.run(
            ["rg", "--line-number", "--no-heading", "--fixed-strings", kw, path],
            capture_output=True, text=True,
        )
        for line in proc.stdout.splitlines():
            parts = line.split(":", 2)
            if len(parts) == 3:
                results.append({
                    "keyword": kw,
                    "file": parts[0],
                    "line": int(parts[1]),
                    "content": parts[2].strip(),
                })
    return results


def main() -> None:
    if len(sys.argv) < 3:
        print("usage: extract-refs.py <path> <keyword> [keyword2 ...]", file=sys.stderr)
        sys.exit(2)
    path, keywords = sys.argv[1], sys.argv[2:]
    print(json.dumps({"matches": search(path, keywords)}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
