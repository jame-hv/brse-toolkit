#!/usr/bin/env python3
"""Scan a source text for terms already confirmed in memory/glossary.md.

Usage: check-glossary.py <text_file> <glossary_md>
Glossary entry format: - EN: <term> | VI: <term> | JP: <term> — <source note>
(EN is a reference term, not a match target — jp-vi-translate only translates
between VI and JP, so a match fires on the VI or JP form appearing in the text.)
"""
import json
import re
import sys

ENTRY_RE = re.compile(
    r'^-\s*EN:\s*(?P<en>.+?)\s*\|\s*VI:\s*(?P<vi>.+?)\s*\|\s*JP:\s*(?P<jp>.+?)'
    r'(?:\s+[—-]\s.*)?$'
)


def parse_glossary(path: str) -> list[dict]:
    """Missing glossary file → no entries yet, not an error (a project that
    hasn't run /brse-toolkit:init, or ran it but hasn't confirmed any term
    yet, must still be able to translate — just with nothing pre-confirmed)."""
    entries = []
    try:
        f = open(path, encoding="utf-8")
    except FileNotFoundError:
        return entries
    with f:
        for line in f:
            m = ENTRY_RE.match(line.strip())
            if not m:
                continue
            en, vi, jp = m.group("en"), m.group("vi"), m.group("jp")
            # The schema-example line itself ("- EN: <term> | VI: <term> |
            # JP: <term> — ...", scaffolded by /brse-toolkit:init at the top
            # of every fresh glossary.md) matches this same pattern — skip
            # placeholder angle-bracket terms so it isn't parsed as a real,
            # bogus "<term>"/"<term>" entry.
            if en.startswith("<") or vi.startswith("<") or jp.startswith("<"):
                continue
            entries.append({"en": en, "vi": vi, "jp": jp})
    return entries


def check(text: str, glossary_path: str) -> list[dict]:
    entries = parse_glossary(glossary_path)
    return [e for e in entries if e["vi"] in text or e["jp"] in text]


def main() -> None:
    if len(sys.argv) != 3:
        print("usage: check-glossary.py <text_file> <glossary_md>", file=sys.stderr)
        sys.exit(2)
    with open(sys.argv[1], encoding="utf-8") as f:
        text = f.read()
    print(json.dumps({"matches": check(text, sys.argv[2])}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
