"""scene3d: compact grid from a diagram, and placement from a site layout drawing."""
import pytest

from brse.diagram import scene3d

EDGES = [{"source": "a", "target": "b"}, {"source": "b", "target": "c"}]
SCENES = [{"title": "flow", "edges": ["e0", "e1"]}]


def test_grid_keeps_order_but_not_drawio_gaps():
    # draw.io put these 360 apart (room for labels); 3D keeps only the order, one column apart
    pos = {"a": (100, 50), "b": (460, 50), "c": (820, 52)}
    model = {"nodes": [{"id": k, "kind": "equipment"} for k in "abc"], "edges": EDGES, "scenes": SCENES}
    xs = [n["x"] for n in scene3d.scene_data(pos, model, "ja")["nodes"]]
    assert xs == [0, scene3d.COL, 2 * scene3d.COL]


def test_floor_plan_places_nodes_and_zones_by_fraction():
    model = {"floor": {"size": [4000, 1000]},
             "lanes": [{"id": "ctl", "label": "制御", "level": 1}],
             "zones": [{"label": "入荷", "rect": [.5, .5, .5, .5]}],
             "nodes": [{"id": "a", "kind": "equipment", "at": [.25, .5]},
                       {"id": "b", "kind": "equipment", "at": [.75, .75]},
                       {"id": "c", "kind": "system", "at": [.5, .1], "lane": "ctl"}],
             "edges": EDGES, "scenes": SCENES}
    d = scene3d.scene_data({}, model, "ja")
    a, b, c = d["nodes"]
    assert (a["x"], a["z"], a["y"]) == (1000, 500, 0)
    assert (b["x"], b["z"]) == (3000, 750)
    assert c["y"] == scene3d.LEVEL_HEIGHT
    assert d["zones"][0] == {"label": "入荷", "level": 0, "x": 2000, "z": 500, "w": 2000, "d": 500}
    assert "src" not in d["floor"]          # the drawing itself is never embedded


def test_floor_plan_rejects_missing_or_out_of_range_positions():
    model = {"floor": {"size": [100, 100]}, "edges": EDGES, "scenes": SCENES,
             "nodes": [{"id": "a", "kind": "equipment", "at": [.1, .1]},
                       {"id": "b", "kind": "equipment"},
                       {"id": "c", "kind": "equipment", "at": [1.4, .2]}]}
    with pytest.raises(ValueError, match=r"\['b', 'c'\]"):
        scene3d.scene_data({}, model, "ja")


def test_a_lone_node_must_be_connected_or_explained():
    model = {"floor": {"size": [100, 100]}, "edges": EDGES, "scenes": SCENES,
             "nodes": [{"id": k, "kind": "equipment", "at": [.1, .1]} for k in "abc"]
                      + [{"id": "lone", "kind": "equipment", "at": [.5, .5]},
                         {"id": "placed", "kind": "equipment", "at": [.6, .6], "alone": "role not in the documents"}]}
    assert scene3d.not_in_any_flow(scene3d.scene_data({}, model, "ja")) == ["lone"]
