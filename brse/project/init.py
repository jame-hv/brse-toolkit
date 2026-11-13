"""Set up a brse-toolkit workspace in a folder without asking: everything is inferred from the folder,
the user corrects what is wrong afterwards with the same command.

Usage: brse.py init [folder] [--name N] [--sources a/,b/] [--templates t/] [--client-language ja|vi|en]
                    [--reply-language vi|ja|en] [--force]
Inferred (each flag overrides):
  name             the folder's name
  sources          top-level folders holding documents (.xlsx .docx .pptx .pdf .md .txt .csv ...), except
                   template / output / work folders
  templates        top-level folders whose name says template (template, テンプレ, 雛形, 様式, mẫu)
  internal         folders named internal / 社内 / 内部 / nội bộ (our own documents)
  deliverables     folders named deliver / 納品 / 提出 / 送付 (what was sent to the client)
  client language  ja when the documents' names contain Japanese, en when they are plain ASCII, else the default
Creates .brse/ (config.json with only what differs from the defaults, memory/long files holding only their
schema, memory/short, knowledge, registers, .gitignore), the brse-toolkit block of CLAUDE.md (the
user's own text outside the markers is kept) and a git repository when there is none.
An existing workspace is left alone unless --force (memory, knowledge and registers are never touched).
Prints {"created", "inferred": {what: {"value", "from"}}, "workspace"}.
"""
import json
import re
import subprocess
import sys
from pathlib import Path

from brse import config as brse_config
from brse.cli import take

DOCS = {".xlsx", ".xlsm", ".xls", ".docx", ".doc", ".pptx", ".ppt", ".pdf", ".md", ".txt", ".csv", ".eml", ".msg"}
SKIP = {".brse", ".git", ".claude", "node_modules", ".venv", "venv", "__pycache__"}
TEMPLATE = re.compile(r"(?i)template|テンプレ|雛形|ひな形|様式|mẫu|mau")
INTERNAL = re.compile(r"(?i)internal|社内|内部|nội ?bộ|noi ?bo")
DELIVERED = re.compile(r"(?i)deliver|納品|提出|送付|đã ?gửi")
NOT_SOURCE = re.compile(r"(?i)^(out|output|outputs|work|tmp|temp|build|dist)$")
JAPANESE = re.compile(r"[぀-ヿ一-鿿]")

MEMORY = {
    "parties.md": "# Parties — who is who in this project\n\nEntry schema:\n- <Party name> — role: <client/vendor/our team/...> — form of address: <confirmed form, or \"not confirmed\">\n  — source: <where this was confirmed>, <date> — status: active\n",
    "glossary.md": "# Glossary EN-VI-JP\n\nEntry schema:\n- EN: <term> | VI: <term> | JP: <term> — <source note>, <date> — status: active\n",
    "conventions.md": "# Conventions — formatting and writing conventions confirmed for this project\n\nEntry schema:\n- <what> → <confirmed meaning or rule> — source: <file or message>, <date> — status: active\n",
    "decisions-log.md": "# Decisions log — overlay on top of the official spec/design\n\nEntry schema:\n- Decision: <content, with its scope stated>\n  Source: <QA id / message / meeting>, <date>\n  Status in the official doc: <FULLY updated / PARTIALLY updated / NOT YET updated>\n  Status: active\n",
    "deliverables-log.md": "# Deliverables log\n\nEntry schema:\n- <YYYY-MM-DD> | <file name> | <version> | sent to: <party> | <what it answers / contains>\n",
    "feedback-log.md": "<!-- last-review: never -->\n# Feedback log — corrections the user gave, by category\n\nEntry schema:\n- <YYYY-MM-DD> | <category> | <correction, one line> | rule: <conventions entry it produced, or none>\nCategories: misread-request, did-not-read-source, unsupported-claim, out-of-scope,\nignored-feedback, format-layout, writing-style, translation, wrong-content, other\n",
}

BLOCK = """<!-- brse-toolkit:start -->
# {name}

Client documents: {sources} ({client_language}) · Templates: {templates} · Reply to the user in: {reply_language}
Settled facts: `.brse/memory/long/` (parties, glossary, conventions, decisions-log, feedback-log) — read before any work.
Searchable copies of the documents: `.brse/knowledge/docs/` (refresh with `/brse-toolkit:ingest`).

## Enforced by the plugin
- Every Office / draw.io file changed in a session must pass `brse.py gate check <file> [--original <file>]`
  before the turn can end.
- An estimate goes through `brse.py run start estimate --file <copy>` and `brse.py run status`.
- The client's documents ({sources}) are never written; work on a copy.

## Rules
1. Answer what was asked, first. A correction from the user is applied at once and reported — never asked back.
2. Every conclusion cites file + sheet/cell, page or file:line; no source → say it is unconfirmed.
3. Keep the document's own term with its location; separate "the document says" from "my reading"; never
   invent example data.
4. No abbreviations in text written for people (estimate cells may use abbreviations in the glossary);
   numbers with their basis.
5. Do only what was asked; anything extra → propose it.
6. When the user confirms a term, convention, party or decision, write it to `.brse/memory/long/` with
   source and date.
7. Nothing from this project goes into another repository or any public place.
<!-- brse-toolkit:end -->"""


