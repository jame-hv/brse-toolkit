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
  "add": [{"id": "new1", "clone": "<id>", "from"?: "<other.drawio> | template:<name>", "label": "...",
           "parent": "<id>", "x": 0, "y": 0}],   ("from" brings an icon over from another diagram or template)
  "connect": [{"source": "<id>", "target": "<id>", "label": ""}]}
Templates are read straight from draw.io's app.asar (no extra tools). Pure stdlib.
"""
import sys

sys.dont_write_bytecode = True
import base64
import importlib.util
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


def load_any(ref: str) -> ET.Element:
    """A .drawio path, or 'template:<name>' for one of draw.io's bundled templates."""
    if ref.startswith("template:"):
        _, config = brse_common.workspace(".")
        asar = find_asar(config)
        if not asar:
            raise RuntimeError("draw.io's app.asar not found — cannot read templates")
        files = asar_index(asar)
        name = TEMPLATE_PREFIX + ref[len("template:"):] + ".xml"
        if name not in files:
            raise RuntimeError(f"no template {ref[len('template:'):]!r}")
        return decode_diagram(asar_read(asar, files, name).decode("utf-8"))
    return load(ref)


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
    others = {}
    for spec in changes.get("add", []):
        pool = by_id
        if spec.get("from"):  # an icon from another .drawio file or a bundled template ("template:cloud/aws/aws_6")
            if spec["from"] not in others:
                others[spec["from"]] = {c.get("id"): c for c in model_root(load_any(spec["from"])).iter("mxCell")}
            pool = others[spec["from"]]
        src = pool.get(spec.get("clone"))
        if src is None:
            report["missing_ids"].append(f"{spec.get('from', '')}#{spec.get('clone')}")
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
        if cid in is_container or style.startswith("text;") or re.search(r"brseKind=(legend|lane|title)", style):
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
    kind_of = {c.get("id"): (re.search(r"brseKind=([\w-]+)", c.get("style", "")) or [None, None])[1] for c in all_cells}
    for v in vertices:
        text = label(v)
        k = kind_of.get(v.get("id"))
        if not text or k in ("title", "legend", "lane", "note") or v.get("style", "").startswith("text;"):
            continue
        lines = [x for x in re.split(r"<br\s*/?>|\n", v.get("value", "")) if re.sub(r"<[^>]+>", "", x).strip()]
        if len(lines) > 2 or any(len(re.sub(r"<[^>]+>", "", x).strip()) > 28 for x in lines):
            findings.append({"rule": "long-label", "id": v.get("id"), "label": text[:60],
                             "note": "max 2 lines of ~28 characters — put details in a table next to the diagram"})
        if re.search(r"[\u3040-\u30ff\u4e00-\u9fff]", text) and re.search(
                r"[ăâđêôơưạảấầẩẫậắằẳẵặẹẻẽếềểễệịọỏốồổỗộớờởỡợụủứừửữựỳỵỷỹ]", text, re.I):
            findings.append({"rule": "mixed-language-label", "id": v.get("id"), "label": text[:60]})
    for e in edges:
        if not label(e) and kind_of.get(e.get("source")) in INTERFACE_KINDS and kind_of.get(e.get("target")) in INTERFACE_KINDS:
            findings.append({"rule": "unlabeled-interface", "id": e.get("id"),
                             "detail": f"{e.get('source')} → {e.get('target')}: say what flows (data, file, instruction)"})
    labels = [label(v) for v in vertices if label(v) and kind_of.get(v.get("id")) not in ("legend", "lane")]
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


