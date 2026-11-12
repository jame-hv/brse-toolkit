"""Check a translated Office copy unit by unit, and record the result.

Usage: brse.py translation-check <source file> <translations.json> <translated copy>
                                 --lang vi|ja|en [--source-lang ja|vi|en] [--glossary <glossary.md>]
                                 [--units <units.json>]   (only these units — a subset taken from extract)
Rules (each problem names the unit id):
  missing        a unit of the source has no translation
  number         the numbers of a unit differ (compared by value: "07" = "7", full-width = half-width)
  code           an ID / code (has a digit or "_", or is 2+ capital letters) is missing from the translation
  marker         the ⟦n⟧…⟦/n⟧ formatting markers differ from the source unit
  glossary       a confirmed glossary term is in the source unit but its confirmed translation is not
  untranslated / halfwidth-kana   errors from lang-lint, unit by unit (a .xlsx sheet name
                 written exactly is accepted: office-text never renames tabs, so a reference
                 to a tab keeps its name)
lang-lint warnings are listed but do not fail the check. --glossary defaults to the
workspace's .brse/memory/long/glossary.md. Prints {"pass", "units", "problems",
"warnings"}; exit 1 when any problem remains. The result is recorded so the Stop hook
knows this copy was checked.
"""
import json
import re
import sys
import unicodedata
from collections import Counter
from pathlib import Path

from brse import config as brse_config
from brse.cli import take
from brse.office import text as office_text
from brse.translate import glossary, lint, record

NUMBER = re.compile(r"\d+(?:[.,]\d+)?")
CODE = re.compile(r"[A-Za-z0-9_\-]*[0-9_][A-Za-z0-9_\-]*|\b[A-Z]{2,}\b")
MARKER = re.compile(r"⟦/?\d+⟧")
TARGET_FIELD = {"vi": "vi", "en": "en", "ja": "jp"}
SOURCE_FIELDS = ("jp", "en", "vi")


def numbers(s: str) -> Counter:
    return Counter(str(float(n.replace(",", "."))) if "." in n or "," in n else str(int(n))
                   for n in NUMBER.findall(unicodedata.normalize("NFKC", s)))


def codes(s: str) -> set:
    return {c for c in CODE.findall(unicodedata.normalize("NFKC", s)) if len(c) > 1 and not re.fullmatch(r"[\d\-_.]+", c)}


def check_unit(uid, src, dst, lang, source_lang, terms, keep=()) -> tuple:
    problems, warnings = [], []
    if numbers(src) != numbers(dst):
        problems.append({"id": uid, "rule": "number", "source": src, "translation": dst})
    lost = sorted(c for c in codes(src) if c not in unicodedata.normalize("NFKC", dst))
    if lost:
        problems.append({"id": uid, "rule": "code", "missing": lost})
    if sorted(MARKER.findall(src)) != sorted(MARKER.findall(dst)):
        problems.append({"id": uid, "rule": "marker", "source": src, "translation": dst})
    for t in terms:
        want = t.get(TARGET_FIELD[lang], "")
        if glossary.is_real(want) and any(glossary.is_real(t[f]) and t[f] in src for f in SOURCE_FIELDS
                                          if f != TARGET_FIELD[lang]) and want.casefold() not in dst.casefold():
            problems.append({"id": uid, "rule": "glossary", "expected": want})
    bare = MARKER.sub("", dst)
    for name in sorted(keep, key=len, reverse=True):
        bare = bare.replace(name, " ")
    for f in lint.lint(bare, lang, source_lang):
        (problems if f["severity"] == "error" else warnings).append({"id": uid, **f})
    return problems, warnings


def check(source: Path, translations: dict, lang: str, source_lang, glossary_path, only=None) -> dict:
    units, _ = office_text.EXTRACT[source.suffix.lower()](source)
    if only is not None:
        units = [u for u in units if u["id"] in only]
    terms = glossary.parse_glossary(str(glossary_path)) if glossary_path else []
    keep = set()
    if source.suffix.lower() in (".xlsx", ".xlsm"):
        from brse.office.xlsx import load_workbook
        keep = set(load_workbook(source).sheetnames)
    problems, warnings = [], []
    for u in units:
        if u["id"] not in translations:
            problems.append({"id": u["id"], "rule": "missing", "source": u["text"]})
            continue
        p, w = check_unit(u["id"], u["text"], translations[u["id"]], lang, source_lang, terms, keep)
        problems += p
        warnings += w
    return {"pass": not problems, "units": len(units), "problems": problems, "warnings": warnings}


def main() -> int:
    args = sys.argv[1:]
    lang, source_lang, gloss = take(args, "--lang"), take(args, "--source-lang"), take(args, "--glossary")
    units_file = take(args, "--units")
    only = None
    if units_file:  # a list of units, or the whole `office-text extract` output (all three trials passed that)
        data = json.loads(Path(units_file).read_text(encoding="utf-8"))
        only = {u["id"] for u in (data.get("units", []) if isinstance(data, dict) else data)}
    if len(args) != 3 or lang not in TARGET_FIELD:
        print(__doc__, file=sys.stderr)
        return 2
    source, tr_file, copy = Path(args[0]), Path(args[1]), Path(args[2])
    if gloss is None:
        root = brse_config.find_workspace(copy.resolve().parent) or brse_config.find_workspace(Path.cwd())
        default = root / ".brse" / "memory" / "long" / "glossary.md" if root else None
        gloss = default if default and default.is_file() else None
    out = check(source, json.loads(tr_file.read_text(encoding="utf-8")), lang, source_lang, gloss, only)
    record.checked(copy, out["pass"], len(out["problems"]))
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0 if out["pass"] else 1
