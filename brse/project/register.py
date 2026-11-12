"""Project registers: requirements, gaps, Q&A, decisions, tasks, meetings, plus
version history of the approach and the estimate. Every item has an ID and links,
so a change can be traced to everything it touches.

Storage: <workspace>/.brse/registers/<kind>.json (one list per kind) and
versions.json. `render` writes a readable REGISTER.md next to them.
All output is JSON on stdout; errors exit 2 with {"error": ...}.

  brse.py register add Q --title "..." [--links R-003,G-002] [--owner client] [--due 2026-11-20]
  brse.py register add D --title "..." --source M-2026-11-09 --supersedes D-006 --links R-003
  brse.py register update Q-004 --status answered --set answer="..."
  brse.py register get D-014 | list [--kind Q] [--status sent] [--open]
  brse.py register impact D-014            # everything linked, grouped by kind
  brse.py register bump estimate --file 02_analysis/estimate_v1.4.xlsx --reason "..." --decisions D-014
  brse.py register check [--stale-days 5]  # broken links, overdue tasks, unanswered Q&A
  brse.py register status                  # dashboard counts for reports
  brse.py register render                  # .brse/registers/REGISTER.md
"""
import argparse
import datetime as dt
import json
import re
from collections import deque
from pathlib import Path

from brse import config as brse_config
from brse import markdown

KINDS = {
    "R": {"name": "requirements", "statuses": ["open", "in", "out", "pending"], "default": "open",
          "closed": ["in", "out"]},
    "G": {"name": "gaps", "statuses": ["open", "closed"], "default": "open", "closed": ["closed"]},
    "Q": {"name": "qa", "statuses": ["draft", "sent", "answered", "closed", "void"], "default": "draft",
          "closed": ["closed", "void"]},
    "D": {"name": "decisions", "statuses": ["proposed", "active", "superseded"], "default": "active",
          "closed": ["superseded"]},
    "T": {"name": "tasks", "statuses": ["todo", "doing", "waiting", "done", "cancelled"], "default": "todo",
          "closed": ["done", "cancelled"]},
    "M": {"name": "meetings", "statuses": ["held"], "default": "held", "closed": ["held"]},
}
ARTIFACTS = ("approach", "estimate")
ID_RE = re.compile(r"^([RGQDTM])-(.+)$")


class Fail(Exception):
    pass


def today() -> str:
    return dt.date.today().isoformat()


def reg_dir(root: Path) -> Path:
    return root / ".brse" / "registers"


def load(root: Path, kind: str) -> list:
    p = reg_dir(root) / f"{KINDS[kind]['name']}.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else []


