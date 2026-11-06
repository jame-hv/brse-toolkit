import base64
import json
import struct
import urllib.parse
import zlib

from conftest import run_script

MODEL = """<mxGraphModel><root><mxCell id="0"/><mxCell id="1" parent="0"/>
<mxCell id="grp" value="AWS Cloud" style="shape=mxgraph.aws4.group;container=1;" vertex="1" parent="1"><mxGeometry x="0" y="0" width="400" height="200" as="geometry"/></mxCell>
<mxCell id="in1" value="S3" style="shape=mxgraph.aws4.s3;" vertex="1" parent="1"><mxGeometry x="20" y="40" width="60" height="60" as="geometry"/></mxCell>
<mxCell id="app" value="App" style="rounded=0;" vertex="1" parent="1"><mxGeometry x="500" y="40" width="80" height="60" as="geometry"/></mxCell>
<mxCell id="lone" value="Lonely" style="rounded=0;" vertex="1" parent="1"><mxGeometry x="700" y="40" width="80" height="60" as="geometry"/></mxCell>
<mxCell id="bump" value="Bump" style="rounded=0;" vertex="1" parent="1"><mxGeometry x="540" y="70" width="80" height="60" as="geometry"/></mxCell>
<mxCell id="e1" edge="1" parent="1" source="app" target="grp"><mxGeometry relative="1" as="geometry"/></mxCell>
<mxCell id="e2" edge="1" parent="1" source="app" target="bump"><mxGeometry relative="1" as="geometry"/></mxCell>
<mxCell id="e3" edge="1" parent="1" source="app" target="ghost"><mxGeometry relative="1" as="geometry"/></mxCell>
</root></mxGraphModel>"""


def compressed_mxfile(model: str) -> str:
    c = zlib.compressobj(9, zlib.DEFLATED, -15)
    raw = c.compress(urllib.parse.quote(model).encode()) + c.flush()
    return f'<mxfile><diagram name="p">{base64.b64encode(raw).decode()}</diagram></mxfile>'


def fake_asar(path, files: dict):
    """Minimal Electron asar: 16-byte pickle header + JSON index + concatenated data."""
    tree, data, off = {"files": {}}, b"", 0
    for name, content in files.items():
        node = tree
        parts = name.split("/")
        for p in parts[:-1]:
            node = node["files"].setdefault(p, {"files": {}})
        node["files"][parts[-1]] = {"size": len(content), "offset": str(off)}
        data += content
        off += len(content)
    js = json.dumps(tree).encode()
    pad = (4 - len(js) % 4) % 4
    header = struct.pack("<4I", 4, len(js) + pad + 8, len(js) + pad + 4, len(js)) + js + b"\0" * pad
    path.write_bytes(header + data)


def test_templates_listed_and_extracted_from_asar_decompressed(tmp_path):
    asar = tmp_path / "app.asar"
    pre = "drawio/src/main/webapp/templates/"
    fake_asar(asar, {pre + "cloud/aws/aws_1.xml": compressed_mxfile(MODEL).encode(),
                     pre + "cloud/aws/aws_1.png": b"png", pre + "index.xml": b"<x/>"})
    cfg = tmp_path / "cfg" / "brse-toolkit"
    cfg.mkdir(parents=True)
    (cfg / "config.json").write_text(json.dumps({"tools": {"paths": {"drawio-asar": str(asar)}}}))
    names = json.loads(run_script("drawio-tool.py", "templates", "aws", tmp=tmp_path, cwd=tmp_path).stdout)
    assert names == ["cloud/aws/aws_1"]
    out = json.loads(run_script("drawio-tool.py", "template", "cloud/aws/aws_1", tmp_path / "t.drawio",
                                tmp=tmp_path, cwd=tmp_path).stdout)
    assert out["cells"] == 8 and "<mxGraphModel" in (tmp_path / "t.drawio").read_text()


def test_lint_finds_orphan_overlap_dangling_but_not_contained_icons(tmp_path):
    (tmp_path / "d.drawio").write_text(compressed_mxfile(MODEL))
    f = json.loads(run_script("drawio-tool.py", "lint", tmp_path / "d.drawio", tmp=tmp_path).stdout)["findings"]
    rules = {(x["rule"], x.get("label") or tuple(x.get("ids", [])) or x.get("id")) for x in f}
    assert ("orphan", "Lonely") in rules
    assert ("overlap", ("app", "bump")) in rules
    assert any(r == "dangling-edge" for r, _ in rules)
    assert not any(r == "orphan" and l == "S3" for r, l in rules)  # inside a connected group by position


