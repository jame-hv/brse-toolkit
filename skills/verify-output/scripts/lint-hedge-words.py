#!/usr/bin/env python3
"""Lint a draft response for banned hedge words and unsourced bullet claims.

Usage: lint-hedge-words.py [file]   (reads stdin if no file given)
Exit 0 if clean, 1 if any violation found.
"""
import json
import re
import sys

HEDGE_WORDS = ["có lẽ", "chắc là", "hình như", "có thể"]
SOURCE_TAG_RE = re.compile(r"\(nguồn:[^)]*\)")


def split_sentences(text: str) -> list[str]:
    parts = re.split(r"(?<=[.!?])\s+", text.strip())
    return [p for p in parts if p.strip()]


def lint_hedge_words(text: str) -> list[dict]:
    """Flag hedge words in conclusions only.

    Questions are exempt (spec mục 6.1: "không cấm khi đang hỏi lại khách") —
    a hedge word inside a question to the customer is the correct phrasing,
    not a violation.
    """
    violations = []
    for sentence in split_sentences(text):
        if "?" in sentence:
            continue
        lower = sentence.lower()
        for word in HEDGE_WORDS:
            if word in lower:
                violations.append({"type": "hedge_word", "word": word, "sentence": sentence})
    return violations


def lint_missing_sources(text: str) -> list[dict]:
    missing = []
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("- ") and "?" not in stripped:
            if not SOURCE_TAG_RE.search(stripped):
                missing.append({"type": "missing_source", "line": stripped})
    return missing


def main() -> None:
    if len(sys.argv) > 1:
        with open(sys.argv[1], encoding="utf-8") as f:
            text = f.read()
    else:
        text = sys.stdin.read()

    violations = lint_hedge_words(text) + lint_missing_sources(text)
    print(json.dumps({"violations": violations, "ok": len(violations) == 0}, ensure_ascii=False, indent=2))
    sys.exit(1 if violations else 0)


if __name__ == "__main__":
    main()
