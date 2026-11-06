#!/usr/bin/env python3
"""Score work against a fixed rubric by an independent reviewer, with pass thresholds.

Usage:
  judge.py run <request_file> <work_file> [<sources_file>] [--project DIR]
      builds the rubric prompt (config/rubric.md), asks a second agent (ask-agent.py
      order), parses its JSON verdict. No second agent → prints {"provider": "none",
      "prompt_file": ...}: give that prompt to a context-free reviewer subagent, save
      its reply, then run `judge.py parse <reply_file>`.
  judge.py parse <reply_file> [--project DIR]
      validates a reviewer's JSON reply and applies the thresholds.
Thresholds: config.quality.min_scores (default correctness/evidence/scope ≥ 4,
others ≥ 3). Prints {"pass", "scores", "failed", "must_fix", "reasons", "provider"};
exit 1 when the work does not pass or the reply is unusable.
"""
import sys

sys.dont_write_bytecode = True
import importlib.util
import json
import re
import tempfile
from pathlib import Path

import brse_common

CRITERIA = ["correctness", "completeness", "logic", "evidence", "language", "scope"]
DEFAULT_MIN = {"correctness": 4, "completeness": 3, "logic": 3, "evidence": 4, "language": 3, "scope": 4}


def verdict(reply: str, config: dict) -> dict:
    m = re.search(r"\{.*\}", reply, re.S)
    if not m:
        return {"pass": False, "error": "reviewer reply contains no JSON"}
    try:
        data = json.loads(m.group(0))
    except ValueError as e:
        return {"pass": False, "error": f"reviewer JSON unreadable: {e}"}
    scores = data.get("scores", {})
    missing = [c for c in CRITERIA if not isinstance(scores.get(c), (int, float))]
    if missing:
        return {"pass": False, "error": f"reviewer gave no score for: {', '.join(missing)}"}
    mins = {**DEFAULT_MIN, **config.get("quality", {}).get("min_scores", {})}
    failed = {c: scores[c] for c in CRITERIA if scores[c] < mins[c]}
    return {"pass": not failed, "scores": scores, "failed": failed, "thresholds": mins,
            "must_fix": data.get("must_fix", []), "reasons": data.get("reasons", {})}


def main() -> None:
    args = sys.argv[1:]
    project = "."
    if "--project" in args:
        i = args.index("--project")
        project = args[i + 1]
        del args[i:i + 2]
    _, config = brse_common.workspace(project)
    if args[:1] == ["parse"] and len(args) == 2:
        out = verdict(Path(args[1]).read_text(encoding="utf-8"), config)
    elif args[:1] == ["run"] and len(args) in (3, 4):
        read = lambda p: Path(p).read_text(encoding="utf-8")
        prompt = (brse_common.ROOT / "config" / "rubric.md").read_text(encoding="utf-8") \
            .replace("{request}", read(args[1])).replace("{work}", read(args[2])) \
            .replace("{sources}", read(args[3]) if len(args) == 4 else "(none provided)")
        spec = importlib.util.spec_from_file_location("ask", brse_common.ROOT / "scripts" / "ask-agent.py")
        ask = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(ask)
        res = ask.ask(prompt, config, 600)
        if res["provider"] == "none":
            f = Path(tempfile.mkdtemp(prefix="brse-judge-")) / "rubric-prompt.md"
            f.write_text(prompt, encoding="utf-8")
            print(json.dumps({"provider": "none", "prompt_file": str(f), "tried": res["tried"],
                              "next": "run a context-free reviewer subagent on prompt_file, save its reply, "
                                      "then: judge.py parse <reply_file>"}, ensure_ascii=False, indent=2))
            sys.exit(1)
        out = {"provider": res["provider"], **verdict(res["output"], config)}
    else:
        print(__doc__, file=sys.stderr)
        sys.exit(2)
    print(json.dumps(out, ensure_ascii=False, indent=2))
    sys.exit(0 if out.get("pass") else 1)


if __name__ == "__main__":
    main()
