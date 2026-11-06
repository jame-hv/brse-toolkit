#!/usr/bin/env python3
"""Work with draw.io diagrams starting from draw.io's own templates.

Usage:
  drawio-tool.py templates [filter]                    list the templates bundled with draw.io
  drawio-tool.py template <name> <out.drawio>          copy one (e.g. cloud/aws/aws_6) as editable XML
  drawio-tool.py cells <file.drawio>                   list shapes/edges: id, label, kind, parent
  drawio-tool.py edit <file> <changes.json> <out>      relabel / delete / add / connect by id
  drawio-tool.py kinds                                 node kinds available to `build`
  drawio-tool.py build <model.json> <out.drawio>       build a diagram from a model when no template fits
  drawio-tool.py lint <file.drawio>                    orphans, dangling edges, overlaps, empty labels
  drawio-tool.py export <file.drawio> <out.png> [--layout NAME]   render with the draw.io CLI
changes.json: {"set": {"<id>": "<new label>"}, "delete": ["<id>"],
  "add": [{"id": "new1", "clone": "<existing id>", "label": "...", "parent": "<id>", "x": 0, "y": 0}],
  "connect": [{"source": "<id>", "target": "<id>", "label": ""}]}
Templates are read straight from draw.io's app.asar (no extra tools). Pure stdlib.
"""
import sys

sys.dont_write_bytecode = True
import base64
import copy
import json
import os
import re
import shutil
import struct
import subprocess
import tempfile
import urllib.parse
import xml.etree.ElementTree as ET
import zlib
from pathlib import Path

import brse_common

ASAR_CANDIDATES = [
    "/snap/drawio/current/app/resources/app.asar", "/opt/drawio/resources/app.asar",
    "/usr/lib/drawio/resources/app.asar", "/Applications/draw.io.app/Contents/Resources/app.asar",
    "C:/Program Files/draw.io/resources/app.asar",
    os.path.expandvars("%LOCALAPPDATA%/Programs/draw.io/resources/app.asar"),
]
TEMPLATE_PREFIX = "drawio/src/main/webapp/templates/"


# ---------- asar (Electron archive) ----------
def find_asar(config: dict):
    override = config.get("tools", {}).get("paths", {}).get("drawio-asar")
    exe = config.get("tools", {}).get("paths", {}).get("drawio") or shutil.which("drawio")
    cands = ([override] if override else []) + ASAR_CANDIDATES
    if exe:
        cands.append(str(Path(exe).resolve().parent / "resources" / "app.asar"))
    return next((c for c in cands if c and Path(c).is_file()), None)


def asar_index(path: str):
    with open(path, "rb") as f:
        head = f.read(16)
        _, header_size, _, json_len = struct.unpack("<4I", head)
        header = json.loads(f.read(json_len))
    base = 8 + header_size
    files = {}

    def walk(node, prefix):
        for name, entry in node.get("files", {}).items():
            p = f"{prefix}{name}"
            if "files" in entry:
                walk(entry, p + "/")
            elif not entry.get("unpacked"):
                files[p] = (base + int(entry["offset"]), entry["size"])
    walk(header, "")
    return files


def asar_read(path: str, files: dict, name: str) -> bytes:
    off, size = files[name]
    with open(path, "rb") as f:
        f.seek(off)
        return f.read(size)


# ---------- drawio XML ----------
def decode_diagram(xml_text: str) -> ET.Element:
    """Return the <mxfile> element with every <diagram> holding a plain <mxGraphModel>."""
    root = ET.fromstring(xml_text)
    if root.tag == "mxGraphModel":
        wrap = ET.Element("mxfile")
        d = ET.SubElement(wrap, "diagram", name="Page-1")
        d.append(root)
        return wrap
    for d in root.iter("diagram"):
        if d.find("mxGraphModel") is None and (d.text or "").strip():
            raw = zlib.decompress(base64.b64decode(d.text.strip()), -15)
            d.text = None
            d.append(ET.fromstring(urllib.parse.unquote(raw.decode("utf-8"))))
    return root


def load(path) -> ET.Element:
    return decode_diagram(Path(path).read_text(encoding="utf-8"))


def model_root(doc: ET.Element) -> ET.Element:
    return doc.find(".//mxGraphModel/root")


def label(cell) -> str:
    return re.sub(r"<[^>]+>", " ", cell.get("value", "")).replace("&nbsp;", " ").strip()


