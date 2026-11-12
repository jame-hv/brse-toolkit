"""Score work against a fixed rubric by an independent reviewer, with pass thresholds.

Usage:
  brse.py judge run <request_file> <work_file> [<sources_file>] [--project DIR]
      builds the rubric prompt (config/rubric.md), asks a second agent (brse.py ask-agent
      order), parses its JSON verdict. No second agent → prints the prompt to dispatch the
      plugin's `reviewer` agent with ("BRSE-GATE <prompt file>"); its answer is captured by
      the plugin's hook. Run the same `judge run` again to get the verdict. A reply you
      write yourself is never accepted.
  brse.py judge parse <reply_file> [--project DIR]
      validates a saved reply from a second model and applies the thresholds (reported as
      "provider": "file" — not a review of record).
Thresholds: config.quality.min_scores (default correctness/evidence/scope/reader ≥ 4,
others ≥ 3). Prints {"pass", "scores", "failed", "must_fix", "reasons", "provider"};
exit 1 when the work does not pass or the reply is unusable.
"""
import sys
import json
import tempfile
from pathlib import Path

from brse import config as brse_config
from brse.cli import take
from brse.review.reply import json_object

CRITERIA = ["correctness", "completeness", "logic", "evidence", "language", "scope", "reader"]
DEFAULT_MIN = {"correctness": 4, "completeness": 3, "logic": 3, "evidence": 4, "language": 3, "scope": 4, "reader": 4}


def verdict(reply: str, config: dict) -> dict:
    try:
        data = json_object(reply)
    except ValueError as e:
        return {"pass": False, "error": str(e)}
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
    project = take(args, "--project", ".")
    _, config = brse_config.workspace(project)
    if args[:1] == ["parse"] and len(args) == 2:
        out = {"provider": "file", **verdict(Path(args[1]).read_text(encoding="utf-8"), config)}
    elif args[:1] == ["run"] and len(args) in (3, 4):
        read = lambda p: Path(p).read_text(encoding="utf-8")
        prompt = (brse_config.PLUGIN_ROOT / "config" / "rubric.md").read_text(encoding="utf-8") \
            .replace("{request}", read(args[1])).replace("{work}", read(args[2])) \
            .replace("{sources}", read(args[3]) if len(args) == 4 else "(none provided)")
        from brse.review import agents as ask
        res = ask.ask(prompt, config, 600)
        if res["provider"] == "none":
            import hashlib
            root = brse_config.find_workspace(Path(project).resolve())
            d = (root / ".brse" / "gate") if root else Path(tempfile.mkdtemp(prefix="brse-judge-")) / "gate"
            d.mkdir(parents=True, exist_ok=True)
            sha = hashlib.sha256(prompt.encode()).hexdigest()
            f, reply = d / f"judge-{sha[:12]}.prompt.md", d / f"judge-{sha[:12]}.reply.json"
            if reply.is_file() and json.loads(reply.read_text(encoding="utf-8")).get("prompt_sha") == sha:
                out = {"provider": "claude-subagent (not model-independent)",
                       **verdict(json.loads(reply.read_text(encoding="utf-8"))["reply"], config)}
            else:
                f.write_text(prompt, encoding="utf-8")
                print(json.dumps({"provider": "none", "tried": res["tried"],
                                  "next": f"Dispatch the plugin's reviewer agent (subagent_type 'brse-toolkit:reviewer') "
                                          f"with exactly this prompt: \"BRSE-GATE {f}\" — then run this same judge run "
                                          "again. Its answer is captured by the plugin; do not write it yourself."},
                                 ensure_ascii=False, indent=2))
                sys.exit(1)
        else:
            out = {"provider": res["provider"], **verdict(res["output"], config)}
    else:
        print(__doc__, file=sys.stderr)
        sys.exit(2)
    print(json.dumps(out, ensure_ascii=False, indent=2))
    sys.exit(0 if out.get("pass") else 1)