def test_edit_relabels_deletes_group_with_contents_and_connects(tmp_path):
    (tmp_path / "d.drawio").write_text(compressed_mxfile(MODEL))
    (tmp_path / "c.json").write_text(json.dumps({
        "set": {"app": "Laravel app", "nope": "x"}, "delete": ["grp"],
        "add": [{"id": "db", "clone": "app", "label": "RDS", "x": 900}],
        "connect": [{"source": "app", "target": "db", "label": "SQL"}]}))
    r = json.loads(run_script("drawio-tool.py", "edit", tmp_path / "d.drawio", tmp_path / "c.json",
                              tmp_path / "o.drawio", tmp=tmp_path).stdout)
    assert set(r["deleted"]) == {"grp", "in1", "e1"} and r["missing_ids"] == ["nope"]
    cells = {c["id"]: c for c in json.loads(run_script("drawio-tool.py", "cells", tmp_path / "o.drawio", tmp=tmp_path).stdout)}
    assert cells["app"]["label"] == "Laravel app" and cells["db"]["label"] == "RDS"
    assert any(c.get("source") == "app" and c.get("target") == "db" for c in cells.values())


def test_build_without_computed_layout_is_refused(tmp_path):
    (tmp_path / "m.json").write_text(json.dumps({"nodes": [{"id": "a", "kind": "system", "x": 10, "y": 10}]}))
    r = run_script("drawio-tool.py", "build", tmp_path / "m.json", tmp_path / "a.drawio", tmp=tmp_path)
    assert r.returncode == 1 and "not set by hand" in r.stdout


def test_build_rejects_unknown_kind_and_bad_edges(tmp_path):
    lanes = [{"id": "l", "label": "L"}]
    (tmp_path / "m.json").write_text(json.dumps({"layout": "swimlane", "lanes": lanes,
                                                 "nodes": [{"id": "x", "kind": "mainframe", "lane": "l"}]}))
    r = run_script("drawio-tool.py", "build", tmp_path / "m.json", tmp_path / "a.drawio", tmp=tmp_path)
    assert r.returncode == 1 and "unknown kind" in r.stdout
    (tmp_path / "m.json").write_text(json.dumps({"layout": "swimlane", "lanes": lanes,
                                                 "nodes": [{"id": "x", "kind": "system", "lane": "l"}],
                                                 "edges": [{"source": "x", "target": "y"}]}))
    r = run_script("drawio-tool.py", "build", tmp_path / "m.json", tmp_path / "a.drawio", tmp=tmp_path)
    assert r.returncode == 1 and "unknown target" in r.stdout


REF = {"file": "docs/spec.txt", "part": "page 3", "quote": "仕分"}
SWIM = {"layout": "swimlane", "title": "現行業務フロー",
        "lanes": [{"id": "op", "label": "作業者"}, {"id": "wcs", "label": "WCS"}, {"id": "wms", "label": "WMS"}],
        "nodes": [{"id": "s1", "kind": "step", "label": "入荷", "lane": "op", "col": 0, "ref": REF},
                  {"id": "s2", "kind": "device", "label": "HTでJAN読取", "lane": "op", "col": 1, "ref": REF},
                  {"id": "s3", "kind": "system", "label": "仕分先を指示", "lane": "wcs", "col": 1, "ref": REF},
                  {"id": "s4", "kind": "step", "label": "重量検品", "lane": "op", "col": 2, "status": "changed", "ref": REF},
                  {"id": "s5", "kind": "system", "label": "実績受信", "lane": "wms", "col": 3, "status": "new", "ref": REF}],
        "edges": [{"source": "s1", "target": "s2", "ref": REF}, {"source": "s2", "target": "s3", "label": "JAN", "ref": REF},
                  {"source": "s3", "target": "s4", "ref": REF},
                  {"source": "s4", "target": "s5", "label": "実績", "status": "new", "ref": REF}]}


def build(tmp_path, model):
    (tmp_path / "m.json").write_text(json.dumps(model, ensure_ascii=False), encoding="utf-8")
    r = run_script("drawio-tool.py", "build", tmp_path / "m.json", tmp_path / "a.drawio", tmp=tmp_path)
    return r, (json.loads(r.stdout) if r.stdout.strip() else {})


