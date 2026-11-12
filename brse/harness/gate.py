"""The final check of a deliverable file, run on the file itself — not on text the agent copied out.

Usage:
  brse.py gate check <file> [--original <file>] [--kind estimate-cell|text] [--reader "..."] [--lang vi|ja|en]
      Reads every unit (cell / paragraph / slide paragraph / diagram label) from <file>. With
      --original only the units that differ from it are reviewed; without, all of them.
      Units already reviewed with the same text are not reviewed again. Asks a second model
      (review.second_agent); none → writes a prompt and tells you to dispatch the plugin's
      wording-reviewer agent on it — its answer is captured by the plugin's hook, never typed
      in by you. Every issue must be resolved; when none is open and every unit's current text
      has been reviewed, the file's hash is stamped. Changing the file afterwards voids the stamp.
  brse.py gate resolve <file> <issue-id> fixed|rejected [--reason "..."]
      fixed → the next `check` confirms that unit's text changed, then reviews it again;
      rejected → needs --reason, shown to the user in the summary.
  brse.py gate status            stamped / not stamped, for the files checked in this workspace
Exit 0 only when the file is stamped.
"""
import hashlib
import json
import re
import sys
import time
from pathlib import Path

from brse import config as brse_config
from brse.cli import take

OFFICE = {".xlsx", ".xlsm", ".docx", ".pptx", ".drawio"}
TYPES = {"unclear", "ambiguous", "literal-translation", "mismatch", "translated-feel", "abbreviation",
         "wrong-term", "unnatural", "vague", "invented", "not-applied"}
MARK = "BRSE-GATE"


class Fail(Exception):
    pass


def sha(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def gate_dir(root: Path) -> Path:
    return root / ".brse" / "gate"


def state_path(root: Path, file: Path) -> Path:
    return gate_dir(root) / (hashlib.sha1(str(file.resolve()).encode()).hexdigest()[:12] + ".json")


def load_state(root: Path, file: Path) -> dict:
    p = state_path(root, file)
    if p.is_file():
        return json.loads(p.read_text(encoding="utf-8"))
    return {"file": str(file.resolve()), "reviewed": {}, "issues": [], "stamp": None}


def save_state(root: Path, file: Path, st: dict) -> None:
    p = state_path(root, file)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(st, ensure_ascii=False, indent=1), encoding="utf-8")


def units(path: Path) -> dict:
    """{unit id: {"text", "beside"}} read from the file."""
    ext = path.suffix.lower()
    if ext == ".drawio":
        from brse.diagram import drawio as dt
        return {c.get("id"): {"text": dt.label(c), "beside": None} for c in dt.cells(dt.load(path)) if dt.label(c)}
    from brse.office.text import EXTRACT
    out = {}
    for u in EXTRACT[ext](path)[0]:
        ctx = u.get("context") or {}
        beside = {k: ctx[k] for k in ("left", "above", "heading", "slide") if ctx.get(k)} or None
        out[u["id"]] = {"text": u["text"], "beside": beside}
    return out


def session_requests(root: Path) -> list:
    """The user's messages in the current session, verbatim (session file written by the hooks)."""
    cur = root / ".brse" / "runs" / "current.json"
    try:
        t = Path(json.loads(cur.read_text(encoding="utf-8"))["transcript_path"])
        from brse.project import memory_log
        return memory_log.parse(t)[0][-40:]
    except (OSError, ValueError, KeyError, TypeError):
        return []


def memory_text(root: Path, name: str, only_entries=False) -> str:
    p = root / ".brse" / "memory" / "long" / name
    if not p.is_file():
        return "(none yet)"
    text = p.read_text(encoding="utf-8")
    if only_entries:
        text = "\n".join(l for l in text.splitlines() if l.lstrip().startswith("- "))
    return text.strip() or "(none yet)"


TERM = re.compile(r"[\u30a0-\u30ff\u4e00-\u9fff\u3005ー]{3,}")


def documents(root: Path, text: str, limit: int = 3) -> list:
    """Passages of the client's documents that mention the screen / function names in `text`: the reviewer
    needs them to see what a short cell refers to (design spec 2026-11-12, section 5.3)."""
    db = root / ".brse" / "knowledge" / "index.sqlite"
    if not db.is_file() or not text:
        return []
    from brse.knowledge.search import search
    out, seen = [], set()
    for term in sorted(set(TERM.findall(text)), key=len, reverse=True):
        for hit in search(db, term, 5)[1]:
            key = (hit["path"], hit["ref"])
            if key not in seen:
                seen.add(key)
                out.append(f'{hit["path"]} ({hit["ref"]}): {hit["snippet"]}')
            if len(out) >= limit:
                return out
    return out