SEMANTIC = {  # kind: (style, w, h) — non-cloud systems: logistics, ERP, factory, on-premise
    "system": ("rounded=1;whiteSpace=wrap;html=1;fontSize=14;fontStyle=1;fillColor=#DAE8FC;strokeColor=#6C8EBF;arcSize=8;", 170, 70),
    "external-system": ("rounded=1;whiteSpace=wrap;html=1;fontSize=14;fontStyle=1;fillColor=#F5F5F5;strokeColor=#666666;arcSize=8;", 170, 70),
    "module": ("rounded=1;whiteSpace=wrap;html=1;fontSize=13;fillColor=#FFFFFF;strokeColor=#6C8EBF;arcSize=8;", 150, 56),
    "device": ("rounded=1;whiteSpace=wrap;html=1;fontSize=13;fillColor=#FFF2CC;strokeColor=#D6B656;arcSize=8;", 140, 56),
    "equipment": ("shape=process;whiteSpace=wrap;html=1;fontSize=13;fillColor=#E1D5E7;strokeColor=#9673A6;size=0.08;", 150, 56),
    "datastore": ("shape=cylinder3;whiteSpace=wrap;html=1;boundedLbl=1;backgroundOutline=1;size=10;fontSize=13;fillColor=#F5F5F5;strokeColor=#666666;", 110, 70),
    "file": ("shape=note;whiteSpace=wrap;html=1;size=12;fontSize=12;fillColor=#FFFFFF;strokeColor=#666666;", 120, 56),
    "actor": ("shape=umlActor;verticalLabelPosition=bottom;verticalAlign=top;html=1;fontSize=13;strokeColor=#333333;fillColor=#FFFFFF;", 30, 56),
    "step": ("rounded=1;whiteSpace=wrap;html=1;fontSize=13;fillColor=#FFFFFF;strokeColor=#333333;arcSize=12;", 150, 56),
    "decision": ("rhombus;whiteSpace=wrap;html=1;fontSize=12;fillColor=#FFFFFF;strokeColor=#333333;", 120, 70),
    "start": ("ellipse;whiteSpace=wrap;html=1;fontSize=12;fillColor=#333333;fontColor=#FFFFFF;strokeColor=none;", 40, 40),
    "end": ("ellipse;shape=doubleEllipse;whiteSpace=wrap;html=1;fontSize=12;fillColor=#FFFFFF;strokeColor=#333333;", 40, 40),
}
STATUS = {  # how a node/edge is marked; the legend is generated from what is used
    "changed": ("strokeColor=#D6001C;strokeWidth=3;fillColor=#FFE6E6;", "strokeColor=#D6001C;strokeWidth=3;", "変更 / changed"),
    "new": ("strokeColor=#2E7D32;strokeWidth=3;fillColor=#E8F5E9;", "strokeColor=#2E7D32;strokeWidth=3;", "新規 / new"),
    "removed": ("dashed=1;strokeColor=#999999;fontColor=#999999;fillColor=#F5F5F5;", "dashed=1;strokeColor=#999999;", "廃止 / removed"),
    "unconfirmed": ("dashed=1;strokeColor=#D05C17;", "dashed=1;strokeColor=#D05C17;", "要確認 / to confirm"),
}
INTERFACE_KINDS = {"system", "external-system", "module", "datastore"}  # business systems: say what flows


def node_style(kind: str):
    """(style, default width, default height) for a node kind. Every style carries brseKind=<kind>."""
    if kind in ICONS:
        g, f = _CAT[ICONS[kind][0]]
        style, w, h = _ICON.format(g=g, f=f, r=ICONS[kind][1]), 78, 78
    elif kind in CLIENTS:
        style, w, h = _CLIENT.format(r=CLIENTS[kind]), 78, 78
    elif kind in GROUPS:
        gi, stroke, dashed, fill = GROUPS[kind]
        style, w, h = _GROUP.format(gi=gi, s=stroke, d=dashed, fill=fill), 400, 300
    elif kind in SEMANTIC:
        style, w, h = SEMANTIC[kind]
    elif kind in PLAIN:
        style, w, h = PLAIN[kind], (160 if kind in ("box", "todo") else 600), (60 if kind != "title" else 40)
    else:
        raise ValueError(f"unknown kind {kind!r}; known: {', '.join(sorted({**ICONS, **CLIENTS, **GROUPS, **SEMANTIC, **PLAIN}))}")
    return style + f"brseKind={kind};", w, h


def with_status(style: str, status, kind: str, edge=False) -> str:
    if not status:
        return style
    if status not in STATUS:
        raise ValueError(f"unknown status {status!r}; known: {', '.join(STATUS)}")
    node_add, edge_add, _ = STATUS[status]
    tag = f"brseStatus={status};"
    if edge:
        return style + edge_add + tag
    if kind in ICONS or kind in CLIENTS:  # keep the icon colours, mark the outline only
        return style + ("strokeColor=#D6001C;strokeWidth=3;" if status == "changed" else edge_add) + tag
    return style + node_add + tag


