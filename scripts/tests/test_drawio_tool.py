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


def test_build_from_model_then_lint_clean(tmp_path):
    model = {"name": "arch", "groups": [{"id": "cloud", "kind": "aws-cloud", "label": "AWS", "x": 200, "y": 0, "w": 600, "h": 300}],
             "nodes": [{"id": "pc", "kind": "pc", "label": "店舗PC", "x": 20, "y": 100},
                       {"id": "alb", "kind": "alb", "label": "ALB", "x": 260, "y": 100},
                       {"id": "app", "kind": "ec2", "label": "App", "x": 460, "y": 100},
                       {"id": "q", "kind": "todo", "label": "ワーカー（要確認）", "x": 620, "y": 200}],
             "edges": [{"source": "pc", "target": "alb", "label": "HTTPS"}, {"source": "alb", "target": "app"},
                       {"source": "app", "target": "q", "dashed": True, "points": [[560, 230]]}]}
    (tmp_path / "m.json").write_text(json.dumps(model, ensure_ascii=False), encoding="utf-8")
    out = json.loads(run_script("drawio-tool.py", "build", tmp_path / "m.json", tmp_path / "a.drawio", tmp=tmp_path).stdout)
    assert out["nodes"] == 5 and out["edges"] == 3
    lint = json.loads(run_script("drawio-tool.py", "lint", tmp_path / "a.drawio", tmp=tmp_path).stdout)["findings"]
    assert lint == []
    xml = (tmp_path / "a.drawio").read_text(encoding="utf-8")
    assert "resIcon=mxgraph.aws4.ec2" in xml and "dashed=1;" in xml and "mxPoint" in xml


def test_build_rejects_unknown_kind_and_bad_edges(tmp_path):
    (tmp_path / "m.json").write_text(json.dumps({"nodes": [{"id": "x", "kind": "mainframe"}]}))
    r = run_script("drawio-tool.py", "build", tmp_path / "m.json", tmp_path / "a.drawio", tmp=tmp_path)
    assert r.returncode == 1 and "unknown kind" in r.stdout
    (tmp_path / "m.json").write_text(json.dumps({"nodes": [{"id": "x", "kind": "ec2"}], "edges": [{"source": "x", "target": "y"}]}))
    r = run_script("drawio-tool.py", "build", tmp_path / "m.json", tmp_path / "a.drawio", tmp=tmp_path)
    assert r.returncode == 1 and "unknown target" in r.stdout
