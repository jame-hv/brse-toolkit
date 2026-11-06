#!/usr/bin/env python3
"""Count the user's corrections by category, from .brse/memory/long/feedback-log.md.

Usage: feedback-stats.py [project_dir] [--days N]
Entry format (written by /brse-toolkit:memory-review):
  - <YYYY-MM-DD> | <category> | <correction, one line> | rule: <conventions entry or none>
Prints {"total", "by_category", "by_week", "since"}; categories outside the fixed
list are counted under "other" and reported in "unknown_categories".
"""
import sys

sys.dont_write_bytecode = True
import datetime
import json
import re
from collections import Counter
from pathlib import Path

import brse_common

CATEGORIES = ["misread-request", "did-not-read-source", "unsupported-claim", "out-of-scope",
              "ignored-feedback", "format-layout", "writing-style", "translation",
              "wrong-content", "other"]
ENTRY_RE = re.compile(r"^-\s*(\d{4}-\d{2}-\d{2})\s*\|\s*([\w-]+)\s*\|")


def stats(log: Path, days=None) -> dict:
    since = datetime.date.today() - datetime.timedelta(days=days) if days else None
    by_cat, by_week, unknown = Counter(), Counter(), set()
    if log.is_file():
        for line in log.read_text(encoding="utf-8").splitlines():
            m = ENTRY_RE.match(line.strip())
            if not m:
                continue
            day = datetime.date.fromisoformat(m.group(1))
            if since and day < since:
                continue
            cat = m.group(2)
            if cat not in CATEGORIES:
                unknown.add(cat)
                cat = "other"
            by_cat[cat] += 1
            y, w, _ = day.isocalendar()
            by_week[f"{y}-W{w:02d}"] += 1
    return {"total": sum(by_cat.values()), "by_category": dict(by_cat.most_common()),
            "by_week": dict(sorted(by_week.items())), "since": str(since) if since else None,
            "unknown_categories": sorted(unknown)}


def main() -> None:
    args = sys.argv[1:]
    days = None
    if "--days" in args:
        i = args.index("--days")
        days = int(args[i + 1])
        del args[i:i + 2]
    root, _ = brse_common.workspace(args[0] if args else ".")
    if root is None:
        print(json.dumps({"error": "not inside a brse-toolkit workspace"}))
        sys.exit(1)
    print(json.dumps(stats(root / ".brse" / "memory" / "long" / "feedback-log.md", days), indent=2))


if __name__ == "__main__":
    main()