def cell_kind(cell) -> str:
    style = cell.get("style", "")
    if cell.get("edge") == "1":
        return "edge"
    m = re.search(r"(?:resIcon|shape|grIcon)=([\w.]+)", style)
    return m.group(1) if m else (style.split(";")[0] or "box")


def cells(doc):
    for c in model_root(doc).iter("mxCell"):
        if c.get("id") in ("0", "1"):
            continue
        yield c


def geometry(c):
    g = c.find("mxGeometry")
    if g is None or g.get("relative") == "1":
        return None
    return tuple(float(g.get(k, 0)) for k in ("x", "y", "width", "height"))


def cmd_cells(path):
    doc = load(path)
    out = []
    for c in cells(doc):
        item = {"id": c.get("id"), "label": label(c), "kind": cell_kind(c), "parent": c.get("parent")}
        if c.get("edge") == "1":
            item.update(source=c.get("source"), target=c.get("target"))
        out.append(item)
    return out


def cmd_edit(path, changes, out):
    doc = load(path)
    root = model_root(doc)
    by_id = {c.get("id"): c for c in root.iter("mxCell")}
    report = {"set": [], "deleted": [], "added": [], "connected": [], "missing_ids": []}
    for cid, text in changes.get("set", {}).items():
        if cid in by_id:
            by_id[cid].set("value", text)
            report["set"].append(cid)
        else:
            report["missing_ids"].append(cid)
    doomed = set(changes.get("delete", []))
    # template icons often sit inside a group box by position only (not as children): take them too
    boxes = {}
    for c in root.iter("mxCell"):
        g = geometry(c) if c.get("vertex") == "1" else None
        if g and c.get("parent") in ("1", None):
            boxes[c.get("id")] = g
    for d in list(doomed):
        db = boxes.get(d)
        if db:
            doomed |= {cid for cid, b in boxes.items() if cid != d and b[0] >= db[0] and b[1] >= db[1]
                       and b[0] + b[2] <= db[0] + db[2] and b[1] + b[3] <= db[1] + db[3]}
    grew = True
    while grew:  # children of deleted containers, and edges touching deleted cells
        grew = False
        for c in root.iter("mxCell"):
            cid = c.get("id")
            if cid not in doomed and (c.get("parent") in doomed or c.get("source") in doomed or c.get("target") in doomed):
                doomed.add(cid)
                grew = True
    for c in list(root.iter("mxCell")):
        if c.get("id") in doomed:
            root.remove(c)
            report["deleted"].append(c.get("id"))
    for spec in changes.get("add", []):
        src = by_id.get(spec.get("clone"))
        if src is None:
            report["missing_ids"].append(spec.get("clone"))
            continue
        new = copy.deepcopy(src)
        new.set("id", spec["id"])
        new.set("value", spec.get("label", ""))
        new.set("parent", spec.get("parent", src.get("parent")))
        g = new.find("mxGeometry")
        if g is not None:
            for k in ("x", "y"):
                if k in spec:
                    g.set(k, str(spec[k]))
        root.append(new)
        report["added"].append(spec["id"])
    for i, e in enumerate(changes.get("connect", [])):
        el = ET.SubElement(root, "mxCell", id=e.get("id", f"edge-new-{i}"), value=e.get("label", ""),
                           style="edgeStyle=orthogonalEdgeStyle;rounded=0;html=1;endArrow=block;endFill=1;",
                           edge="1", parent="1", source=e["source"], target=e["target"])
        ET.SubElement(el, "mxGeometry", relative="1", **{"as": "geometry"})
        report["connected"].append(f"{e['source']}->{e['target']}")
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    Path(out).write_text(ET.tostring(doc, encoding="unicode"), encoding="utf-8")
    return report