def build_prompt(root: Path, todo: dict, before: dict, kind: str, reader: str, lang: str, history=()) -> str:
    kinds = json.loads((brse_config.PLUGIN_ROOT / "config" / "deliverable-kinds.json").read_text(encoding="utf-8"))
    k = kinds.get(kind) or kinds["text"]
    blocks = []
    for uid, u in todo.items():
        lines = [f"[{uid}]"]
        if u["beside"]:
            lines.append("beside: " + json.dumps(u["beside"], ensure_ascii=False))
        if uid in before:
            lines.append("before: " + before[uid])
        source_text = " ".join(str(v) for v in (u["beside"] or {}).values()) + " " + u["text"]
        for d in documents(root, source_text):
            lines.append("document: " + d)
        for i in (i for i in history if i["unit"] == uid):
            lines.append(f"earlier review: {i['type']} — {i['problem']} → answered {i['status']}"
                         + (f" ({i['reason']})" if i.get("reason") else "") + f"; text then: {i['text_at_review']}")
        lines.append("now: " + u["text"])
        blocks.append("\n".join(lines))
    reqs = session_requests(root)
    fill = {"{reader}": reader or k["reader"], "{lang}": lang, "{kind}": kind,
            "{kind_rules}": "\n".join(f"- {r}" for r in k["rules"]),
            "{requests}": "\n".join(f"- {r}" for r in reqs) or "(not available)",
            "{feedback}": memory_text(root, "feedback-log.md", only_entries=True),
            "{conventions}": memory_text(root, "conventions.md"),
            "{glossary}": memory_text(root, "glossary.md"),
            "{units}": "\n\n".join(blocks)}
    prompt = (brse_config.PLUGIN_ROOT / "config" / "gate-review.md").read_text(encoding="utf-8")
    for a, b in fill.items():
        prompt = prompt.replace(a, b)
    return prompt


def parse_issues(reply: str, todo: dict) -> list:
    from brse.review.reply import json_object
    issues = json_object(reply).get("issues")
    if not isinstance(issues, list):
        raise Fail("reviewer reply has no 'issues' list")
    good = [i for i in issues if isinstance(i, dict) and i.get("unit") in todo and i.get("type") in TYPES
            and i.get("problem") and i.get("rewrite")]
    if len(good) != len(issues):
        raise Fail(f"reviewer reply has {len(issues) - len(good)} malformed issue(s) "
                   "(unknown unit, unknown type, or no problem / rewrite) — run the review again")
    return good


STYLE = {"unnatural", "translated-feel"}


def record(st: dict, reply: str, texts: dict) -> None:
    """Add the reviewer's issues for the texts it saw; those texts count as reviewed.
    A style-only issue on a unit already changed for an earlier issue is advice, not a blocker: a reviewer
    can reverse its own style rewrites round after round (remove a word, then ask for it back) and the gate
    would never converge. Meaning problems always block."""
    found = parse_issues(reply, texts)
    n = len(st["issues"])
    for j, i in enumerate(found, 1):
        changed_before = any(p["unit"] == i["unit"] and p["status"] in ("closed", "fixed") for p in st["issues"])
        st["issues"].append({"id": f"I{n + j}", "unit": i["unit"], "type": i["type"], "problem": i["problem"],
                             "rewrite": i["rewrite"], "text_at_review": texts[i["unit"]], "status": "open",
                             "blocking": not (i["type"] in STYLE and changed_before)})
    st["reviewed"].update(texts)


def files_of(root: Path, file: Path):
    key = state_path(root, file).stem
    return (gate_dir(root) / f"{key}.prompt.md", gate_dir(root) / f"{key}.pending.json",
            gate_dir(root) / f"{key}.reply.json")


def consume(root: Path, file: Path, st: dict) -> None:
    """A reply captured from the wording-reviewer is recorded against the texts it was given, even when
    the file was edited before this check ran."""
    _, pending, reply = files_of(root, file)
    if not (pending.is_file() and reply.is_file()):
        return
    p, r = (json.loads(f.read_text(encoding="utf-8")) for f in (pending, reply))
    if p.get("prompt_sha") != r.get("prompt_sha"):
        return
    pending.unlink()
    reply.unlink()
    st["provider"] = "claude-subagent (not model-independent)"
    record(st, r["reply"], p["texts"])


