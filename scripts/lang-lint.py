#!/usr/bin/env python3
"""Mechanical language checks on a translated or written text.

Usage: lang-lint.py <text_file> --lang ja|vi|en [--source-lang ja|vi|en]
errors (exit 1):
  untranslated   characters of the source script left in the target text
                 (kana/kanji in vi/en output; Vietnamese letters in ja output)
  halfwidth-kana ｱｲｳ-style half-width katakana in Japanese text
warnings:
  ja-style-mix   です/ます and だ/である sentence endings mixed in one text
  ja-width-mix   full-width and half-width Latin letters/digits mixed
  long-sentence  sentence longer than the limit (ja 120 chars, vi/en 45 words)
  repeated-word  the same word twice in a row (vi/en)
Lines inside ``` code fences and text in backticks are ignored (IDs, code).
"""
import sys

sys.dont_write_bytecode = True
import json
import re
from pathlib import Path

CJK = re.compile(r"[぀-ヿ一-鿿]+")
HALF_KANA = re.compile(r"[｡-ﾟ]+")
VI_LETTERS = re.compile(r"[ăâđêôơưĂÂĐÊÔƠƯạảấầẩẫậắằẳẵặẹẻẽếềểễệỉịọỏốồổỗộớờởỡợụủứừửữựỳỵỷỹ]")
FULL_ALNUM = re.compile(r"[Ａ-Ｚａ-ｚ０-９]")
HALF_ALNUM = re.compile(r"[A-Za-z0-9]")
POLITE = re.compile(r"(です|ます|ました|ません|でした|ください|ましょう)[。！？]?$")
PLAIN = re.compile(r"(である|だ|った|ない|する|した|いる)[。！？]?$")


def clean(text: str) -> str:
    text = re.sub(r"```.*?```", " ", text, flags=re.S)
    return re.sub(r"`[^`]*`", " ", text)


def sentences(text: str, lang: str) -> list:
    pattern = r"(?<=[。！？])|\n" if lang == "ja" else r"(?<=[.!?])\s+|\n"
    return [s.strip() for s in re.split(pattern, text) if s.strip()]


def lint(text: str, lang: str, source_lang=None) -> list:
    text = clean(text)
    findings = []
    if lang in ("vi", "en") and (source_lang == "ja" or source_lang is None):
        for m in CJK.finditer(text):
            ctx = text[max(0, m.start() - 20): m.end() + 20].replace("\n", " ")
            findings.append({"severity": "error", "rule": "untranslated", "text": m.group(0), "context": ctx})
    if lang == "ja":
        if source_lang == "vi":
            for m in VI_LETTERS.finditer(text):
                findings.append({"severity": "error", "rule": "untranslated",
                                 "context": text[max(0, m.start() - 20): m.end() + 20]})
        for m in HALF_KANA.finditer(text):
            findings.append({"severity": "error", "rule": "halfwidth-kana", "text": m.group(0)})
        sents = sentences(text, "ja")
        polite = [s for s in sents if POLITE.search(s)]
        plain = [s for s in sents if PLAIN.search(s) and not POLITE.search(s)]
        if polite and plain:
            minority = plain if len(plain) <= len(polite) else polite
            findings.append({"severity": "warning", "rule": "ja-style-mix",
                             "detail": f"{len(polite)} です/ます vs {len(plain)} だ/である endings",
                             "examples": minority[:3]})
        if FULL_ALNUM.search(text) and HALF_ALNUM.search(text):
            findings.append({"severity": "warning", "rule": "ja-width-mix",
                             "examples": sorted(set(FULL_ALNUM.findall(text)))[:10]})
        findings += [{"severity": "warning", "rule": "long-sentence", "text": s[:80] + "…"}
                     for s in sents if len(s) > 120]
    else:
        for s in sentences(text, lang):
            words = s.split()
            if len(words) > 45:
                findings.append({"severity": "warning", "rule": "long-sentence", "text": s[:80] + "…"})
            for a, b in zip(words, words[1:]):
                if a.lower() == b.lower() and a.isalpha():
                    findings.append({"severity": "warning", "rule": "repeated-word", "text": f"{a} {b}"})
    return findings


def main() -> None:
    args = sys.argv[1:]
    opts = {}
    for flag in ("--lang", "--source-lang"):
        if flag in args:
            i = args.index(flag)
            opts[flag] = args[i + 1]
            del args[i:i + 2]
    if not args or opts.get("--lang") not in ("ja", "vi", "en"):
        print(__doc__, file=sys.stderr)
        sys.exit(2)
    findings = lint(Path(args[0]).read_text(encoding="utf-8"), opts["--lang"], opts.get("--source-lang"))
    errors = [f for f in findings if f["severity"] == "error"]
    print(json.dumps({"errors": len(errors), "warnings": len(findings) - len(errors), "findings": findings},
                     ensure_ascii=False, indent=2))
    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