def cmd_lint(path):
    doc = load(path)
    all_cells = list(cells(doc))
    by_id = {c.get("id"): c for c in all_cells}
    ids = set(by_id)
    edges = [c for c in all_cells if c.get("edge") == "1"]
    linked = {e.get("source") for e in edges} | {e.get("target") for e in edges}
    vertices = [c for c in all_cells if c.get("vertex") == "1"]

    def absbox(c):
        g = geometry(c)
        if g is None:
            return None
        x, y, w, h = g
        p = by_id.get(c.get("parent"))
        while p is not None:
            pg = geometry(p)
            if pg:
                x, y = x + pg[0], y + pg[1]
            p = by_id.get(p.get("parent"))
        return x, y, w, h

    boxes = {v.get("id"): absbox(v) for v in vertices if absbox(v)}

    def inside(a, b):  # a fully inside b
        return a[0] >= b[0] and a[1] >= b[1] and a[0] + a[2] <= b[0] + b[2] and a[1] + a[3] <= b[1] + b[3]

    def containers_of(cid):
        out, p = [], by_id.get(cid, {}).get("parent") if by_id.get(cid) is not None else None
        while p and p not in ("0", "1"):
            out.append(p)
            p = by_id[p].get("parent") if p in by_id else None
        box = boxes.get(cid)
        if box:
            out += [o for o, ob in boxes.items() if o != cid and ob != box and inside(box, ob)]
        return out

    findings = []
    for e in edges:
        for end in ("source", "target"):
            if e.get(end) and e.get(end) not in ids:
                findings.append({"rule": "dangling-edge", "id": e.get("id"), "detail": f"{end} {e.get(end)} missing"})
            if not e.get(end):
                findings.append({"rule": "loose-edge", "id": e.get("id"), "detail": f"no {end} attached"})
    is_container = {cid for v in vertices for cid in containers_of(v.get("id"))}
    for v in vertices:
        cid, style = v.get("id"), v.get("style", "")
        if cid in is_container or style.startswith("text;"):
            continue
        if edges and cid not in linked and not any(c in linked for c in containers_of(cid)):
            findings.append({"rule": "orphan", "id": cid, "label": label(v)})
        if not label(v) and "shape=" not in style and "image" not in style:
            findings.append({"rule": "empty-label", "id": cid})
    items = list(boxes.items())
    for i, (a, ga) in enumerate(items):
        for b, gb in items[i + 1:]:
            cross = ga[0] < gb[0] + gb[2] and gb[0] < ga[0] + ga[2] and ga[1] < gb[1] + gb[3] and gb[1] < ga[1] + ga[3]
            if cross and not inside(ga, gb) and not inside(gb, ga):
                findings.append({"rule": "overlap", "ids": [a, b], "labels": [label(by_id[a]), label(by_id[b])]})
    labels = [label(v) for v in vertices if label(v)]
    for dup in sorted({l for l in labels if labels.count(l) > 1}):
        findings.append({"rule": "duplicate-label", "label": dup, "note": "fine if intended (e.g. one per account)"})
    return findings


def cmd_export(path, out, layout, config):
    exe = config.get("tools", {}).get("paths", {}).get("drawio") or shutil.which("drawio")
    if not exe:
        raise RuntimeError("draw.io CLI not found — run /brse-toolkit:doctor")
    src, dst = Path(path).resolve(), Path(out).resolve()
    stage = None
    if exe.startswith("/snap/") and (str(src).startswith("/tmp") or "/." in str(src) or str(dst).startswith("/tmp")):
        # ponytail: snap confinement only sees non-hidden folders under $HOME; stage there and clean up
        stage = Path(tempfile.mkdtemp(prefix="brse-drawio-", dir=Path.home()))
        shutil.copy2(src, stage / src.name)
        run_in, run_out = stage / src.name, stage / dst.name
    else:
        run_in, run_out = src, dst
    args = [exe, "-x", "-f", "png", "-s", "2", "--normalize", "-o", str(run_out), str(run_in)]
    if layout:
        args[1:1] = ["--layout", layout]
    try:
        r = subprocess.run(args, capture_output=True, text=True, timeout=180)
        if not Path(run_out).is_file():
            raise RuntimeError((r.stderr or r.stdout).strip()[-400:] or "export produced no file")
        if stage:
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(run_out, dst)
    finally:
        if stage:
            shutil.rmtree(stage, ignore_errors=True)
    return {"png": str(dst)}


# ---------- build from a model (no hand-written XML) ----------
_ICON = ("outlineConnect=0;fontColor=#232F3E;gradientColor={g};gradientDirection=north;fillColor={f};strokeColor=#ffffff;"
         "dashed=0;verticalLabelPosition=bottom;verticalAlign=top;align=center;html=1;fontSize=14;fontStyle=0;aspect=fixed;"
         "shape=mxgraph.aws4.resourceIcon;resIcon=mxgraph.aws4.{r};labelBackgroundColor=#ffffff;")
_GROUP = ("outlineConnect=0;gradientColor=none;html=1;whiteSpace=wrap;fontSize=14;fontStyle=1;shape=mxgraph.aws4.group;"
          "grIcon=mxgraph.aws4.{gi};strokeColor={s};fillColor={fill};verticalAlign=top;align=left;spacingLeft=30;fontColor={s};"
          "dashed={d};labelBackgroundColor=none;container=1;pointerEvents=0;collapsible=0;recursiveResize=0;")