def swimlane_positions(model: dict) -> dict:
    """lanes = [{id, label}], nodes carry lane + col → absolute positions, lanes sized to fit."""
    head, colw, pad = 140, 210, 24
    lanes = model["lanes"]
    lane_ids = [l["id"] for l in lanes]
    stacks = {}
    for n in model.get("nodes", []):
        if n.get("lane") not in lane_ids:
            raise ValueError(f"node {n['id']!r}: lane {n.get('lane')!r} is not one of {lane_ids}")
        stacks.setdefault((n["lane"], int(n.get("col", 0))), []).append(n)
    lane_h = {}
    for lid in lane_ids:
        heights = [sum(node_style(m["kind"])[2] + pad for m in ms) + pad
                   for (l, _), ms in stacks.items() if l == lid]
        lane_h[lid] = max([110] + heights)
    cols = max([int(n.get("col", 0)) for n in model.get("nodes", [])] + [0]) + 1
    width = head + cols * colw + pad
    pos, y = {}, model.get("top", 60)
    lane_boxes = []
    for l in lanes:
        lane_boxes.append({"id": l["id"], "label": l["label"], "x": 0, "y": y, "w": width, "h": lane_h[l["id"]]})
        for (lid, col), ms in stacks.items():
            if lid != l["id"]:
                continue
            total = sum(node_style(m["kind"])[2] for m in ms) + pad * (len(ms) - 1)
            ny = y + (lane_h[lid] - total) / 2
            for m in ms:
                _, w, h = node_style(m["kind"])
                w, h = m.get("w", w), m.get("h", h)
                pos[m["id"]] = (head + col * colw + (colw - w) / 2, ny, w, h)
                ny += h + pad
        y += lane_h[l["id"]]
    return {"nodes": pos, "lanes": lane_boxes, "bottom": y, "width": width}


LANE_STYLE = ("swimlane;horizontal=0;whiteSpace=wrap;html=1;startSize=140;fontSize=14;fontStyle=1;"
              "fillColor=#F5F5F5;swimlaneFillColor=#FFFFFF;strokeColor=#999999;brseKind=lane;")