def test_swimlane_positions_nodes_in_their_lane_and_column(tmp_path):
    r, out = build(tmp_path, SWIM)
    assert r.returncode == 0 and out["layout"] == "swimlane" and out["statuses"] == ["changed", "new"]
    cells = {c["id"]: c for c in json.loads(run_script("drawio-tool.py", "cells", tmp_path / "a.drawio", tmp=tmp_path).stdout)}
    assert {"op", "wcs", "wms", "brse-legend-changed", "brse-legend-new"} <= set(cells)
    import xml.etree.ElementTree as ET
    geo = {c.get("id"): c.find("mxGeometry").attrib for c in ET.parse(tmp_path / "a.drawio").iter("mxCell")
           if c.find("mxGeometry") is not None and c.get("vertex") == "1"}
    lane_y = {l: (float(geo[l]["y"]), float(geo[l]["y"]) + float(geo[l]["height"])) for l in ("op", "wcs", "wms")}
    for nid, lane in (("s1", "op"), ("s2", "op"), ("s3", "wcs"), ("s4", "op"), ("s5", "wms")):
        y = float(geo[nid]["y"])
        assert lane_y[lane][0] <= y <= lane_y[lane][1], nid
    assert float(geo["s2"]["x"]) == float(geo["s3"]["x"]) - (float(geo["s2"]["width"]) - float(geo["s3"]["width"])) / 2
    assert float(geo["s1"]["x"]) < float(geo["s2"]["x"]) < float(geo["s4"]["x"]) < float(geo["s5"]["x"])
    lint = json.loads(run_script("drawio-tool.py", "lint", tmp_path / "a.drawio", tmp=tmp_path).stdout)["findings"]
    assert lint == [], lint


def test_lint_flags_long_and_mixed_labels_and_silent_interfaces(tmp_path):
    model = {"layout": "swimlane", "lanes": [{"id": "l", "label": "L"}],
             "nodes": [{"id": "a", "kind": "system", "label": "WMS (テクニカル・ユニオン) Nhận đơn từ cửa hàng", "lane": "l", "col": 0, "ref": REF},
                       {"id": "b", "kind": "system", "label": "WCS", "lane": "l", "col": 1, "ref": REF},
                       {"id": "c", "kind": "step", "label": "1<br>2<br>3<br>4", "lane": "l", "col": 2, "ref": REF}],
             "edges": [{"source": "a", "target": "b", "ref": REF}, {"source": "b", "target": "c", "label": "x", "ref": REF}]}
    r, _ = build(tmp_path, model)
    rules = {f["rule"] for f in json.loads(run_script("drawio-tool.py", "lint", tmp_path / "a.drawio", tmp=tmp_path).stdout)["findings"]}
    assert {"long-label", "mixed-language-label", "unlabeled-interface"} <= rules


def test_element_without_source_is_drawn_unconfirmed_and_listed(tmp_path):
    model = json.loads(json.dumps(SWIM))
    del model["edges"][3]["ref"]          # the new 実績 arrow has no source
    del model["nodes"][3]["ref"]          # the changed 重量検品 step has no source
    r, out = build(tmp_path, model)
    assert set(out["unsourced"]) == {"s4", "e3"}
    xml = (tmp_path / "a.drawio").read_text(encoding="utf-8")
    import re as _re
    s4 = _re.search(r'id="s4"[^>]*style="([^"]*)"|style="([^"]*)"[^>]*id="s4"', xml)
    assert "dashed=1" in "".join(g for g in s4.groups() if g)
    table = (tmp_path / "a.drawio.sources.md").read_text(encoding="utf-8")
    assert "no source — drawn as unconfirmed" in table and "重量検品" in table
    claims = json.loads((tmp_path / "a.drawio.claims.json").read_text(encoding="utf-8"))
    assert len(claims) == 7 and claims[0]["locator"] == {"part": "page 3"}


def test_unknown_lane_or_status_is_rejected(tmp_path):
    bad = json.loads(json.dumps(SWIM))
    bad["nodes"][0]["lane"] = "nope"
    r, _ = build(tmp_path, bad)
    assert r.returncode == 1 and "lane" in r.stdout
    bad = json.loads(json.dumps(SWIM))
    bad["nodes"][0]["status"] = "maybe"
    r, _ = build(tmp_path, bad)
    assert r.returncode == 1 and "unknown status" in r.stdout


def test_edit_brings_an_icon_over_from_another_diagram(tmp_path):
    (tmp_path / "base.drawio").write_text(compressed_mxfile(MODEL))
    other = MODEL.replace('id="app" value="App" style="rounded=0;"', 'id="scale" value="Scale" style="shape=mxgraph.aws4.iot_sensor;"')
    (tmp_path / "other.drawio").write_text(compressed_mxfile(other))
    (tmp_path / "c.json").write_text(json.dumps({"add": [
        {"id": "s1", "clone": "scale", "from": str(tmp_path / "other.drawio"), "label": "重量計", "x": 900, "y": 40},
        {"id": "s2", "clone": "nope", "from": str(tmp_path / "other.drawio")}]}))
    r = json.loads(run_script("drawio-tool.py", "edit", tmp_path / "base.drawio", tmp_path / "c.json",
                              tmp_path / "o.drawio", tmp=tmp_path).stdout)
    assert r["added"] == ["s1"] and r["missing_ids"] == [f"{tmp_path / 'other.drawio'}#nope"]
    xml = (tmp_path / "o.drawio").read_text(encoding="utf-8")
    assert "mxgraph.aws4.iot_sensor" in xml and "重量計" in xml