_CLIENT = ("outlineConnect=0;fontColor=#232F3E;gradientColor=none;fillColor=#232F3D;strokeColor=none;dashed=0;"
           "verticalLabelPosition=bottom;verticalAlign=top;align=center;html=1;fontSize=14;fontStyle=0;aspect=fixed;"
           "pointerEvents=1;shape=mxgraph.aws4.{r};labelBackgroundColor=#ffffff;")
_CAT = {"compute": ("#F78E04", "#D05C17"), "network": ("#945DF2", "#5A30B5"), "database": ("#4D72F3", "#3334B9"),
        "storage": ("#60A337", "#277116"), "integration": ("#F34482", "#BC1356"), "security": ("#F54749", "#C7131F"),
        "management": ("#F34482", "#BC1356")}
ICONS = {  # kind: (category, resIcon)
    "ec2": ("compute", "ec2"), "lambda": ("compute", "lambda"), "ecs": ("compute", "ecs"), "fargate": ("compute", "fargate"),
    "alb": ("network", "elastic_load_balancing"), "cloudfront": ("network", "cloudfront"), "route53": ("network", "route_53"),
    "api_gateway": ("integration", "api_gateway"), "vpn": ("network", "site_to_site_vpn"),
    "rds": ("database", "rds"), "aurora": ("database", "aurora"), "dynamodb": ("database", "dynamodb"),
    "elasticache": ("database", "elasticache"),
    "s3": ("storage", "s3"), "efs": ("storage", "elastic_file_system"),
    "sqs": ("integration", "sqs"), "sns": ("integration", "sns"), "eventbridge": ("integration", "eventbridge"),
    "waf": ("security", "waf"), "cognito": ("security", "cognito"), "secrets_manager": ("security", "secrets_manager"),
    "cloudwatch": ("management", "cloudwatch_2"),
}
CLIENTS = {"pc": "client", "mobile": "mobile_client", "user": "user", "users": "users",
           "server": "traditional_server", "office": "office_building"}
GROUPS = {  # kind: (grIcon, stroke colour, dashed, fill)
    "aws-cloud": ("group_aws_cloud_alt", "#232F3E", 0, "none"), "region": ("group_region", "#00A4A6", 1, "none"),
    "vpc": ("group_vpc2", "#8C4FFF", 0, "none"), "public-subnet": ("group_security_group", "#7AA116", 0, "#F2F6E8"),
    "private-subnet": ("group_security_group", "#00A4A6", 0, "#E6F6F7"),
    "datacenter": ("group_corporate_data_center", "#7D8998", 0, "none"), "account": ("group_account", "#CD2264", 0, "none"),
}
PLAIN = {
    "box": "rounded=1;whiteSpace=wrap;html=1;fontSize=14;strokeColor=#232F3E;fillColor=#FFFFFF;",
    "todo": "rounded=1;whiteSpace=wrap;html=1;fontSize=14;dashed=1;strokeColor=#D05C17;fillColor=#FFF5EB;",
    "note": "text;html=1;align=left;verticalAlign=middle;fontSize=14;whiteSpace=wrap;",
    "title": "text;html=1;align=left;verticalAlign=middle;fontSize=22;fontStyle=1;",
}
EDGE_STYLE = ("edgeStyle=orthogonalEdgeStyle;rounded=0;orthogonalLoop=1;jettySize=auto;html=1;endArrow=open;endFill=0;"
              "strokeWidth=2;fontSize=13;labelBackgroundColor=#ffffff;")


def node_style(kind: str):
    """(style, default width, default height) for a node kind."""
    if kind in ICONS:
        g, f = _CAT[ICONS[kind][0]]
        return _ICON.format(g=g, f=f, r=ICONS[kind][1]), 78, 78
    if kind in CLIENTS:
        return _CLIENT.format(r=CLIENTS[kind]), 78, 78
    if kind in GROUPS:
        gi, stroke, dashed, fill = GROUPS[kind]
        return _GROUP.format(gi=gi, s=stroke, d=dashed, fill=fill), 400, 300
    if kind in PLAIN:
        return PLAIN[kind], (160 if kind in ("box", "todo") else 600), (60 if kind != "title" else 40)
    raise ValueError(f"unknown kind {kind!r}; known: {', '.join(sorted({**ICONS, **CLIENTS, **GROUPS, **PLAIN}))}")