def scan(root: Path) -> dict:
    found = {"sources": [], "templates": [], "internal": [], "deliverables": [], "names": []}
    for d in sorted(p for p in root.iterdir() if p.is_dir() and p.name not in SKIP):
        files = [f for f in d.rglob("*") if f.is_file() and f.suffix.lower() in DOCS
                 and not any(part in SKIP for part in f.relative_to(root).parts)]
        if not files:
            continue
        if TEMPLATE.search(d.name):
            found["templates"].append(d.name + "/")
        elif INTERNAL.search(d.name):
            found["internal"].append(d.name + "/")
        elif DELIVERED.search(d.name):
            found["deliverables"].append(d.name + "/")
        elif not NOT_SOURCE.match(d.name):
            found["sources"].append(d.name + "/")
            found["names"] += [str(f.relative_to(d)) for f in files]
    return found


def write_block(root: Path, block: str) -> None:
    f = root / "CLAUDE.md"
    text = f.read_text(encoding="utf-8") if f.is_file() else ""
    m = re.search(r"<!-- brse-toolkit:start -->.*?<!-- brse-toolkit:end -->", text, re.S)
    text = text[:m.start()] + block + text[m.end():] if m else (text.rstrip() + "\n\n" if text.strip() else "") + block
    f.write_text(text.rstrip() + "\n", encoding="utf-8")


def init(root: Path, opts: dict) -> dict:
    existing = brse_config.find_workspace(root)
    if existing == root and not opts["--force"]:
        return {"error": f"{root} is already a workspace — pass --force to rewrite its config and CLAUDE.md block "
                         "(memory, knowledge and registers are kept)"}
    found = scan(root)
    split = lambda v: [s.strip() if s.strip().endswith("/") else s.strip() + "/" for s in v.split(",") if s.strip()]
    opts = {**opts, **{f: split(opts[f]) for f in ("--sources", "--templates") if opts[f]}}
    inferred = {}

    def pick(key, flag, value, source):
        inferred[key] = {"value": opts[flag], "from": "given"} if opts[flag] else {"value": value, "from": source}
        return inferred[key]["value"]

    defaults = json.loads(brse_config.DEFAULTS.read_text(encoding="utf-8"))
    name = pick("name", "--name", root.name, "folder name")
    sources = pick("sources", "--sources", found["sources"] or defaults["paths"]["sources"],
                   "folders holding documents" if found["sources"] else "default — no document folder found yet")
    templates = pick("templates", "--templates", found["templates"],
                     "folders named like a template" if found["templates"] else "none found")
    names = " ".join(found["names"])
    lang = "ja" if JAPANESE.search(names) else ("en" if names and names.isascii() else None)
    client = pick("client_language", "--client-language", lang or defaults["project"]["client_language"],
                  "document names" if lang else "default")
    reply = pick("reply_language", "--reply-language", defaults["project"]["reply_language"], "default")

    brse = root / ".brse"
    for d in ("memory/long", "memory/short", "knowledge/docs", "registers"):
        (brse / d).mkdir(parents=True, exist_ok=True)
    cfg = {"layout_version": 2, "project": {"name": name, "client_language": client},
           "paths": {"sources": sources, "templates": templates,
                     **{k: found[k] for k in ("internal", "deliverables") if found[k]}}}
    for k in ("internal", "deliverables"):
        if found[k]:
            inferred[k] = {"value": found[k], "from": "folder name"}
    (brse / "config.json").write_text(json.dumps(cfg, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    local = brse / "config.local.json"
    if opts["--reply-language"] or not local.is_file():
        local.write_text(json.dumps({"project": {"reply_language": reply}}, ensure_ascii=False, indent=2) + "\n",
                         encoding="utf-8")
    (brse / ".gitignore").write_text("memory/short/\nknowledge/\nwork/\nconfig.local.json\nruns/\ngate/\n",
                                     encoding="utf-8")
    created = []
    for fname, schema in MEMORY.items():
        f = brse / "memory" / "long" / fname
        if not f.is_file():
            f.write_text(schema, encoding="utf-8")
            created.append(str(f.relative_to(root)))
    write_block(root, BLOCK.format(name=name, sources=", ".join(sources), templates=", ".join(templates) or "none",
                                   client_language=client, reply_language=reply))
    if subprocess.run(["git", "rev-parse", "--is-inside-work-tree"], cwd=root, capture_output=True).returncode:
        subprocess.run(["git", "init", "-q"], cwd=root)
        created.append("git repository")
    out = {"workspace": str(root), "created": [".brse/config.json", ".brse/config.local.json", "CLAUDE.md block"]
           + created, "inferred": inferred}
    if existing and existing != root:
        out["note"] = f"this folder is inside another workspace ({existing}); a separate one was created here"
    return out


def main() -> None:
    args = sys.argv[1:]
    opts = {f: take(args, f) for f in ("--name", "--sources", "--templates", "--client-language", "--reply-language")}
    opts["--force"] = "--force" in args
    args = [a for a in args if a != "--force"]
    root = Path(args[0] if args else ".").resolve()
    out = init(root, opts)
    print(json.dumps(out, ensure_ascii=False, indent=2))
    sys.exit(2 if "error" in out else 0)
