#!/usr/bin/env python3
"""Scan a source text for terms already confirmed in memory/glossary.md.

Usage: check-glossary.py <text_file> <glossary_md>
Glossary entry format: - <term> → "<translation>" — nguồn: ...
"""
import json
import re
import sys

ENTRY_RE = re.compile(r'^- (?P<term>\S+) → "(?P<translation>[^"]+)"')


def parse_glossary(path: str) -> list[tuple[str, str]]:
    entries = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            m = ENTRY_RE.match(line.strip())
            if m:
                entries.append((m.group("term"), m.group("translation")))
    return entries


def check(text: str, glossary_path: str) -> list[dict]:
    entries = parse_glossary(glossary_path)
    return [{"term": term, "translation": translation} for term, translation in entries if term in text]


def main() -> None:
    if len(sys.argv) != 3:
        print("usage: check-glossary.py <text_file> <glossary_md>", file=sys.stderr)
        sys.exit(2)
    with open(sys.argv[1], encoding="utf-8") as f:
        text = f.read()
    print(json.dumps({"matches": check(text, sys.argv[2])}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
