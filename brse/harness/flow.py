"""The estimate workflow, held by code: `brse.py gate check` refuses to stamp the estimate until every step passes.

Usage:
  brse.py run start estimate --file <estimate copy>
  brse.py run status                          each step: pass / what is missing / the command to run
  brse.py run read <file> [--not-read "why"]  a `partial` file of the knowledge manifest was read visually (or why not)
  brse.py run pair <old file> <new file>      two versions of the same document (spec v1 → v2, Rev.6 → Rev.7)
  brse.py run approve                         the user approved the requirement list (only after they replied)
  brse.py run rows <rows.json> --column B --from 5
                                              rows.json = {"<sheet>!B5": "R-001", ...}: the requirement each
                                              work-item cell of the estimate comes from
Steps (why each exists — the 2026-11-12 estimate session):
  sources       every file in .brse/knowledge/manifest.json is readable, or its pictures were read / said not read
  versions      documents that exist in several versions are paired, so new and already-existing items are told
                apart (work items were written for a button the old spec already had)
  requirements  every R- in the registers has `source` (new document) and `old_source` (old document, or
                "none" when new) pointing at existing files
  approved      the user replied after the requirement list was ready, and the agent recorded the approval
  rows          every non-empty work-item cell in the declared column maps to an R- that is not out of scope,
                and every R- in scope has a row (rows without a basis were in the estimate)
"""
import json
import re
import sys
import time
from pathlib import Path

from brse import config as brse_config
from brse.cli import take

VERSION = re.compile(r"(?i)[_\-\s]*(rev\.?\s*\d+|ver\.?\s*\d+|v\d+(?:\.\d+)*|第?\d+版)(?=[_\-\s.]|$)")
STEPS = ("sources", "versions", "requirements", "approved", "rows")


class Fail(Exception):
    pass


def state_file(root: Path) -> Path:
    return root / ".brse" / "runs" / "estimate.json"


def load(root: Path):
    f = state_file(root)
    return json.loads(f.read_text(encoding="utf-8")) if f.is_file() else None


def save(root: Path, st: dict) -> None:
    f = state_file(root)
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(json.dumps(st, ensure_ascii=False, indent=1), encoding="utf-8")


def manifest(root: Path) -> dict:
    f = root / ".brse" / "knowledge" / "manifest.json"
    return json.loads(f.read_text(encoding="utf-8")) if f.is_file() else {}


def family(name: str):
    """'画面仕様_v2.md' → '画面仕様.md'; None when the name carries no version."""
    p = Path(name)
    base = VERSION.sub("", p.stem)
    return str(p.with_name(base + p.suffix)) if base != p.stem else None


def requests_count(root: Path) -> list:
    """[session id, number of the user's messages in it] — a new session means the user wrote again."""
    from brse.harness.gate import session_requests
    try:
        sid = json.loads((root / ".brse" / "runs" / "current.json").read_text(encoding="utf-8")).get("session_id")
    except (OSError, ValueError):
        sid = None
    return [sid, len(session_requests(root))]


def file_of(ref: str) -> str:
    """'docs/spec_v2.md:12' or 'docs/a.xlsx#Sheet!B3' → the file part."""
    m = re.match(r"(.+?\.[A-Za-z0-9]{1,5})(?:[:#].*)?$", ref.strip())
    return m.group(1) if m else ref.strip()


def step_results(root: Path, st: dict) -> dict:
    from brse.project import register
    res = {}
    man = manifest(root)
    if not man:
        res["sources"] = "no knowledge manifest — run `brse.py kb-ingest`"
    else:
        todo = [f for f, v in man.items() if v.get("status") == "partial" and f not in st["read"]]
        bad = [f for f, v in man.items() if v.get("status") == "unreadable" and f not in st["read"]]
        res["sources"] = (f"partial files not read yet: {todo} — read their pictures, then `brse.py run read <file>`"
                          if todo else f"unreadable files not accounted for: {bad} — `brse.py run read <file> "
                          "--not-read \"why\"`" if bad else None)
    fams = {}
    for f in man:
        k = family(f)
        if k:
            fams.setdefault(k, []).append(f)
    paired = {f for pair in st["pairs"] for f in pair}
    loose = sorted(f for files in fams.values() if len(files) > 1 for f in files if f not in paired)
    res["versions"] = (f"several versions of one document, not paired: {loose} — `brse.py run pair <old> <new>`"
                       if loose else None)
    reqs = register.load(root, "R")
    if not reqs:
        res["requirements"] = "no requirements in the registers — `brse.py register add R --title ... --source <file:place> --set old_source=<file:place|none>`"
    else:
        probs = []
        for r in reqs:
            src, old = (r.get("source") or "").strip(), str(r.get("old_source") or "").strip()
            if not src or not (root / file_of(src)).is_file():
                probs.append(f"{r['id']}: source '{src}' is not an existing file")
            if not old:
                probs.append(f"{r['id']}: no old_source (the place in the old version, or 'none' when it is new)")
            elif old.lower() != "none" and not (root / file_of(old)).is_file():
                probs.append(f"{r['id']}: old_source '{old}' is not an existing file")
        res["requirements"] = "; ".join(probs) or None
    if res["requirements"] is None and st.get("requirements_ready_at") is None:
        st["requirements_ready_at"] = requests_count(root)
    if res["requirements"]:
        res["approved"] = "requirements not ready"
    elif not st.get("approved"):
        res["approved"] = ("show the requirement list to the user; after they reply, `brse.py run approve`")
    else:
        res["approved"] = None
    rows = st.get("rows")
    if not rows:
        res["rows"] = "no row map — `brse.py run rows <rows.json> --column <letter> --from <first row>`"
    else:
        res["rows"] = rows_problem(root, st, reqs)
    return res