def save(root: Path, kind: str, items: list):
    d = reg_dir(root)
    d.mkdir(parents=True, exist_ok=True)
    (d / f"{KINDS[kind]['name']}.json").write_text(
        json.dumps(items, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")


def load_versions(root: Path) -> list:
    p = reg_dir(root) / "versions.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else []


def all_items(root: Path) -> dict:
    return {i["id"]: i for k in KINDS for i in load(root, k)}


def kind_of(item_id: str) -> str:
    m = ID_RE.match(item_id or "")
    if not m:
        raise Fail(f"not an item id: {item_id!r} (expected R-/G-/Q-/D-/T-/M-…)")
    return m.group(1)


def split_ids(text) -> list:
    return [x.strip() for x in (text or "").split(",") if x.strip()]


def parse_sets(pairs) -> dict:
    out = {}
    for p in pairs or []:
        if "=" not in p:
            raise Fail(f"--set expects key=value, got {p!r}")
        k, v = p.split("=", 1)
        if k in ("id", "kind", "links", "created"):
            raise Fail(f"--set cannot change {k!r}")
        out[k.strip()] = v
    return out


def next_id(kind: str, items: list, given=None) -> str:
    if given:
        if kind_of(given) != kind:
            raise Fail(f"id {given} does not match kind {kind}")
        if any(i["id"] == given for i in items):
            raise Fail(f"{given} already exists")
        return given
    if kind == "M":
        base = f"M-{today()}"
        n = sum(1 for i in items if i["id"].startswith(base))
        return base if n == 0 else f"{base}-{n + 1}"
    nums = [int(m.group(1)) for i in items if (m := re.match(rf"^{kind}-(\d+)$", i["id"]))]
    return f"{kind}-{(max(nums) + 1) if nums else 1:03d}"


def check_status(kind, status):
    if status and status not in KINDS[kind]["statuses"]:
        raise Fail(f"status {status!r} invalid for {kind}; use one of {KINDS[kind]['statuses']}")


def find(root, item_id):
    kind = kind_of(item_id)
    items = load(root, kind)
    for i in items:
        if i["id"] == item_id:
            return kind, items, i
    raise Fail(f"{item_id} not found")


def cmd_add(root, a):
    kind = a.kind.upper()
    if kind not in KINDS:
        raise Fail(f"kind must be one of {list(KINDS)}")
    check_status(kind, a.status)
    items = load(root, kind)
    known = all_items(root)
    links = split_ids(a.links)
    for l in links:
        kind_of(l)
    item = {"id": next_id(kind, items, a.id), "title": a.title, "status": a.status or KINDS[kind]["default"],
            "source": a.source or "", "links": links, "owner": a.owner or "", "due": a.due or "",
            "created": today(), "updated": today()}
    item.update(parse_sets(a.set))
    warnings = [f"link {l} does not exist yet" for l in links if l not in known]
    if a.supersedes:
        if kind != "D":
            raise Fail("--supersedes is only for decisions (D)")
        _, ditems, old = find(root, a.supersedes)
        item["supersedes"] = a.supersedes
        if a.supersedes not in item["links"]:
            item["links"].append(a.supersedes)
        if item["status"] == "active":
            old["status"], old["superseded_by"], old["updated"] = "superseded", item["id"], today()
            ditems = [old if i["id"] == old["id"] else i for i in ditems]
            items = ditems
    items.append(item)
    save(root, kind, items)
    return {"added": item, "warnings": warnings}


def cmd_update(root, a):
    kind, items, item = find(root, a.item_id)
    check_status(kind, a.status)
    if a.status:
        item["status"] = a.status
        if kind == "Q" and a.status == "sent" and not item.get("sent"):
            item["sent"] = today()
        if kind == "Q" and a.status == "answered" and not item.get("answered"):
            item["answered"] = today()
    for f in ("title", "owner", "due", "source"):
        if getattr(a, f) is not None:
            item[f] = getattr(a, f)
    for l in split_ids(a.add_links):
        kind_of(l)
        if l not in item["links"]:
            item["links"].append(l)
    item["links"] = [l for l in item["links"] if l not in split_ids(a.remove_links)]
    item.update(parse_sets(a.set))
    item["updated"] = today()
    save(root, kind, items)
    return {"updated": item}


def cmd_get(root, a):
    _, _, item = find(root, a.item_id)
    known = all_items(root)
    back = sorted(i["id"] for i in known.values() if a.item_id in i.get("links", []))
    return {"item": item, "linked_from": back}


def is_open(item) -> bool:
    return item["status"] not in KINDS[kind_of(item["id"])]["closed"]


def cmd_list(root, a):
    kinds = [a.kind.upper()] if a.kind else list(KINDS)
    out = []
    for k in kinds:
        if k not in KINDS:
            raise Fail(f"kind must be one of {list(KINDS)}")
        for i in load(root, k):
            if a.status and i["status"] not in split_ids(a.status):
                continue
            if a.owner and i.get("owner") != a.owner:
                continue
            if a.open and not is_open(i):
                continue
            out.append(i)
    return {"count": len(out), "items": out}


def cmd_impact(root, a):
    known = all_items(root)
    if a.item_id not in known:
        raise Fail(f"{a.item_id} not found")
    graph = {i: set(it.get("links", [])) for i, it in known.items()}
    for i, it in known.items():
        for l in it.get("links", []):
            graph.setdefault(l, set()).add(i)
    seen, q = {a.item_id: 0}, deque([a.item_id])
    while q:
        cur = q.popleft()
        if seen[cur] >= a.depth:
            continue
        for nb in graph.get(cur, ()):
            if nb not in seen:
                seen[nb] = seen[cur] + 1
                q.append(nb)
    grouped = {}
    for i, d in sorted(seen.items(), key=lambda x: (x[1], x[0])):
        if i == a.item_id:
            continue
        it = known.get(i, {"id": i, "title": "(missing)", "status": "?"})
        grouped.setdefault(kind_of(i), []).append(
            {"id": i, "title": it["title"], "status": it["status"], "distance": d, "open": i in known and is_open(it)})
    versions = [v for v in load_versions(root) if set(v.get("decisions", [])) & set(seen)]
    return {"item": known[a.item_id], "impacted": grouped, "versions_based_on_these": versions,
            "hint": "Estimate lines and approach sections citing these IDs must be re-checked."}


def cmd_bump(root, a):
    vs = load_versions(root)
    mine = [v for v in vs if v["artifact"] == a.artifact]
    if a.version:
        ver = a.version
    elif mine:
        major, minor = (mine[-1]["version"].split(".") + ["0"])[:2]
        ver = f"{major}.{int(minor) + 1}"
    else:
        ver = "1.0"
    decisions = split_ids(a.decisions)
    for d in decisions:
        if kind_of(d) != "D":
            raise Fail(f"--decisions takes D- ids, got {d}")
    v = {"artifact": a.artifact, "version": ver, "file": a.file or "", "reason": a.reason,
         "decisions": decisions, "date": today(), "previous": mine[-1]["version"] if mine else None}
    vs.append(v)
    d = reg_dir(root)
    d.mkdir(parents=True, exist_ok=True)
    (d / "versions.json").write_text(json.dumps(vs, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return {"bumped": v}


def problems(root, stale_days):
    known = all_items(root)
    t = dt.date.today()
    out = []
    for i, it in known.items():
        for l in it.get("links", []):
            if l not in known:
                out.append({"id": i, "problem": f"links to missing {l}"})
        if it.get("due") and is_open(it):
            try:
                if dt.date.fromisoformat(it["due"]) < t:
                    out.append({"id": i, "problem": f"overdue since {it['due']}", "owner": it.get("owner", "")})
            except ValueError:
                out.append({"id": i, "problem": f"due date not YYYY-MM-DD: {it['due']}"})
        if i.startswith("Q-") and it["status"] == "sent" and it.get("sent"):
            age = (t - dt.date.fromisoformat(it["sent"])).days
            if age >= stale_days:
                out.append({"id": i, "problem": f"sent {age} days ago, no answer"})
        if i.startswith("Q-") and it["status"] == "answered":
            if not any(x.startswith("D-") for x in it.get("links", [])) and not any(
                    i in o.get("links", []) for o in known.values() if o["id"].startswith("D-")):
                out.append({"id": i, "problem": "answered but no decision (D) recorded from it"})
        if i.startswith("D-") and it["status"] == "active" and it.get("superseded_by"):
            out.append({"id": i, "problem": f"active but superseded_by {it['superseded_by']}"})
    return out


def cmd_check(root, a):
    p = problems(root, a.stale_days)
    return {"ok": not p, "problems": p}


def cmd_status(root, a):
    counts = {}
    for k, meta in KINDS.items():
        c = {}
        for i in load(root, k):
            c[i["status"]] = c.get(i["status"], 0) + 1
        counts[meta["name"]] = c
    tasks = [i for i in load(root, "T") if is_open(i)]
    latest = {}
    for v in load_versions(root):
        latest[v["artifact"]] = v
    return {"counts": counts,
            "waiting_on_user": [i for i in tasks if i.get("owner") in ("anh", "user", "me")]
            + [i for i in load(root, "D") if i["status"] == "proposed"],
            "waiting_on_client": [i for i in load(root, "Q") if i["status"] == "sent"]
            + [i for i in tasks if i.get("owner") == "client"],
            "open_tasks": tasks, "latest_versions": latest, "problems": problems(root, a.stale_days)}


def md_table(items, cols):
    if not items:
        return "_(none)_\n"
    cell = lambda v: (", ".join(v) if isinstance(v, list) else str(v)).replace("|", "\\|").replace("\n", " ")
    return markdown.table(cols, [[cell(i.get(c, "")) for c in cols] for i in items]) + "\n"


def cmd_render(root, a):
    parts = [f"# Project register\n\n_Generated {today()} by brse.py register — do not edit; "
             f"change items with brse.py register._\n"]
    cols = {"R": ["id", "title", "status", "source", "links"], "G": ["id", "title", "status", "links"],
            "Q": ["id", "title", "status", "sent", "answered", "links"],
            "D": ["id", "title", "status", "source", "supersedes", "links"],
            "T": ["id", "title", "status", "owner", "due", "links"], "M": ["id", "title", "links"]}
    for k, meta in KINDS.items():
        parts.append(f"\n## {meta['name'].capitalize()} ({k})\n\n" + md_table(load(root, k), cols[k]))
    parts.append("\n## Versions\n\n" + md_table(load_versions(root),
                                                 ["artifact", "version", "date", "reason", "decisions", "file"]))
    p = problems(root, a.stale_days)
    parts.append("\n## Problems\n\n" + md_table(p, ["id", "problem"]))
    out = reg_dir(root) / "REGISTER.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("".join(parts), encoding="utf-8")
    return {"written": str(out), "problems": len(p)}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", default=".", help="any folder inside the workspace (default: cwd)")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("add")
    p.add_argument("kind")
    p.add_argument("--title", required=True)
    for f in ("id", "status", "source", "links", "owner", "due", "supersedes"):
        p.add_argument(f"--{f}")
    p.add_argument("--set", action="append")
    p = sub.add_parser("update")
    p.add_argument("item_id")
    for f in ("status", "title", "owner", "due", "source", "add-links", "remove-links"):
        p.add_argument(f"--{f}")
    p.add_argument("--set", action="append")
    p = sub.add_parser("get")
    p.add_argument("item_id")
    p = sub.add_parser("list")
    for f in ("kind", "status", "owner"):
        p.add_argument(f"--{f}")
    p.add_argument("--open", action="store_true")
    p = sub.add_parser("impact")
    p.add_argument("item_id")
    p.add_argument("--depth", type=int, default=3)
    p = sub.add_parser("bump")
    p.add_argument("artifact", choices=ARTIFACTS)
    p.add_argument("--reason", required=True)
    for f in ("file", "decisions", "version"):
        p.add_argument(f"--{f}")
    for name in ("check", "status", "render"):
        p = sub.add_parser(name)
        p.add_argument("--stale-days", type=int, default=5)
    a = ap.parse_args(argv)
    try:
        root, _ = brse_config.workspace(a.root)
        if root is None:
            raise Fail("not inside a brse-toolkit workspace; run /brse-toolkit:init first")
        out = globals()[f"cmd_{a.cmd}"](root, a)
    except (Fail, ValueError) as e:
        print(json.dumps({"error": str(e)}, ensure_ascii=False))
        return 2
    print(json.dumps(out, ensure_ascii=False, indent=1))
    return 0