def ask_review(root: Path, file: Path, st: dict, prompt: str, texts: dict, config: dict) -> bool:
    """True when the review is recorded now (second model); False when the wording-reviewer must run."""
    from brse.review import agents
    res = agents.ask(prompt, config, 600)
    if res["provider"] != "none":
        st["provider"] = res["provider"]
        record(st, res["output"], texts)
        return True
    pfile, pending, _ = files_of(root, file)
    pfile.parent.mkdir(parents=True, exist_ok=True)
    pfile.write_text(prompt, encoding="utf-8")
    pending.write_text(json.dumps({"prompt_sha": hashlib.sha256(prompt.encode()).hexdigest(), "texts": texts},
                                  ensure_ascii=False), encoding="utf-8")
    return False


def capture(prompt_text: str, reply_text: str, cwd: str) -> bool:
    """Called by the PostToolUse hook of the Agent tool: store the wording-reviewer's reply for `gate check`."""
    i = prompt_text.find(MARK + " ")
    if i < 0:
        return False
    pfile = Path(prompt_text[i + len(MARK) + 1:].split()[0])
    if not (pfile.name.endswith(".prompt.md") and pfile.parent.name == "gate" and pfile.is_file()):
        return False
    phash = hashlib.sha256(pfile.read_text(encoding="utf-8").encode()).hexdigest()
    rfile = pfile.with_name(pfile.name.replace(".prompt.md", ".reply.json"))
    rfile.write_text(json.dumps({"prompt_sha": phash, "reply": reply_text, "at": time.time()}, ensure_ascii=False),
                     encoding="utf-8")
    return True


def check(root: Path, file: Path, original, kind: str, reader: str, lang: str, config: dict) -> dict:
    now = units(file)
    before = {k: v["text"] for k, v in units(original).items()} if original else {}
    scope = [k for k in now if not original or before.get(k) != now[k]["text"]]
    st = load_state(root, file)
    st.update({"original": str(original) if original else None, "kind": kind})
    try:
        consume(root, file, st)
    except (Fail, ValueError) as e:
        save_state(root, file, st)
        return {"pass": False, "file": str(file), "error": str(e)}
    for i in st["issues"]:
        cur = now.get(i["unit"], {}).get("text")
        if i["status"] in ("open", "fixed") and cur != i["text_at_review"]:
            i["status"] = "closed"  # the unit was changed after the issue; its new text is reviewed again
        elif i["status"] == "fixed":
            i["status"], i["note"] = "open", "marked fixed but the unit's text did not change"
    todo = {k: now[k] for k in scope if st["reviewed"].get(k) != now[k]["text"]}
    if todo:
        texts = {k: u["text"] for k, u in todo.items()}
        prompt = build_prompt(root, todo, before, kind, reader, lang, st["issues"])
        try:
            done = ask_review(root, file, st, prompt, texts, config)
        except (Fail, ValueError) as e:
            save_state(root, file, st)
            return {"pass": False, "file": str(file), "error": str(e)}
        if not done:
            st["stamp"] = None
            save_state(root, file, st)
            return {"pass": False, "file": str(file), "to_review": len(todo),
                    "next": (f"Dispatch the plugin's wording-reviewer agent (subagent_type "
                             f"'brse-toolkit:wording-reviewer') with exactly this prompt: "
                             f"\"{MARK} {files_of(root, file)[0]}\" — then run this gate check again BEFORE "
                             "changing the file, so its issues are recorded. Its answer is captured by the "
                             "plugin; do not write the reply yourself.")}
    open_ = [i for i in st["issues"] if i["status"] == "open" and i.get("blocking", True)]
    advice = [i for i in st["issues"] if i["status"] == "open" and not i.get("blocking", True)]
    unreviewed = [k for k in scope if st["reviewed"].get(k) != now[k]["text"]]
    from brse.harness import flow
    steps = flow.blocks_stamp(root, file)
    passed = not open_ and not unreviewed and not steps
    st["stamp"] = sha(file) if passed else None
    save_state(root, file, st)
    out = {"pass": passed, "file": str(file), "units_in_scope": len(scope), "provider": st.get("provider")}
    show = lambda i: {k: i[k] for k in ("id", "unit", "type", "problem", "rewrite")} | (
        {"note": i["note"]} if i.get("note") else {})
    if open_:
        out["open_issues"] = [show(i) for i in open_]
        out["next"] = ("For each issue: change the unit in the file (the next check sees the change and reviews "
                       "the new text), or `brse.py gate resolve <file> <id> rejected --reason \"...\"` when the "
                       "issue is wrong; then run this gate check again.")
    if advice:
        out["advice"] = [show(i) for i in advice]
    if steps:
        out["estimate_steps_missing"] = steps
        out.setdefault("next", "The estimate run is not complete (`brse.py run status`): " + "; ".join(steps.values()))
    if passed:
        out["summary"] = summary(st, len(scope))
    return out


