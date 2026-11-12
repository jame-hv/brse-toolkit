"""A self-contained interactive 3D page (Three.js) of a diagram built with `drawio-tool build`.

Usage: brse.py drawio-tool scene3d <file.drawio> <model.json> <out.html> [--lang ja|vi|en]
Positions come from the laid-out .drawio, so nothing is placed by hand. The flow
comes from model.json: "scenes": [{"title": "...", "edges": ["e0", "e1", ...]}] in the
order things happen (edge ids are "id", else e<position in the edges list).
Every step shows its source quote; an element without a ref is shown as unconfirmed.
For a real site, add "floor": {"size": [w, d], "ref": ...}, "at": [x, y] on every node and
"zones": [{"label", "rect": [x, y, w, h]}], all read off the site's layout drawing as fractions:
machines then stand where they are, on a plain floor (the drawing itself is not shown).
Click a machine or its pin: the camera flies to it and its links and sources are listed.
Three.js is embedded in the file: it opens offline, by double-click, with no server.
"""
import base64
import json
from pathlib import Path

VENDOR = Path(__file__).resolve().parent / "vendor" / "three-0.160.0"
TEMPLATE = Path(__file__).resolve().parent / "scene3d.html"
# grid in scene units; the largest model (stacker, cart) is about 160 wide, so a 250 cell leaves a gap
COL = 250
ROW = 210
LANE_GAP = 60
LABEL_ROOM = 260   # floor left of the first column, where the lane name sits
LEVEL_HEIGHT = 330


def _data_url(path: Path) -> str:
    return "data:text/javascript;base64," + base64.b64encode(path.read_bytes()).decode()


def import_map() -> str:
    return json.dumps({"imports": {"three": _data_url(VENDOR / "three.module.min.js"),
                                   "three/OrbitControls": _data_url(VENDOR / "OrbitControls.js"),
                                   "three/CSS2DRenderer": _data_url(VENDOR / "CSS2DRenderer.js")}})


def _ranks(values, tol=30.0) -> dict:
    """Group nearly equal coordinates: {value: index of its column or row}."""
    out, last, i = {}, None, -1
    for v in sorted(set(values)):
        if last is None or v - last > tol:
            i += 1
        out[v], last = i, v
    return out


def _edges_and_scenes(model: dict):
    edges = [{"id": e.get("id", f"e{i}"), "source": e["source"], "target": e["target"],
              "label": e.get("label", ""), "ref": e.get("ref"), "carries": e.get("carries", "data")}
             for i, e in enumerate(model.get("edges", []))]
    known = {e["id"] for e in edges}
    scenes = model.get("scenes") or []
    if not scenes:
        raise ValueError('model needs "scenes": [{"title", "edges": [...]}] — the order things happen')
    for s in scenes:
        unknown = [i for i in s["edges"] if i not in known]
        if unknown:
            raise ValueError(f"scene {s.get('title')!r}: unknown edges {unknown}; known: {sorted(known)}")
    return edges, scenes


def _on_floor_plan(model: dict, lang: str) -> dict:
    """"floor": {"size": [width, depth], "ref": {file, part, quote}}: the site's layout drawing, read by eye.
    Every node has "at": [x, y] and every zone "rect": [x, y, w, h], as fractions of that drawing
    (0..1 from its top-left). The drawing itself is not shown: only plain zones and the machines.
    Control systems ("level": 1 lane) float above the place they serve."""
    floor = model["floor"]
    width, depth = (float(v) for v in floor["size"])
    frac = lambda v: len(v) and all(0 <= x <= 1 for x in v)
    bad = [n["id"] for n in model["nodes"] if len(n.get("at") or []) != 2 or not frac(n["at"])]
    bad += [z.get("label") for z in model.get("zones", []) if len(z.get("rect") or []) != 4 or not frac(z["rect"])]
    if bad:
        raise ValueError(f'with "floor", every node needs "at": [x, y] and every zone "rect": [x, y, w, h], '
                         f'fractions 0..1 of the layout drawing; wrong or missing: {bad}')
    lanes = {l["id"]: l for l in model.get("lanes", [])}
    edges, scenes = _edges_and_scenes(model)
    nodes = [{"id": n["id"], "label": n.get("label", ""), "kind": n["kind"], "icon": n.get("icon", ""),
              "model": n.get("model", ""), "ref": n.get("ref"), "at_ref": n.get("at_ref"), "pin": i,
              "original": n.get("original"), "detail": n.get("detail"), "change": n.get("change"),
              "alone": n.get("alone"),
              "x": n["at"][0] * width, "y": lanes.get(n.get("lane"), {}).get("level", 0) * LEVEL_HEIGHT,
              "z": n["at"][1] * depth}
             for i, n in enumerate(model["nodes"], 1)]
    zones = [{"label": z["label"], "level": 0, "x": z["rect"][0] * width, "z": z["rect"][1] * depth,
              "w": z["rect"][2] * width, "d": z["rect"][3] * depth} for z in model.get("zones", [])]
    return {"title": model.get("title", ""), "lang": lang, "nodes": nodes, "edges": edges, "scenes": scenes,
            "zones": zones, "note": model.get("note", ""), "brief": model.get("brief"), "start": model.get("start_scene", 0), "floor": {"w": width, "d": depth, "ref": floor.get("ref")}}


