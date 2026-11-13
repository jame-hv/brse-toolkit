"""Arrow routing for built diagrams: every arrow gets its own orthogonal path, written into the file.

draw.io computes an arrow's path only when it draws it, so a file without points cannot be checked for
arrows crossing labels or sharing a segment. Here each arrow is routed on a grid that treats every node and
every node's label as an obstacle (an arrow never enters a node through its own label), and a segment
already taken by another arrow costs so much that two arrows never run on top of each other.
"""
import heapq
import re

STEP = 10          # grid size in px
MARGIN = 12        # clearance kept around nodes and labels
BEND = 30          # cost of a turn: fewer turns win when lengths are close
SHARED = 400       # cost of running along a cell another arrow already runs along (same axis)
CROSS = 4          # cost of crossing another arrow
SIDES = {"top": (0.5, 0.0, 0, -1), "bottom": (0.5, 1.0, 0, 1), "left": (0.0, 0.5, -1, 0), "right": (1.0, 0.5, 1, 0)}
SPREAD = [0, -20, 20, -40, 40]  # port offsets along a side when several arrows use it


def text_width(text: str, size: int = 13) -> float:
    """Estimated rendered width: CJK characters are about one em, others about 0.6 em."""
    plain = re.sub(r"<[^>]+>", "", text or "")
    return sum(size if re.match(r"[　-鿿＀-￯]", ch) else size * 0.6 for ch in plain)


LABEL_MAX = 150    # an icon label wraps at this width (style labelWidth)