def summary(st: dict, n: int) -> str:
    fixed = [i for i in st["issues"] if i["status"] == "closed"]
    rejected = [i for i in st["issues"] if i["status"] == "rejected"]
    advice = [i for i in st["issues"] if i["status"] == "open" and not i.get("blocking", True)]
    lines = [f"Gate passed: {Path(st['file']).name} — {n} unit(s) reviewed on the file itself "
             f"({st.get('provider') or 'no new review needed'}); {len(fixed)} issue(s) fixed, {len(rejected)} rejected."]
    lines += [f"- rejected {i['id']} {i['unit']} ({i['type']}): {i['problem']} — reason: {i['reason']}" for i in rejected]
    lines += [f"- style advice not applied {i['id']} {i['unit']}: {i['problem']}" for i in advice]
    return "\n".join(lines)


def resolve(root: Path, file: Path, issue: str, how: str, reason) -> dict:
    st = load_state(root, file)
    hit = [i for i in st["issues"] if i["id"] == issue]
    if not hit:
        raise Fail(f"no issue {issue} for {file}")
    if how not in ("fixed", "rejected"):
        raise Fail("resolution must be 'fixed' or 'rejected'")
    if how == "rejected" and not (reason or "").strip():
        raise Fail("a rejected issue needs --reason")
    hit[0]["status"], hit[0]["reason"] = how, reason
    st["stamp"] = None
    save_state(root, file, st)
    return {"ok": True, "issue": issue, "status": how}


def unstamped(root: Path, since: float, config: dict) -> list:
    """Deliverable files changed in this session without a valid stamp: every Office / draw.io file in the
    workspace modified at or after `since`, except the client's sources and templates and .brse itself."""
    skip = [(root / p).resolve() for p in config.get("paths", {}).get("sources", []) +
            config.get("paths", {}).get("templates", [])]
    # an untouched copy of a template or source document has nothing to review (a template copied to the
    # output folder before the approval step would otherwise block the turn)
    pristine = {sha(f) for s in skip if s.is_dir() for f in s.rglob("*") if f.is_file() and f.suffix.lower() in OFFICE}
    out = []
    for p in root.rglob("*"):
        if p.suffix.lower() not in OFFICE or p.name.startswith(("~$", ".~lock")) or not p.is_file():
            continue
        rp = p.resolve()
        if any(part in (".brse", ".git", "node_modules") for part in rp.relative_to(root.resolve()).parts):
            continue
        if any(rp.is_relative_to(s) for s in skip) or p.stat().st_mtime < since:
            continue
        h = sha(p)
        if h in pristine:
            continue
        st = load_state(root, p)
        if st.get("stamp") != h:
            out.append(str(p.relative_to(root)))
    return sorted(out)


def main() -> None:
    args = sys.argv[1:]
    opts = {f: take(args, f) for f in ("--original", "--kind", "--reader", "--lang", "--reason")}
    try:
        root, config = brse_config.workspace(".")
        if not root:
            raise Fail("not inside a brse-toolkit workspace — run /brse-toolkit:init first")
        if args[:1] == ["check"] and len(args) == 2:
            f = Path(args[1])
            if f.suffix.lower() not in OFFICE or not f.is_file():
                raise Fail(f"{f}: not an existing .xlsx / .xlsm / .docx / .pptx / .drawio file")
            orig = Path(opts["--original"]) if opts["--original"] else None
            out = check(root, f, orig, opts["--kind"] or "text", opts["--reader"] or "",
                        opts["--lang"] or config.get("project", {}).get("reply_language", "vi"), config)
        elif args[:1] == ["resolve"] and len(args) == 4:
            out = resolve(root, Path(args[1]), args[2], args[3], opts["--reason"])
        elif args[:1] == ["status"]:
            out = {"files": [{"file": s["file"], "stamped": bool(s.get("stamp")) and Path(s["file"]).is_file()
                              and s["stamp"] == sha(Path(s["file"]))}
                             for s in (json.loads(p.read_text(encoding="utf-8"))
                                       for p in sorted(gate_dir(root).glob("*.json")) if "." not in p.stem)]}
        else:
            print(__doc__, file=sys.stderr)
            sys.exit(2)
    except Fail as e:
        print(json.dumps({"error": str(e)}, ensure_ascii=False))
        sys.exit(2)
    print(json.dumps(out, ensure_ascii=False, indent=2))
    sys.exit(0 if out.get("pass", out.get("ok", "files" in out)) else 1)