def scene_data(positions: dict, model: dict, lang: str, boxes: dict = None) -> dict:
    """positions = {id: (centre x, centre y)} from the laid-out diagram.
    Only the order is kept: draw.io leaves room for a label under every icon, which in 3D is empty
    floor (a 4:1 strip), so nodes go on a compact grid of the diagram's columns and, per lane, rows.
    A lane with "level": 1 floats above the floor, centred over it (control systems above the machines)."""
    del boxes  # lane boxes are rebuilt from the grid
    if model.get("floor"):
        return _on_floor_plan(model, lang)
    edges, scenes = _edges_and_scenes(model)
    missing = [n["id"] for n in model["nodes"] if n["id"] not in positions]
    if missing:
        raise ValueError(f"nodes not in the diagram: {missing}")
    lanes = {l["id"]: l for l in model.get("lanes", [])}
    level = lambda lane: lanes.get(lane, {}).get("level", 0)
    col = _ranks([positions[n["id"]][0] for n in model["nodes"]])
    members = {}
    for n in model["nodes"]:
        members.setdefault(n.get("lane", ""), []).append(n)
    order = sorted(members, key=lambda k: min(positions[n["id"]][1] for n in members[k]))
    z_of, spans, depth = {}, {}, {0: 0.0, 1: 0.0}
    for k in order:                       # lanes stacked top to bottom as in the diagram, per level
        lv = 1 if level(k) else 0
        row = _ranks([positions[n["id"]][1] for n in members[k]])
        rows = max(row.values()) + 1
        start = depth[lv]
        for n in members[k]:
            z_of[n["id"]] = start + (row[positions[n["id"]][1]] + .5) * ROW
        spans[k] = (lv, start, rows * ROW)
        depth[lv] = start + rows * ROW + LANE_GAP
    shift = (depth[0] - depth[1]) / 2 if depth[1] else 0.0   # upper level centred over the floor
    for n in model["nodes"]:
        if level(n.get("lane")):
            z_of[n["id"]] += shift
    nodes = [{"id": n["id"], "label": n.get("label", ""), "kind": n["kind"], "icon": n.get("icon", ""),
              "model": n.get("model", ""), "ref": n.get("ref"), "pin": i, "alone": n.get("alone"),
              "x": col[positions[n["id"]][0]] * COL, "y": level(n.get("lane")) * LEVEL_HEIGHT,
              "z": z_of[n["id"]]}
             for i, n in enumerate(model["nodes"], 1)]
    right = max(col.values()) * COL + COL / 2
    zones = [{"label": lanes[k]["label"], "level": lv, "x": -LABEL_ROOM, "w": right + LABEL_ROOM,
              "z": start + (shift if lv else 0), "d": d}
             for k, (lv, start, d) in spans.items() if k in lanes]
    return {"title": model.get("title", ""), "lang": lang, "nodes": nodes, "edges": edges, "scenes": scenes,
            "zones": zones, "note": model.get("note", ""), "brief": model.get("brief"),
            "start": model.get("start_scene", 0)}


def render(data: dict) -> str:
    safe = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    title = data["title"].replace("&", "&amp;").replace("<", "&lt;")
    return (TEMPLATE.read_text(encoding="utf-8").replace("__LANG__", data["lang"]).replace("__TITLE__", title)
            .replace("__IMPORTMAP__", import_map()).replace("__DATA__", safe))


def not_in_any_scene(data: dict) -> list:
    used = {i for s in data["scenes"] for i in s["edges"]}
    return [e["id"] for e in data["edges"] if e["id"] not in used]


def not_in_any_flow(data: dict) -> list:
    """Machines, people and terminals that no edge touches. Each must be connected, or carry
    "alone": the reason it stands alone (e.g. the documents read do not give its role)."""
    used = {x for e in data["edges"] for x in (e["source"], e["target"])}
    return [n["id"] for n in data["nodes"] if n["id"] not in used and not n.get("alone")]
