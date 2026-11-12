"""Scan a source text for terms already confirmed in memory/glossary.md.

Usage: brse.py check-glossary <text_file> <glossary_md>
Glossary entry format: - EN: <term> | VI: <term> | JP: <term> — <source note>
A match fires on any of the EN/VI/JP forms appearing in the text (EN as a whole
word, case-insensitive). Empty or placeholder cells ("—", "-", "n/a") never match.
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


PLACEHOLDERS = {"", "—", "-", "–", "n/a", "na", "?"}


def is_real(term: str) -> bool:
    return term.strip().lower() not in PLACEHOLDERS


def matches(entry: dict, text: str) -> bool:
    if is_real(entry["vi"]) and entry["vi"] in text:
        return True
    if is_real(entry["jp"]) and entry["jp"] in text:
        return True
    en = entry["en"]
    return is_real(en) and re.search(rf"(?<!\w){re.escape(en)}(?!\w)", text, re.I) is not None


def check(text: str, glossary_path: str) -> list[dict]:
    return [e for e in parse_glossary(glossary_path) if matches(e, text)]


def main() -> None:
    if len(sys.argv) != 3:
        print("usage: brse.py check-glossary <text_file> <glossary_md>", file=sys.stderr)
        sys.exit(2)
    with open(sys.argv[1], encoding="utf-8") as f:
        text = f.read()
    print(json.dumps({"matches": check(text, sys.argv[2])}, ensure_ascii=False, indent=2))