def label_lines(text, size=13) -> int:
    return max(1, -(-int(text_width(text, size)) // LABEL_MAX)) if text else 0


def label_box(box, text, size=13):
    """The label drawn under an icon (labelPosition=center, verticalLabelPosition=bottom, wrapped at LABEL_MAX)."""
    if not text:
        return None
    x, y, w, h = box
    tw = min(text_width(text, size), LABEL_MAX) + 8
    return (x + w / 2 - tw / 2, y + h, tw, label_lines(text, size) * size * 1.4 + 4)


def _cells(box, margin):
    x, y, w, h = box
    return (int((x - margin) // STEP), int((y - margin) // STEP),
            int((x + w + margin) // STEP), int((y + h + margin) // STEP))


def route_all(nodes: dict, labels: dict, edges: list, bounds) -> dict:
    """nodes: {id: (x, y, w, h)}; labels: {id: label box or None}; edges: [(edge id, source, target)];
    bounds: (x0, y0, x1, y1) the area arrows may use.
    → {edge id: {"exit": (fx, fy), "entry": (fx, fy), "points": [(x, y), ...]}}; an edge with no route is left out."""
    x0, y0, x1, y1 = bounds
    gx0, gy0, gx1, gy1 = int(x0 // STEP), int(y0 // STEP), int(x1 // STEP), int(y1 // STEP)
    blocked = set()
    for nid, box in list(nodes.items()) + [(k, v) for k, v in labels.items() if v]:
        cx0, cy0, cx1, cy1 = _cells(box, MARGIN)
        blocked |= {(i, j) for i in range(cx0, cx1 + 1) for j in range(cy0, cy1 + 1)}
    used = {}       # (i, j) -> set of axes ("h" / "v") already taken
    ports = {}      # (node, side) -> offsets used
    out = {}

    def port_points(nid, side):
        x, y, w, h = nodes[nid]
        fx, fy, dx, dy = SIDES[side]
        lb = labels.get(nid)
        for off in SPREAD:
            if off in ports.get((nid, side), set()):
                continue
            px, py = x + fx * w + (off if dy else 0), y + fy * h + (off if dx else 0)
            if (dx and not y < py < y + h) or (dy and not x < px < x + w):
                continue
            if lb and side == "bottom":
                continue  # the label sits under the node: never leave or enter through it
            reach = MARGIN + STEP
            cell = (int(round((px + dx * reach) / STEP)), int(round((py + dy * reach) / STEP)))
            return off, (px, py), cell, (fx + (off / w if dy else 0), fy + (off / h if dx else 0))
        return None

    for eid, s, t in edges:
        starts, goals = {}, {}
        for side in SIDES:
            p = port_points(s, side)
            if p and p[2] not in blocked and gx0 <= p[2][0] <= gx1 and gy0 <= p[2][1] <= gy1:
                starts[p[2]] = (side, p)
            q = port_points(t, side)
            if q and q[2] not in blocked and gx0 <= q[2][0] <= gx1 and gy0 <= q[2][1] <= gy1:
                goals[q[2]] = (side, q)
        if not starts or not goals:
            continue
        tx = sum(c[0] for c in goals) / len(goals)
        ty = sum(c[1] for c in goals) / len(goals)
        heap, best, prev = [], {}, {}
        for c, (side, _) in starts.items():
            d = (SIDES[side][2], SIDES[side][3])
            heapq.heappush(heap, (0, 0, c, d))
            best[(c, d)] = 0
        end = None
        while heap:
            _, g, c, d = heapq.heappop(heap)
            if g > best.get((c, d), 1e18):
                continue
            if c in goals:
                gd = SIDES[goals[c][0]]
                if d == (-gd[2], -gd[3]):
                    end = (c, d)
                    break
            for nd in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                if nd == (-d[0], -d[1]):
                    continue
                n = (c[0] + nd[0], c[1] + nd[1])
                if not (gx0 <= n[0] <= gx1 and gy0 <= n[1] <= gy1) or (n in blocked and n not in goals):
                    continue
                axis = "h" if nd[1] == 0 else "v"
                taken = used.get(n, set())
                cost = g + 1 + (BEND if nd != d else 0) + (SHARED if axis in taken else CROSS if taken else 0)
                if cost < best.get((n, nd), 1e18):
                    best[(n, nd)] = cost
                    prev[(n, nd)] = (c, d)
                    heapq.heappush(heap, (cost + abs(n[0] - tx) + abs(n[1] - ty), cost, n, nd))
        if not end:
            continue
        path, k = [], end
        while k in prev:
            path.append(k[0])
            k = prev[k]
        path.append(k[0])
        path.reverse()
        sside, sp = starts[path[0]]
        tside, tp = goals[path[-1]]
        for a, b in zip(path, path[1:]):
            axis = "h" if a[1] == b[1] else "v"
            used.setdefault(a, set()).add(axis)
            used.setdefault(b, set()).add(axis)
        ports.setdefault((s, sside), set()).add(sp[0])
        ports.setdefault((t, tside), set()).add(tp[0])
        # the drawn line: source port → path corners → target port, every segment horizontal or vertical
        pts = [(sp[1][0], sp[1][1])]
        sdx, sdy = SIDES[sside][2], SIDES[sside][3]
        first = (path[0][0] * STEP, path[0][1] * STEP)
        pts.append((sp[1][0], first[1]) if sdy else (first[0], sp[1][1]))
        pts += [(c[0] * STEP, c[1] * STEP) for c in path]
        tdx, tdy = SIDES[tside][2], SIDES[tside][3]
        last = (path[-1][0] * STEP, path[-1][1] * STEP)
        pts.append((tp[1][0], last[1]) if tdy else (last[0], tp[1][1]))
        pts.append((tp[1][0], tp[1][1]))
        out[eid] = {"exit": sp[3], "entry": tp[3], "points": corners(pts)[1:-1], "line": corners(pts)}
    return out


def corners(pts):
    """Drop repeated points and points in the middle of a straight run."""
    clean = []
    for p in pts:
        p = (round(p[0]), round(p[1]))
        if clean and p == clean[-1]:
            continue
        if len(clean) >= 2 and (clean[-2][0] == clean[-1][0] == p[0] or clean[-2][1] == clean[-1][1] == p[1]):
            clean[-1] = p
        else:
            clean.append(p)
    return clean


def label_position(line):
    """draw.io places an edge label at a relative x in [-1, 1] along the whole path: the middle of the
    longest segment keeps it on a straight run, away from corners."""
    segs = [(a, b, abs(b[0] - a[0]) + abs(b[1] - a[1])) for a, b in zip(line, line[1:])]
    total = sum(s[2] for s in segs) or 1
    run, best = 0, (0, 0)
    for a, b, length in segs:
        if length > best[1]:
            best = (run + length / 2, length)
        run += length
    return round(2 * best[0] / total - 1, 3)


def segments_hit(line, box):
    """True when a horizontal / vertical polyline passes through the box."""
    bx, by, bw, bh = box
    for (ax, ay), (cx, cy) in zip(line, line[1:]):
        if ay == cy and by < ay < by + bh and min(ax, cx) < bx + bw and max(ax, cx) > bx:
            return True
        if ax == cx and bx < ax < bx + bw and min(ay, cy) < by + bh and max(ay, cy) > by:
            return True
    return False


def shared_run(l1, l2, min_len=10):
    """True when two polylines run on top of each other for at least min_len px."""
    for (a, b) in zip(l1, l1[1:]):
        for (c, d) in zip(l2, l2[1:]):
            if a[1] == b[1] == c[1] == d[1]:
                lo, hi = max(min(a[0], b[0]), min(c[0], d[0])), min(max(a[0], b[0]), max(c[0], d[0]))
                if hi - lo >= min_len:
                    return True
            if a[0] == b[0] == c[0] == d[0]:
                lo, hi = max(min(a[1], b[1]), min(c[1], d[1])), min(max(a[1], b[1]), max(c[1], d[1]))
                if hi - lo >= min_len:
                    return True
    return False
