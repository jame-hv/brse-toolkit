"""Single entry point: `scripts/brse.py <command> [args]`.

Each command is a module's `main()` that reads sys.argv[1:] and prints JSON.
Modules are imported only when their command runs, so `config` and `doctor`
work on a machine without openpyxl / python-docx / python-pptx.
"""
import importlib
import json
import sys

# command name -> "module:function"
COMMANDS = {
    "config": "brse.config:main",
    "office": "brse.office.render:main",
    "office-text": "brse.office.text:main",
    "office-diff": "brse.office.diff:main",
    "extract-cells": "brse.office.xlsx:cells_main",
    "extract-images": "brse.office.xlsx:images_main",
    "kb-ingest": "brse.knowledge.ingest:main",
    "kb-search": "brse.knowledge.search:main",
    "doc2md": "brse.knowledge.doc2md:main",
    "ask-agent": "brse.review.agents:main",
    "judge": "brse.review.judge:main",
    "wording": "brse.review.wording:main",
    "verify-claims": "brse.review.claims:main",
    "lint-hedge-words": "brse.review.hedge:main",
    "drawio-tool": "brse.diagram.drawio:main",
    "hook": "brse.hooks:main",
    "gate": "brse.harness.gate:main",
    "run": "brse.harness.flow:main",
    "init": "brse.project.init:main",
    "register": "brse.project.register:main",
    "feedback-stats": "brse.project.feedback:main",
    "library": "brse.project.library:main",
    "set-key": "brse.project.keys:main",
    "doctor": "brse.project.doctor:main",
    "mt": "brse.translate.mt:main",
    "translation-check": "brse.translate.check:main",
    "lang-lint": "brse.translate.lint:main",
    "check-glossary": "brse.translate.glossary:main",
    "check-consistency": "brse.translate.consistency:main",
    "extract-refs": "brse.code.refs:main",
    "diff-structured": "brse.code.structured_diff:main",
    "ocr-pass": "brse.code.ocr:main",
}


def command_names() -> set:
    return set(COMMANDS)


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv or argv[0] not in COMMANDS:
        print(json.dumps({"error": f"unknown command {argv[0] if argv else '(none)'!r}",
                          "commands": sorted(COMMANDS)}, ensure_ascii=False))
        return 2
    name, rest = argv[0], argv[1:]
    module, func = COMMANDS[name].split(":")
    old = sys.argv
    sys.argv = [name, *rest]  # the command modules read their own arguments
    try:
        code = getattr(importlib.import_module(module), func)()
        return code if isinstance(code, int) else 0
    except SystemExit as e:
        return e.code if isinstance(e.code, int) else (0 if e.code is None else 1)
    finally:
        sys.argv = old


def take(args: list, flag: str, default=None):
    """Remove `flag VALUE` from args and return VALUE ("" when the value is missing); default if absent."""
    if flag not in args:
        return default
    i = args.index(flag)
    value = args[i + 1] if i + 1 < len(args) else ""
    del args[i:i + 2]
    return value
