#!/usr/bin/env python3
"""Personal library of approved deliverables, reusable across projects.

Usage:
  library.py add <file> --kind <kind> [--note TEXT] [--project NAME]
  library.py list [--kind <kind>]
  library.py remove <id>
Stored per user (not per project) in <data dir>/brse-toolkit/library/, with an
index.json. Kinds are free text; common ones: estimate, preconditions,
proposal, test-spec, detail-design, report. Only what the user explicitly
chooses to add is stored — it may contain one client's material, so the
skills ask before reusing an item for a different client.
"""
import sys

sys.dont_write_bytecode = True
import datetime
import json
import shutil
import uuid
from pathlib import Path

import brse_common


def lib_dir() -> Path:
    return brse_common.data_dir() / "library"


def load_index() -> list:
    f = lib_dir() / "index.json"
    return json.loads(f.read_text(encoding="utf-8")) if f.is_file() else []


def save_index(items: list) -> None:
    lib_dir().mkdir(parents=True, exist_ok=True)
    (lib_dir() / "index.json").write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")


def opt(args: list, flag: str, default=None):
    if flag in args:
        i = args.index(flag)
        val = args[i + 1]
        del args[i:i + 2]
        return val
    return default


def main() -> None:
    args = sys.argv[1:]
    cmd = args.pop(0) if args else ""
    items = load_index()
    if cmd == "add":
        kind, note, project = opt(args, "--kind"), opt(args, "--note", ""), opt(args, "--project", "")
        if not args or not kind:
            print(json.dumps({"error": "usage: library.py add <file> --kind <kind> [--note T] [--project N]"}))
            sys.exit(2)
        src = Path(args[0])
        if not src.is_file():
            print(json.dumps({"error": f"no such file: {src}"}))
            sys.exit(1)
        item_id = uuid.uuid4().hex[:8]
        dest = lib_dir() / kind / f"{item_id}-{src.name}"
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dest)
        entry = {"id": item_id, "kind": kind, "file": str(dest), "original_name": src.name,
                 "note": note, "project": project, "added": datetime.date.today().isoformat()}
        save_index(items + [entry])
        print(json.dumps(entry, ensure_ascii=False, indent=2))
    elif cmd == "list":
        kind = opt(args, "--kind")
        print(json.dumps([i for i in items if not kind or i["kind"] == kind], ensure_ascii=False, indent=2))
    elif cmd == "remove" and args:
        keep = [i for i in items if i["id"] != args[0]]
        for i in items:
            if i["id"] == args[0] and Path(i["file"]).is_file():
                Path(i["file"]).unlink()
        save_index(keep)
        print(json.dumps({"removed": len(items) - len(keep)}))
    else:
        print(__doc__, file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    main()