def cmd_build(model: dict, out):
    """model = {"name", "layout": "swimlane" | "auto", "direction"?: "RIGHT" | "DOWN",
    "lanes"?: [{id, label}], "nodes": [...], "edges": [...], "legend"?: true}
    nodes: {id, kind, label, status?, lane?, col?, ref?}
    edges: {source, target, label?, status?, ref?}
    ref = {"file": "<path in the workspace>", "part": "<page / section / sheet>", "quote": "<words in the source>"}
    Positions are never typed by hand: swimlane → lane = who does it, col = order of the step;
    auto → draw.io's layered layout from the arrows (needs the draw.io CLI).
    An element without a ref is drawn as unconfirmed (dashed) whatever status was asked for.
    Writes <out>.sources.md (one row per element with its source) and <out>.claims.json
    (for verify-claims.py, which opens each source and checks the quote is there)."""
    layout = model.get("layout")
    if layout not in ("swimlane", "auto"):
        raise ValueError("layout must be 'swimlane' (lane = who, col = step order) or 'auto' "
                         "(layered layout from the arrows) — positions are not set by hand")
    for item in model.get("groups", []):
        raise ValueError("groups need hand positions; use a draw.io template (drawio-tool.py templates) instead")
    mx = ET.Element("mxfile")
    d = ET.SubElement(mx, "diagram", name=model.get("name", "Page-1"))
    for key in ("title", "question", "reader"):
        if not model.get(key):
            raise ValueError(f"model needs '{key}': what the diagram answers and for whom (criterion 1)")
    m = ET.SubElement(d, "mxGraphModel", grid="0", page="1", background="#ffffff",
                      brseLayout=layout, brseQuestion=model["question"], brseReader=model["reader"])
    root = ET.SubElement(m, "root")
    ET.SubElement(root, "mxCell", id="0")
    ET.SubElement(root, "mxCell", id="1", parent="0")
    seen, kinds, unsourced = set(), {}, []

    def add_vertex(item, style, x, y, w, h):
        if item["id"] in seen or item["id"] in ("0", "1"):
            raise ValueError(f"duplicate or reserved id {item['id']!r}")
        seen.add(item["id"])
        c = ET.SubElement(root, "mxCell", id=item["id"], value=item.get("label", ""), style=style, vertex="1", parent="1")
        ET.SubElement(c, "mxGeometry", x=str(round(x)), y=str(round(y)), width=str(round(w)), height=str(round(h)),
                      **{"as": "geometry"})

    used_status = set()
    bottom, width = 0, 0
    if layout == "swimlane":
        lay = swimlane_positions(model)
        for lb in lay["lanes"]:
            add_vertex(lb, LANE_STYLE, lb["x"], lb["y"], lb["w"], lb["h"])
        bottom, width = lay["bottom"], lay["width"]
    if model.get("title"):
        add_vertex({"id": "brse-title", "label": model["title"]}, PLAIN["title"] + "brseKind=title;", 0, 0, 900, 40)
    for item in model.get("groups", []):
        style, w, h = node_style(item["kind"])
        add_vertex(item, style, item.get("x", 0), item.get("y", 0), item.get("w", w), item.get("h", h))
    for i, item in enumerate(model.get("nodes", [])):
        style, w, h = node_style(item["kind"])
        status = effective_status(item, unsourced)
        style = with_status(style, status, item["kind"])
        used_status.add(status)
        kinds[item["id"]] = item["kind"]
        if layout == "swimlane":
            x, y, w, h = lay["nodes"][item["id"]]
        elif layout == "auto":
            x, y = (i % 5) * 220, (i // 5) * 140  # replaced by the ELK layout below
        add_vertex(item, style, x, y, w, h)
        bottom = max(bottom, y + h)
        width = max(width, x + w)
    for i, e in enumerate(model.get("edges", [])):
        for end in ("source", "target"):
            if e[end] not in seen:
                raise ValueError(f"edge {i}: unknown {end} {e[end]!r}")
        e.setdefault("id", f"e{i}")
        status = effective_status(e, unsourced)
        style = with_status(EDGE_STYLE, status, "", edge=True)
        used_status.add(status)
        c = ET.SubElement(root, "mxCell", id=e["id"], value=e.get("label", ""), style=style,
                          edge="1", parent="1", source=e["source"], target=e["target"])
        g = ET.SubElement(c, "mxGeometry", relative="1", **{"as": "geometry"})
        if e.get("points"):
            arr = ET.SubElement(g, "Array", **{"as": "points"})
            for x, y in e["points"]:
                ET.SubElement(arr, "mxPoint", x=str(x), y=str(y))
    used_status.discard(None)
    if used_status and model.get("legend", True) and layout != "auto":
        ly = bottom + 30
        add_vertex({"id": "brse-legend-title", "label": "凡例 / Legend"}, PLAIN["note"] + "fontStyle=1;brseKind=legend;",
                   0, ly, 200, 24)
        for k, st in enumerate(s for s in STATUS if s in used_status):
            add_vertex({"id": f"brse-legend-{st}", "label": STATUS[st][2]},
                       SEMANTIC["step"][0] + STATUS[st][0] + "brseKind=legend;", 220 + k * 190, ly - 6, 170, 36)
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    Path(out).write_text(ET.tostring(mx, encoding="unicode"), encoding="utf-8")
    if layout == "auto":
        bake_layout(out, model.get("direction", "RIGHT"))
    sources_md, claims = source_outputs(model)
    Path(str(out) + ".sources.md").write_text(sources_md, encoding="utf-8")
    Path(str(out) + ".claims.json").write_text(json.dumps(claims, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"file": str(out), "layout": layout, "nodes": len(seen), "edges": len(model.get("edges", [])),
            "statuses": sorted(used_status), "unsourced": unsourced,
            "sources_table": str(out) + ".sources.md", "claims": str(out) + ".claims.json"}


def effective_status(item: dict, unsourced: list):
    ref = item.get("ref") or {}
    if not (ref.get("file") and ref.get("quote")):
        unsourced.append(item.get("id") or f"{item.get('source')}->{item.get('target')}")
        return "unconfirmed"
    return item.get("status")


def source_outputs(model: dict):
    labels = {n["id"]: n.get("label", n["id"]) for n in model.get("nodes", [])}
    rows = ["| # | Element | Source (file · part) | Quote |", "|---|---|---|---|"]
    claims = []
    items = [("box", n, labels[n["id"]]) for n in model.get("nodes", [])] + \
            [("arrow", e, f"{labels.get(e['source'], e['source'])} → {labels.get(e['target'], e['target'])}"
              + (f" ({e['label']})" if e.get("label") else "")) for e in model.get("edges", [])]
    for i, (kind, it, name) in enumerate(items, 1):
        ref = it.get("ref") or {}
        name = re.sub(r"<[^>]+>", " ", name)
        if ref.get("file") and ref.get("quote"):
            rows.append(f"| {i} | {kind}: {name} | {ref['file']} · {ref.get('part', '')} | {ref['quote']} |")
            claims.append({"claim": f"{kind}: {name}", "file": ref["file"],
                           "locator": {"part": ref["part"]} if ref.get("part") else {}, "expect": ref["quote"]})
        else:
            rows.append(f"| {i} | {kind}: {name} | **no source — drawn as unconfirmed** | |")
    return "\n".join(rows) + "\n", claims


def bake_layout(path, direction):
    _, config = brse_common.workspace(".")
    exe = config.get("tools", {}).get("paths", {}).get("drawio") or shutil.which("drawio")
    if not exe:
        raise RuntimeError("layout 'auto' needs the draw.io CLI — use 'swimlane' or 'manual', or install draw.io")
    lay = json.dumps([{"layout": "elkLayered", "config": {
        "elk.direction": direction, "elk.spacing.nodeNode": "50",
        "elk.layered.spacing.nodeNodeBetweenLayers": "90", "elk.edgeRouting": "ORTHOGONAL"}}])
    src = Path(path).resolve()
    stage = Path(tempfile.mkdtemp(prefix="brse-drawio-", dir=Path.home()))
    try:
        shutil.copy2(src, stage / "in.drawio")
        subprocess.run([exe, "-x", "-f", "xml", "--layout", lay, "-o", str(stage / "out.drawio"), str(stage / "in.drawio")],
                       capture_output=True, text=True, timeout=180)
        if not (stage / "out.drawio").is_file():
            raise RuntimeError("draw.io layout produced no file")
        shutil.copy2(stage / "out.drawio", src)
    finally:
        shutil.rmtree(stage, ignore_errors=True)


# ---------- acceptance criteria ----------
FLOW_KINDS = {"step", "decision", "start", "end"}
SYSTEM_KINDS = {"system", "external-system", "module", "datastore", "device", "equipment", "file"} | set(ICONS) | set(CLIENTS)
SKIP_KINDS = {"lane", "legend", "title", "note", "box", "todo", "actor"} | set(GROUPS)
MAX_ELEMENTS = 15
BLOCKING_LINT = {"overlap", "long-label", "mixed-language-label", "unlabeled-interface", "orphan",
                 "dangling-edge", "loose-edge"}


def norm_label(text: str) -> str:
    import unicodedata
    return re.sub(r"\s+", "", unicodedata.normalize("NFKC", text or "")).lower()


def diagram_elements(doc):
    """(nodes, edges): nodes = [{id, kind, status, label, x, y}], edges = [{id, source, target, label, status}]."""
    nodes, edges = [], []
    for c in cells(doc):
        style = c.get("style", "")
        kind = (re.search(r"brseKind=([\w-]+)", style) or [None, None])[1]
        status = (re.search(r"brseStatus=([\w-]+)", style) or [None, None])[1]
        if c.get("edge") == "1":
            edges.append({"id": c.get("id"), "source": c.get("source"), "target": c.get("target"),
                          "label": label(c), "status": status})
        elif c.get("vertex") == "1":
            g = geometry(c) or (0, 0, 0, 0)
            nodes.append({"id": c.get("id"), "kind": kind, "status": status, "label": label(c), "x": g[0], "y": g[1]})
    return nodes, edges


def cmd_check(path, changes=None) -> dict:
    """Criteria 1, 2, 3, 5, 6, 7 by machine; 4 and 8 need a reviewer (see reader-test)."""
    doc = load(path)
    model = doc.find(".//mxGraphModel")
    nodes, edges = diagram_elements(doc)
    content = [n for n in nodes if n["kind"] not in SKIP_KINDS and not (n["id"] or "").startswith("brse-")]
    crit = {}
    has_title = any(n["kind"] == "title" for n in nodes)
    crit["1_purpose"] = {"pass": bool(model.get("brseQuestion")) and has_title,
                         "detail": {"question": model.get("brseQuestion"), "reader": model.get("brseReader"),
                                    "title": has_title}}
    flow = sorted({n["kind"] for n in content if n["kind"] in FLOW_KINDS})
    system = sorted({n["kind"] for n in content if n["kind"] in SYSTEM_KINDS})
    crit["2_one_view"] = {"pass": not (flow and system),
                          "detail": "mixes business-flow steps and system parts" if flow and system else
                          ("business flow" if flow else "system view")}
    claims_file = Path(str(path) + ".claims.json")
    sources_file = Path(str(path) + ".sources.md")
    if claims_file.is_file():
        spec = importlib.util.spec_from_file_location("vc", brse_common.ROOT / "scripts" / "verify-claims.py")
        vc = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(vc)
        root, _ = brse_common.workspace(".")
        root = root or Path(".").resolve()
        convert = vc.converter()
        results = [vc.check(c, root, convert) for c in json.loads(claims_file.read_text(encoding="utf-8"))]
        bad = [r for r in results if r["status"] != "ok"]
        unsourced = sources_file.read_text(encoding="utf-8").count("no source") if sources_file.is_file() else 0
        crit["3_correct"] = {"pass": not bad, "detail": {"claims_checked": len(results), "not_ok": bad,
                                                         "drawn_as_unconfirmed": unsourced}}
    else:
        crit["3_correct"] = {"pass": False, "detail": "no claims file — build the diagram with drawio-tool.py build "
                                                      "(every element with a ref) or list its sources by hand"}
    layout = model.get("brseLayout") or model.get("brseTemplate")
    crit["5_layout"] = {"pass": layout in ("swimlane", "auto") or bool(model.get("brseTemplate")),
                        "detail": layout or "positions not computed (hand-placed)"}
    findings = [f for f in cmd_lint(path) if f["rule"] in BLOCKING_LINT]
    crit["6_readable"] = {"pass": len(content) <= MAX_ELEMENTS and not findings,
                          "detail": {"elements": len(content), "max": MAX_ELEMENTS, "problems": findings}}
    marked = {n["id"]: n["status"] for n in content if n["status"]}
    marked.update({e["id"]: e["status"] for e in edges if e["status"]})
    marked = {k: v for k, v in marked.items() if v != "unconfirmed"}
    if changes is None:
        crit["7_changes"] = {"pass": not marked,
                             "detail": "statuses drawn but no change table given (--changes)" if marked else "no changes drawn"}
    else:
        want = {c["id"]: c["status"] for c in changes}
        crit["7_changes"] = {"pass": want == marked, "detail": {
            "in_table_not_drawn": sorted(set(want) - set(marked)),
            "drawn_not_in_table": sorted(set(marked) - set(want)),
            "status_differs": sorted(k for k in set(want) & set(marked) if want[k] != marked[k])}}
    crit["4_complete"] = {"pass": None, "detail": "reviewer: compare the sources table with the source documents"}
    crit["8_reader_test"] = {"pass": None, "detail": "run drawio-tool.py reader-test, then --score"}
    return {"pass": all(c["pass"] for c in crit.values() if c["pass"] is not None), "criteria": crit}


def expected_reading(path) -> dict:
    doc = load(path)
    nodes, _ = diagram_elements(doc)
    lanes = [n for n in nodes if n["kind"] == "lane"]
    content = [n for n in nodes if n["kind"] not in SKIP_KINDS and not (n["id"] or "").startswith("brse-")]
    who = [n["label"] for n in sorted(lanes, key=lambda n: n["y"])] or \
          [n["label"] for n in content if n["kind"] in SYSTEM_KINDS | {"actor"}]
    steps = [n["label"] for n in sorted(content, key=lambda n: (n["x"], n["y"])) if n["kind"] in FLOW_KINDS]
    by_status = {st: sorted(n["label"] for n in content if n["status"] == st) for st in STATUS}
    return {"who": who, "steps_in_order": steps, **by_status}


def make_reader_test(path) -> dict:
    model = load(path).find(".//mxGraphModel")
    prompt = f"""You see ONLY the attached image of a diagram — no other document. Answer from the image alone.
If something is not readable on the image, leave it out; do not guess.

Answer with ONLY this JSON:
{{"question_answered": "<what question does this diagram answer, in one sentence>",
  "who": ["<each person, team or system that has its own lane or box, as written>"],
  "steps_in_order": ["<each step, as written, in the order they happen>"],
  "changed": ["<elements marked as changed>"], "new": ["<marked as new>"],
  "removed": ["<marked as removed>"], "unconfirmed": ["<marked as to confirm>"]}}
"""
    p = Path(str(path) + ".reader-test.md")
    p.write_text(prompt, encoding="utf-8")
    return {"prompt_file": str(p), "image": "export the diagram to PNG and give ONLY that image + prompt to a "
            "fresh reviewer (the plugin's reviewer agent, or a second model); save its JSON and run "
            "drawio-tool.py reader-test <file> --score <answers.json>",
            "intended_question": model.get("brseQuestion")}


def score_reader_test(path, answers: dict) -> dict:
    exp = expected_reading(path)
    out, ok = {}, True

    def found(lbl, pool):
        n = norm_label(lbl)
        return any(n and (n in norm_label(p) or norm_label(p) in n) for p in pool)

    for key in ["who", "steps_in_order"] + list(STATUS):
        want, got = exp.get(key, []), answers.get(key, [])
        missed = [w for w in want if not found(w, got)]
        extra = [g for g in got if not found(g, want)] if key in STATUS else []
        out[key] = {"expected": want, "missed": missed, "wrongly_seen": extra}
        if missed or extra:
            ok = False
    order_got = [g for g in answers.get("steps_in_order", []) if found(g, exp["steps_in_order"])]
    pos = [next(i for i, w in enumerate(exp["steps_in_order"]) if found(w, [g])) for g in order_got]
    swaps = sum(1 for a, b in zip(pos, pos[1:]) if b < a)
    out["order_inversions"] = swaps
    ok = ok and swaps == 0
    return {"pass": ok, "reader_understood": out, "question_answered": answers.get("question_answered"),
            "note": "every 'missed' or 'wrongly_seen' item is a place the image does not say what it should"}


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
                for mgm in doc.iter("mxGraphModel"):
                    mgm.set("brseTemplate", name)
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_text(ET.tostring(doc, encoding="unicode"), encoding="utf-8")
                out = {"template": name, "file": str(dest), "cells": len(list(cells(doc)))}
        elif cmd == "kinds":
            out = {"semantic": sorted(SEMANTIC), "aws": sorted(ICONS), "clients": sorted(CLIENTS),
                   "groups": sorted(GROUPS), "plain": sorted(PLAIN), "statuses": sorted(STATUS),
                   "layouts": ["manual", "swimlane", "auto"]}
        elif cmd == "build":
            out = cmd_build(json.loads(Path(args[1]).read_text(encoding="utf-8")), args[2])
        elif cmd == "cells":
            out = cmd_cells(args[1])
        elif cmd == "edit":
            out = cmd_edit(args[1], json.loads(Path(args[2]).read_text(encoding="utf-8")), args[3])
        elif cmd == "lint":
            out = {"findings": cmd_lint(args[1])}
        elif cmd == "check":
            changes = json.loads(Path(args[args.index("--changes") + 1]).read_text(encoding="utf-8")) \
                if "--changes" in args else None
            out = cmd_check(args[1], changes)
            if not out["pass"]:
                print(json.dumps(out, ensure_ascii=False, indent=2))
                sys.exit(1)
        elif cmd == "reader-test":
            if "--score" in args:
                i = args.index("--score")
                out = score_reader_test(args[1], json.loads(Path(args[i + 1]).read_text(encoding="utf-8")))
                if not out["pass"]:
                    print(json.dumps(out, ensure_ascii=False, indent=2))
                    sys.exit(1)
            else:
                out = make_reader_test(args[1])
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
