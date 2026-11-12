"""Lint a draft response for banned hedge words and unsourced bullet claims.

Usage: brse.py lint-hedge-words [file] [--source-tag FORMAT]   (reads stdin if no file)
FORMAT is the workspace's `style.source_tag` from brse.py config, e.g.
"(nguồn: {ref})" (default) or "(source: {ref})". A claim also counts as sourced
when it cites a reference inline: `path/file.ext:123` or `Sheet!A12`.
Exit 0 if clean, 1 if any violation found.
"""
import json
import re
import sys

from brse.cli import take

# "có thể" is not here: in Vietnamese specs it mostly means "is able to" ("người dùng có thể đăng nhập"),
# so a literal match flags correct sentences; a guess written with it is left to the reviewer.
HEDGE_WORDS = ["có lẽ", "chắc là", "hình như"]
DEFAULT_SOURCE_TAG = "(nguồn: {ref})"
INLINE_REF_RE = re.compile(r"[\w./-]+\.\w+:\d+|[^\s!(（]+![A-Z]{1,3}\d+")


def tag_regex(fmt: str) -> re.Pattern:
    if "{ref}" not in fmt:
        raise ValueError("source tag format must contain {ref}")
    before, after = fmt.split("{ref}", 1)
    return re.compile(re.escape(before.strip()) + r"\s*.+?" + re.escape(after.strip()))


SOURCE_TAG_RE = tag_regex(DEFAULT_SOURCE_TAG)


def has_source(text: str, tag_re: re.Pattern) -> bool:
    return bool(tag_re.search(text) or INLINE_REF_RE.search(text))
QUESTION_MARKS = ("?", "？")  # deliverables in this toolkit are sometimes
# Japanese (detail-design-jp output, jp-vi-translate's JP-target translations)
# — the full-width "？" is the real question mark there, half-width "?" alone
# would miss every JP question and misflag it as an unsourced claim.


def is_question(text: str) -> bool:
    return any(mark in text for mark in QUESTION_MARKS)


def split_sentences(text: str) -> list[str]:
    # Half-width .!? only split when followed by whitespace (avoids cutting
    # "8.5" mid-number); full-width 。！？ split immediately after — Japanese
    # prose has no space between sentences, so requiring one would leave
    # multiple JP sentences glued into a single "sentence" and never checked.
    parts = re.split(r"(?<=[.!?])\s+|(?<=[。！？])", text.strip())
    return [p for p in parts if p.strip()]


def lint_hedge_words(text: str) -> list[dict]:
    """Flag hedge words in conclusions only.

    Questions are exempt (spec mục 6.1: "không cấm khi đang hỏi lại khách") —
    a hedge word inside a question to the customer is the correct phrasing,
    not a violation.
    """
    violations = []
    for sentence in split_sentences(text):
        if is_question(sentence):
            continue
        lower = sentence.lower()
        for word in HEDGE_WORDS:
            if word in lower:
                violations.append({"type": "hedge_word", "word": word, "sentence": sentence})
    return violations


BULLET_RE = re.compile(r"^([-*]\s|\d+[.)]\s)")
STRUCTURAL_RE = re.compile(r"^([#|]|[-=*_ ]+$)")


def lint_missing_sources(text: str, tag_re: re.Pattern = SOURCE_TAG_RE) -> list[dict]:
    """Flag concluding claims with no source tag and no inline reference.

    Checks bullet/numbered list items as a whole line (original behavior),
    AND plain paragraph sentences — a claim doesn't stop being a claim just
    because it wasn't written as a bullet. Excluded: code fences, headers,
    tables, horizontal rules, questions, and sentence fragments with no
    terminal punctuation (lead-in lines like "Kết quả:" aren't claims).
    """
    missing = []
    in_code_block = False
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("```"):
            in_code_block = not in_code_block
            continue
        if in_code_block or not stripped:
            continue
        if STRUCTURAL_RE.match(stripped):
            continue
        if BULLET_RE.match(stripped):
            if not is_question(stripped) and not has_source(stripped, tag_re):
                missing.append({"type": "missing_source", "line": stripped})
            continue
        for sentence in split_sentences(stripped):
            if is_question(sentence) or not sentence.endswith((".", "!", "。", "！")):
                continue
            if not has_source(sentence, tag_re):
                missing.append({"type": "missing_source", "line": sentence})
    return missing


def main() -> None:
    args, fmt = sys.argv[1:], DEFAULT_SOURCE_TAG
    fmt = take(args, "--source-tag", fmt)
    try:
        tag_re = tag_regex(fmt)
    except ValueError as e:
        print(json.dumps({"error": str(e)}))
        sys.exit(2)
    if args:
        with open(args[0], encoding="utf-8") as f:
            text = f.read()
    else:
        text = sys.stdin.read()

    violations = lint_hedge_words(text) + lint_missing_sources(text, tag_re)
    print(json.dumps({"violations": violations, "ok": len(violations) == 0}, ensure_ascii=False, indent=2))
    sys.exit(1 if violations else 0)