def cmd_build(model: dict, out):
    """model = {"name", "groups": [...], "nodes": [...], "edges": [...]};
    groups/nodes: {id, kind, label, x, y, w?, h?}; edges: {source, target, label?, dashed?, points?: [[x, y]]}.
    Coordinates are absolute; groups are drawn first so nodes sit on top of them."""
    mx = ET.Element("mxfile")
    d = ET.SubElement(mx, "diagram", name=model.get("name", "Page-1"))
    m = ET.SubElement(d, "mxGraphModel", grid="0", page="1", background="#ffffff")
    root = ET.SubElement(m, "root")
    ET.SubElement(root, "mxCell", id="0")
    ET.SubElement(root, "mxCell", id="1", parent="0")
    seen = set()
    for item in model.get("groups", []) + model.get("nodes", []):
        if item["id"] in seen or item["id"] in ("0", "1"):
            raise ValueError(f"duplicate or reserved id {item['id']!r}")
        seen.add(item["id"])
        style, w, h = node_style(item["kind"])
        c = ET.SubElement(root, "mxCell", id=item["id"], value=item.get("label", ""), style=style, vertex="1", parent="1")
        ET.SubElement(c, "mxGeometry", x=str(item.get("x", 0)), y=str(item.get("y", 0)),
                      width=str(item.get("w", w)), height=str(item.get("h", h)), **{"as": "geometry"})
    for i, e in enumerate(model.get("edges", [])):
        for end in ("source", "target"):
            if e[end] not in seen:
                raise ValueError(f"edge {i}: unknown {end} {e[end]!r}")
        style = EDGE_STYLE + ("dashed=1;" if e.get("dashed") else "")
        c = ET.SubElement(root, "mxCell", id=e.get("id", f"e{i}"), value=e.get("label", ""), style=style,
                          edge="1", parent="1", source=e["source"], target=e["target"])
        g = ET.SubElement(c, "mxGeometry", relative="1", **{"as": "geometry"})
        if e.get("points"):
            arr = ET.SubElement(g, "Array", **{"as": "points"})
            for x, y in e["points"]:
                ET.SubElement(arr, "mxPoint", x=str(x), y=str(y))
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    Path(out).write_text(ET.tostring(mx, encoding="unicode"), encoding="utf-8")
    return {"file": str(out), "nodes": len(seen), "edges": len(model.get("edges", []))}


def main() -> None:
    args = sys.argv[1:]
    if not args:
        print(__doc__, file=sys.stderr)
        sys.exit(2)
    cmd = args[0]
    _, config = brse_common.workspace(".")
    try:
        if cmd in ("templates", "template"):
            asar = find_asar(config)
            if not asar:
                raise RuntimeError("draw.io's app.asar not found — install draw.io desktop or set tools.paths.drawio-asar")
            files = asar_index(asar)
            names = sorted(n[len(TEMPLATE_PREFIX):-4] for n in files
                           if n.startswith(TEMPLATE_PREFIX) and n.endswith(".xml") and not n.endswith("index.xml"))
            if cmd == "templates":
                flt = args[1].lower() if len(args) > 1 else ""
                out = [n for n in names if flt in n.lower()]
            else:
                name, dest = args[1], Path(args[2])
                if name not in names:
                    raise RuntimeError(f"no template {name!r}; list them with: drawio-tool.py templates")
                doc = decode_diagram(asar_read(asar, files, TEMPLATE_PREFIX + name + ".xml").decode("utf-8"))
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_text(ET.tostring(doc, encoding="unicode"), encoding="utf-8")
                out = {"template": name, "file": str(dest), "cells": len(list(cells(doc)))}
        elif cmd == "kinds":
            out = {"aws": sorted(ICONS), "clients": sorted(CLIENTS), "groups": sorted(GROUPS), "plain": sorted(PLAIN)}
        elif cmd == "build":
            out = cmd_build(json.loads(Path(args[1]).read_text(encoding="utf-8")), args[2])
        elif cmd == "cells":
            out = cmd_cells(args[1])
        elif cmd == "edit":
            out = cmd_edit(args[1], json.loads(Path(args[2]).read_text(encoding="utf-8")), args[3])
        elif cmd == "lint":
            out = {"findings": cmd_lint(args[1])}
        elif cmd == "export":
            layout = args[args.index("--layout") + 1] if "--layout" in args else None
            out = cmd_export(args[1], args[2], layout, config)
        else:
            raise RuntimeError(f"unknown command {cmd}")
    except Exception as e:
        print(json.dumps({"error": f"{type(e).__name__}: {e}"}, ensure_ascii=False))
        sys.exit(1)
    print(json.dumps(out, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
