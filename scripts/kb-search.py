#!/usr/bin/env python3
"""Search the workspace knowledge index built by kb-ingest.py.

Usage: kb-search.py <query> [project_dir] [--limit N]
Prints {"query", "results": [{"path", "ref", "snippet"}], "mode"}.
Finds candidates only — open the Markdown copy or the source and read the
whole part before concluding anything. Queries shorter than 3 characters
(common for Japanese words like 注文) can't use the trigram index, so they
fall back to a substring scan.
"""
import sys

sys.dont_write_bytecode = True
import json
import sqlite3

import brse_common


def snippet(text: str, query: str, width: int = 80) -> str:
    i = text.lower().find(query.lower())
    if i < 0:
        return text[:2 * width].replace("\n", " ")
    return text[max(0, i - width): i + len(query) + width].replace("\n", " ")


def main() -> None:
    args = sys.argv[1:]
    limit = 20
    if "--limit" in args:
        i = args.index("--limit")
        limit = int(args[i + 1])
        del args[i:i + 2]
    if not args:
        print("usage: kb-search.py <query> [project_dir] [--limit N]", file=sys.stderr)
        sys.exit(2)
    query = args[0]
    root, _ = brse_common.workspace(args[1] if len(args) > 1 else ".")
    db = root / ".brse" / "knowledge" / "index.sqlite" if root else None
    if db is None or not db.is_file():
        print(json.dumps({"error": "no knowledge index — run kb-ingest.py first"}))
        sys.exit(1)
    con = sqlite3.connect(db)
    if len(query) >= 3:
        mode = "fts"
        phrase = '"' + query.replace('"', '""') + '"'
        rows = con.execute("SELECT path, ref, text FROM chunks WHERE chunks MATCH ? LIMIT ?",
                           (phrase, limit)).fetchall()
    else:
        mode = "substring"
        rows = con.execute("SELECT path, ref, text FROM chunks WHERE instr(lower(text), lower(?)) > 0 LIMIT ?",
                           (query, limit)).fetchall()
    con.close()
    print(json.dumps({"query": query, "mode": mode,
                      "results": [{"path": p, "ref": r, "snippet": snippet(t, query)} for p, r, t in rows]},
                     ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
