#!/usr/bin/env python3
"""Detect a glossary term translated inconsistently within one document.

Usage: cat entries.json | check-consistency.py
Input: JSON list of {"term": str, "translation_used": str}
"""
import json
import sys
from collections import defaultdict


def check(entries: list[dict]) -> dict:
    by_term = defaultdict(list)
    for e in entries:
        if e["translation_used"] not in by_term[e["term"]]:
            by_term[e["term"]].append(e["translation_used"])
    return {term: vals for term, vals in by_term.items() if len(vals) > 1}


def main() -> None:
    data = json.load(sys.stdin)
    conflicts = check(data)
    print(json.dumps({"conflicts": conflicts, "ok": len(conflicts) == 0}, ensure_ascii=False, indent=2))
    sys.exit(1 if conflicts else 0)


if __name__ == "__main__":
    main()