def rows_problem(root: Path, st: dict, reqs: list):
    from brse.office.xlsx import load_workbook
    rows = st["rows"]
    f = Path(st["file"])
    if not f.is_file():
        return f"estimate file {f} does not exist"
    wb = load_workbook(f)
    by_id = {r["id"]: r for r in reqs}
    probs = []
    for sheet in {k.partition("!")[0] for k in rows["map"]} or set(wb.sheetnames[:1]):
        ws = wb[sheet]
        for r in range(rows["from"], ws.max_row + 1):
            v = ws[f"{rows['column']}{r}"].value
            cell = f"{sheet}!{rows['column']}{r}"
            if v not in (None, "") and cell not in rows["map"]:
                probs.append(f"{cell} has no requirement — a row without a basis goes to the client questions, not the estimate")
    for cell, rid in rows["map"].items():
        if rid not in by_id:
            probs.append(f"{cell} → {rid}: no such requirement")
        elif by_id[rid].get("status") == "out":
            probs.append(f"{cell} → {rid}: that requirement is out of scope")
    mapped = set(rows["map"].values())
    probs += [f"{r['id']} is in scope but has no row (or set its status to out)" for r in reqs
              if r.get("status") != "out" and r["id"] not in mapped]
    return "; ".join(probs) or None


def status(root: Path):
    st = load(root)
    if st is None:
        return None
    res = step_results(root, st)
    save(root, st)
    return {"file": st["file"], "steps": {s: ("pass" if res[s] is None else res[s]) for s in STEPS},
            "done": all(res[s] is None for s in STEPS)}


def blocks_stamp(root: Path, file: Path):
    """For `gate check`: the reason the estimate cannot be stamped yet, or None."""
    st = load(root)
    if not st or Path(st["file"]).resolve() != file.resolve():
        return None
    s = status(root)
    return None if s["done"] else {k: v for k, v in s["steps"].items() if v != "pass"}


def main() -> None:
    args = sys.argv[1:]
    opts = {f: take(args, f) for f in ("--file", "--not-read", "--column", "--from")}
    try:
        root, _ = brse_config.workspace(".")
        if not root:
            raise Fail("not inside a brse-toolkit workspace — run /brse-toolkit:init first")
        st = load(root)
        cmd = args[:1]
        if cmd == ["start"] and args[1:2] == ["estimate"]:
            if not opts["--file"]:
                raise Fail("--file <estimate copy> is required")
            st = {"file": str(Path(opts["--file"]).resolve()), "started": time.time(), "read": {}, "pairs": [],
                  "approved": False, "requirements_ready_at": None, "rows": None}
            save(root, st)
            out = status(root)
        elif st is None:
            raise Fail("no estimate run — `brse.py run start estimate --file <estimate copy>`")
        elif cmd == ["status"]:
            out = status(root)
        elif cmd == ["read"] and len(args) == 2:
            st["read"][args[1]] = opts["--not-read"] or "read"
            save(root, st)
            out = status(root)
        elif cmd == ["pair"] and len(args) == 3:
            missing = [a for a in args[1:] if a not in manifest(root)]
            if missing:
                raise Fail(f"not in the knowledge manifest: {missing} — use the paths kb-ingest lists")
            st["pairs"].append(args[1:3])
            save(root, st)
            out = status(root)
        elif cmd == ["approve"]:
            ready = st.get("requirements_ready_at")
            if ready is None:
                raise Fail("the requirement list is not ready yet — see `brse.py run status`")
            now = requests_count(root)
            if now[0] == ready[0] and now[1] <= ready[1]:
                raise Fail("the user has not replied since the requirement list was ready — show it and wait")
            st["approved"] = True
            save(root, st)
            out = status(root)
        elif cmd == ["rows"] and len(args) == 2:
            if not (opts["--column"] and opts["--from"]):
                raise Fail("--column <letter> and --from <first work-item row> are required")
            st["rows"] = {"map": json.loads(Path(args[1]).read_text(encoding="utf-8")),
                          "column": opts["--column"].upper(), "from": int(opts["--from"])}
            save(root, st)
            out = status(root)
        else:
            print(__doc__, file=sys.stderr)
            sys.exit(2)
    except Fail as e:
        print(json.dumps({"error": str(e)}, ensure_ascii=False))
        sys.exit(2)
    print(json.dumps(out, ensure_ascii=False, indent=2))
    sys.exit(0 if out.get("done") else 1)
