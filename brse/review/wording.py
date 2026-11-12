"""Sentence-by-sentence wording review by a reader who did not write the text.

Usage:
  brse.py wording run <text_file | file.drawio> [--reader "<who reads it>"] [--lang vi|ja|en] [--project DIR]
      builds the prompt (config/wording-review.md) with the project's conventions and
      glossary from .brse/memory/long as the standard; a .drawio file is reviewed label
      by label. Asks a second agent (brse.py ask-agent order); none available → prints
      {"provider": "none", "prompt_file"}: run the plugin's wording-reviewer agent on it with no
      other context, save the reply, then `brse.py wording parse <reply>`.
  brse.py wording parse <reply_file>
Prints {"pass", "issues": [{text, type, problem, rewrite}], "provider"}; exit 1 while any
issue remains — fix every sentence, run again.
"""
import sys
import json
import tempfile
from pathlib import Path

from brse import config as brse_config
from brse.cli import take
from brse.review import agents
from brse.review.reply import json_object

TYPES = {"unclear", "ambiguous", "translated-feel", "abbreviation", "wrong-term", "unnatural", "vague", "invented"}


def text_of(path: Path) -> str:
    if path.suffix == ".drawio":
        from brse.diagram import drawio as dt
        labels = [dt.label(c) for c in dt.cells(dt.load(path)) if dt.label(c)]
        return "\n".join(f"- {l}" for l in labels)
    return path.read_text(encoding="utf-8")


def verdict(reply: str) -> dict:
    try:
        issues = json_object(reply).get("issues")
    except ValueError as e:
        return {"pass": False, "error": str(e)}
    if not isinstance(issues, list):
        return {"pass": False, "error": "reviewer reply has no 'issues' list"}
    bad = [i for i in issues if not (isinstance(i, dict) and i.get("text") and i.get("rewrite") and i.get("type") in TYPES)]
    if bad:
        return {"pass": False, "error": "every issue needs text, a known type and a rewrite", "malformed": bad}
    return {"pass": not issues, "issues": issues}


def main() -> None:
    args = sys.argv[1:]
    opts = {"--reader": "the user (a bridge system engineer)", "--lang": "vi", "--project": "."}
    for flag in list(opts):
        opts[flag] = take(args, flag, opts[flag])
    if args[:1] == ["parse"] and len(args) == 2:
        out = verdict(Path(args[1]).read_text(encoding="utf-8"))
    elif args[:1] == ["run"] and len(args) == 2:
        root, config = brse_config.workspace(opts["--project"])
        mem = (root / ".brse" / "memory" / "long") if root else None
        read = lambda n: (mem / n).read_text(encoding="utf-8") if mem and (mem / n).is_file() else "(none yet)"
        prompt = (brse_config.PLUGIN_ROOT / "config" / "wording-review.md").read_text(encoding="utf-8")
        for k, v in {"{reader}": opts["--reader"], "{lang}": opts["--lang"], "{conventions}": read("conventions.md"),
                     "{glossary}": read("glossary.md"), "{text}": text_of(Path(args[1]))}.items():
            prompt = prompt.replace(k, v)
        res = agents.ask(prompt, config, 600)
        if res["provider"] == "none":
            d = (root / ".brse" / "gate") if root else Path(tempfile.mkdtemp(prefix="brse-wording-"))
            d.mkdir(parents=True, exist_ok=True)  # inside the workspace (git-ignored), not scattered in /tmp
            f = d / "wording-prompt.md"
            f.write_text(prompt, encoding="utf-8")
            print(json.dumps({"provider": "none", "prompt_file": str(f), "tried": res["tried"],
                              "next": "run the plugin's wording-reviewer agent on prompt_file with no other context, "
                                      "save its reply, then: brse.py wording parse <reply_file>"}, ensure_ascii=False, indent=2))
            sys.exit(1)
        out = {"provider": res["provider"], **verdict(res["output"])}
    else:
        print(__doc__, file=sys.stderr)
        sys.exit(2)
    print(json.dumps(out, ensure_ascii=False, indent=2))
    sys.exit(0 if out.get("pass") else 1)

