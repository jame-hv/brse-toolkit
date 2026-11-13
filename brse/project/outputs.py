"""The output folder: deliverables and their versions, and what does not belong there.

Usage:
  brse.py outputs          list deliverables in config.paths.outputs by name with their versions (latest last),
                           and the clutter: backup copies, intermediate files, names with words after the version
  brse.py outputs tidy     move the clutter to .brse/work/old/<date>/ (moved, never deleted)

Rules (basis: what piled up in real workspaces after a few runs):
- a deliverable is named <name>_v<N.N>.<ext>; a change is the next version made from the latest one, and the
  old file stays as the backup — so backup copies (_bak, 書換前, 修正前...) are clutter;
- intermediate files (scripts, JSON models, extracted text, screenshots, previews) belong in .brse/work/;
- <file>.sources.md and <file>.claims.json beside an existing file are part of it (diagram build writes them).
"""
import json
import re
import shutil
import sys
import time
from pathlib import Path

from brse import config as brse_config

VERSION = re.compile(r"[_\- ]?[vV](\d+(?:\.\d+)*)")
BACKUP = re.compile(r"(?i)(^|[_\-. ])(bak|backup|tmp|temp)([_\-. ]|$)|書換前|修正前|削除前|変更前|のコピー|~\$")
INTERMEDIATE = {".json", ".mjs", ".js", ".py", ".txt", ".log", ".csv"}
SHOT = re.compile(r"(?i)preview|shot|screenshot|render")
SIDECARS = (".sources.md", ".claims.json")


def parse(name: str):
    """(base, version tuple or None, words after the version)."""
    stem = Path(name).stem
    m = None
    for m in VERSION.finditer(stem):
        pass
    if not m:
        return stem, None, ""
    return stem[:m.start()], tuple(int(x) for x in m.group(1).split(".")), stem[m.end():].strip("_- ")


def why_clutter(p: Path, names: set):
    n = p.name
    if any(n.endswith(s) and n[:-len(s)] in names for s in SIDECARS):
        return None
    if BACKUP.search(Path(n).stem):
        return "backup copy — the previous version is the backup"
    if p.suffix.lower() in INTERMEDIATE:
        return "intermediate file — belongs in .brse/work/"
    if p.suffix.lower() == ".png" and SHOT.search(n):
        return "screenshot / preview — belongs in .brse/work/"
    if parse(n)[2]:
        return "words after the version — name the next one <name>_v<N.N>"
    return None


def scan(folder: Path) -> dict:
    files = sorted(f for f in folder.rglob("*") if f.is_file()) if folder.is_dir() else []
    names = {f.name for f in files}
    clutter, groups = [], {}
    for f in files:
        why = why_clutter(f, names)
        if why:
            clutter.append({"file": str(f.relative_to(folder)), "why": why})
        elif not f.name.endswith(SIDECARS):
            base, ver, _ = parse(f.name)
            groups.setdefault((str(f.parent.relative_to(folder)), base, f.suffix.lower()), []).append((ver or (), f))
    deliverables = [{"name": str(Path(d) / (b + s)) if d != "." else b + s,
                     "versions": [str(f.relative_to(folder)) for _, f in sorted(v, key=lambda x: x[0])]}
                    for (d, b, s), v in sorted(groups.items())]
    return {"deliverables": deliverables, "clutter": clutter}


def main() -> None:
    args = sys.argv[1:]
    root, config = brse_config.workspace(".")
    if not root:
        print(json.dumps({"error": "not inside a brse-toolkit workspace — run /brse-toolkit:init first"}))
        sys.exit(2)
    folder = root / config.get("paths", {}).get("outputs", "output/")
    out = {"folder": str(folder.relative_to(root)), **scan(folder)}
    if args[:1] == ["tidy"]:
        dest = root / ".brse" / "work" / "old" / time.strftime("%Y%m%d")
        moved = []
        for c in out["clutter"]:
            src, to = folder / c["file"], dest / c["file"]
            to.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(src), str(to))
            moved.append(str(to.relative_to(root)))
        out = {"folder": out["folder"], "moved": moved, **scan(folder)}
    elif args:
        print(__doc__, file=sys.stderr)
        sys.exit(2)
    print(json.dumps(out, ensure_ascii=False, indent=2))
