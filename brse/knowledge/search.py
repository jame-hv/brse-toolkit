"""Search the workspace knowledge index built by brse.py kb-ingest.

Usage: brse.py kb-search <query> [project_dir] [--limit N] [--origin client|internal|delivered]
Prints {"query", "results": [{"path", "ref", "origin", "snippet"}], "mode"}.
origin: client = what the client sent (requirements), internal = our own
documents (assumptions), delivered = what we sent the client (commitments).
Finds candidates only — open the Markdown copy or the source and read the
whole part before concluding anything. Queries shorter than 3 characters
(common for Japanese words like 注文) can't use the trigram index, so they
fall back to a substring scan.
"""
import sys
import json
import sqlite3

from brse import config as brse_config
from brse.cli import take


def snippet(text: str, query: str, width: int = 80) -> str:
    i = text.lower().find(query.lower())
    if i < 0:
        return text[:2 * width].replace("\n", " ")
    return text[max(0, i - width): i + len(query) + width].replace("\n", " ")


def search(db, query: str, limit: int = 20, origin=None):
    """(mode, [{"path", "ref", "origin", "snippet"}]) from the knowledge index at `db`."""
    con = sqlite3.connect(db)
    try:
        if len(query) >= 3:
            mode = "fts"
            phrase = '"' + query.replace('"', '""') + '"'
            rows = con.execute("SELECT path, ref, text, origin FROM chunks WHERE chunks MATCH ? "
                               "AND (? IS NULL OR origin = ?) LIMIT ?", (phrase, origin, origin, limit)).fetchall()
        else:
            mode = "substring"
            rows = con.execute("SELECT path, ref, text, origin FROM chunks WHERE instr(lower(text), lower(?)) > 0 "
                               "AND (? IS NULL OR origin = ?) LIMIT ?", (query, origin, origin, limit)).fetchall()
    finally:
        con.close()
    return mode, [{"path": p, "ref": r, "origin": o, "snippet": snippet(t, query)} for p, r, t, o in rows]


def main() -> None:
    args = sys.argv[1:]
    limit, origin = 20, None
    origin = take(args, "--origin", origin)
    limit = int(take(args, "--limit", limit))
    if not args:
        print("usage: brse.py kb-search <query> [project_dir] [--limit N]", file=sys.stderr)
        sys.exit(2)
    query = args[0]
    root, _ = brse_config.workspace(args[1] if len(args) > 1 else ".")
    db = root / ".brse" / "knowledge" / "index.sqlite" if root else None
    if db is None or not db.is_file():
        print(json.dumps({"error": "no knowledge index — run brse.py kb-ingest first"}))
        sys.exit(1)
    mode, results = search(db, query, limit, origin)
    print(json.dumps({"query": query, "mode": mode, "results": results}, ensure_ascii=False, indent=2))

