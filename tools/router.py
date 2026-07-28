"""Two-layer grid maze router for the remaining nets.

Everything already emitted by gen_pcb (segments, vias, pads) is rasterized
onto a 0.635 mm grid.  Hard obstacles (tracks/vias) are never enterable;
pad zones carry the pad's net so a route may enter zones of its own net
only.  Layer changes cost extra and need a via-clear cell.
"""

import heapq
import math

STEP = 0.3175
NX = int(138.0 / STEP) + 1
NY = int(74.0 / STEP) + 1
LAYERS = ("F.Cu", "B.Cu")
NEW_HALF = 0.15          # autoroute tracks are 0.3 mm
CLR = 0.24               # reserved gap; the rule is 0.18, and the slack covers
                         # a route's closest approach between two grid cells.
                         # 0.25 leaves the U3/U4 corridor one track short of
                         # holding both the signals and C5's ground rescue.
EDGE_Y = 66.35


def cell(x, y):
    return (round(x / STEP), round(y / STEP))


def pos(i, j):
    return (i * STEP, j * STEP)


class Grid:
    def __init__(self):
        # blk[layer]: cell -> set(nets); enterable only if all owners == net
        self.blk = {l: {} for l in LAYERS}
        self.via_hard = set()                    # holes: never place a via
        self.via_soft = {}                       # cell -> set(nets)

    def _disc(self, cx, cy, r):
        i0, j0 = cell(cx - r, cy - r)
        i1, j1 = cell(cx + r, cy + r)
        for i in range(max(i0, 0), min(i1, NX - 1) + 1):
            for j in range(max(j0, 0), min(j1, NY - 1) + 1):
                px, py = pos(i, j)
                if (px - cx) ** 2 + (py - cy) ** 2 <= r * r:
                    yield (i, j)

    def _seg_cells(self, x1, y1, x2, y2, r):
        n = max(int(math.hypot(x2 - x1, y2 - y1) / (STEP / 2)), 1)
        seen = set()
        for k in range(n + 1):
            t = k / n
            for c in self._disc(x1 + (x2 - x1) * t, y1 + (y2 - y1) * t, r):
                if c not in seen:
                    seen.add(c)
                    yield c

    def add_seg(self, x1, y1, x2, y2, layer, width, net):
        r = NEW_HALF + CLR + width / 2 + 0.02
        for c in self._seg_cells(x1, y1, x2, y2, r):
            self.blk[layer].setdefault(c, set()).add(net)
        for c in self._seg_cells(x1, y1, x2, y2, r + 0.17):
            self.via_soft.setdefault(c, set()).add(net)

    def add_via(self, x, y, size, net):
        r = NEW_HALF + CLR + size / 2 + 0.02
        for l in LAYERS:
            for c in self._disc(x, y, r):
                self.blk[l].setdefault(c, set()).add(net)
        self.via_hard.update(self._disc(x, y, r + 0.17))

    def add_pad(self, x, y, size, through, layers, net):
        r = size / 2 + NEW_HALF + CLR + 0.02
        tgt = LAYERS if through else [l for l in LAYERS if l in layers]
        for l in tgt:
            for c in self._disc(x, y, r):
                self.blk[l].setdefault(c, set()).add(net)
        if through:
            self.via_hard.update(self._disc(x, y, r + 0.4))
        else:
            for c in self._disc(x, y, r + 0.15):
                self.via_soft.setdefault(c, set()).add(net)

    def free(self, l, i, j, net):
        if not (2 <= i < NX - 2 and 2 <= j < NY - 2):
            return False
        if j * STEP > EDGE_Y:
            return False
        z = self.blk[l].get((i, j))
        return z is None or z == {net}

    def via_ok(self, i, j, net):
        if (i, j) in self.via_hard:
            return False
        z = self.via_soft.get((i, j))
        return z is None or z == {net}


def build_grid(gp):
    g = Grid()
    for x1, y1, x2, y2, layer, width, net in gp.SEGS:
        g.add_seg(x1, y1, x2, y2, layer, width, net)
    for x, y, size, net in gp.VIAS:
        g.add_via(x, y, size, net)
    for key, info in gp.PAD_INFO.items():
        x, y = gp.PADS[key]
        g.add_pad(x, y, info["size"], info["through"], info["layers"],
                  info.get("net"))
    return g


DIRS = ((1, 0), (-1, 0), (0, 1), (0, -1))


def bfs(g, sources, tcell, tlayers, net):
    dist, prev, pq = {}, {}, []
    for s in sources:
        dist[s] = 0
        heapq.heappush(pq, (0, s))
    while pq:
        d, node = heapq.heappop(pq)
        if dist.get(node, -1) != d:
            continue
        l, i, j = node
        if (i, j) == tcell and l in tlayers:
            path = [node]
            while path[-1] in prev:
                path.append(prev[path[-1]])
            path.reverse()
            return path
        for dx, dy in DIRS:
            ni, nj = i + dx, j + dy
            if g.free(l, ni, nj, net):
                nn = (l, ni, nj)
                if d + 1 < dist.get(nn, 1 << 30):
                    dist[nn] = d + 1
                    prev[nn] = node
                    heapq.heappush(pq, (d + 1, nn))
        ol = "B.Cu" if l == "F.Cu" else "F.Cu"
        if g.via_ok(i, j, net) and g.free(ol, i, j, net):
            nn = (ol, i, j)
            if d + 30 < dist.get(nn, 1 << 30):
                dist[nn] = d + 30
                prev[nn] = node
                heapq.heappush(pq, (d + 30, nn))
    return None


def route_net(gp, g, net, pins, width=0.3):
    pads = []
    for ref, pad in pins:
        x, y = gp.PADS[(ref, str(pad))]
        info = gp.PAD_INFO[(ref, str(pad))]
        lay = LAYERS if info["through"] else tuple(
            l for l in LAYERS if l in info["layers"])
        pads.append((x, y, lay))
    pads.sort()
    # seed the tree from any same-net copper already emitted (hand routes)
    tree = set()
    for x1, y1, x2, y2, layer, w, n2 in gp.SEGS:
        if n2 != net:
            continue
        steps = max(int(math.hypot(x2 - x1, y2 - y1) / STEP), 1)
        for k in range(steps + 1):
            t = k / steps
            i, j = cell(x1 + (x2 - x1) * t, y1 + (y2 - y1) * t)
            tree.add((layer, i, j))
    stubs = []
    if tree:
        legs = pads              # every pad must reach the seeded tree
    else:
        fx, fy, flay = pads[0]
        ci, cj = cell(fx, fy)
        tree = {(l, ci, cj) for l in flay}
        stubs = [((fx, fy), (ci, cj), flay[0])]
        legs = pads[1:]
    n_segs_before = len(gp.SEGS)
    n_vias_before = len(gp.VIAS)
    n_tracks_before = len(gp.TRACKS)
    for x, y, lay in legs:
        ti, tj = cell(x, y)
        path = bfs(g, tree, (ti, tj), lay, net)
        if path is None:
            # roll back partial emissions so they neither pollute the board
            # nor sit unregistered under later nets
            del gp.SEGS[n_segs_before:]
            del gp.VIAS[n_vias_before:]
            del gp.TRACKS[n_tracks_before:]
            return f"FAIL {net} -> pad at ({x:.2f},{y:.2f})"
        emit_path(gp, g, net, path, (x, y), width)
        tree.update(path)
    for (px, py), (i, j), l in stubs:
        gx, gy = pos(i, j)
        if abs(gx - px) > 0.02 or abs(gy - py) > 0.02:
            gp.route(net, [(px, py), (gx, gy)], l, width)
    # freshly emitted geometry becomes an obstacle for later nets
    for s in gp.SEGS[n_segs_before:]:
        g.add_seg(*s)
    return None


def emit_path(gp, g, net, path, tgt, width):
    cur = path[0][0]
    run = [pos(path[0][1], path[0][2])]
    for l, i, j in path[1:]:
        p = pos(i, j)
        if l != cur:
            _run(gp, net, run, cur, width)
            gp.via(run[-1][0], run[-1][1], net, size=0.6, drill=0.3)
            g.add_via(run[-1][0], run[-1][1], 0.6, net)
            cur = l
            run = [run[-1]]
        else:
            run.append(p)
    lx, ly = run[-1]
    tx, ty = tgt
    if abs(lx - tx) > 0.1 and abs(ly - ty) > 0.1:
        run.append((tx, ly))
        run.append((tx, ty))
    elif abs(lx - tx) > 0.02 or abs(ly - ty) > 0.02:
        run.append((tx, ty))
    _run(gp, net, run, cur, width)


def _run(gp, net, run, layer, width):
    simp = [run[0]]
    for p in run[1:]:
        if p == simp[-1]:
            continue
        if len(simp) >= 2:
            a, b = simp[-2], simp[-1]
            if (abs(a[0] - b[0]) < 0.01 and abs(b[0] - p[0]) < 0.01) or \
               (abs(a[1] - b[1]) < 0.01 and abs(b[1] - p[1]) < 0.01):
                simp[-1] = p
                continue
        simp.append(p)
    if len(simp) > 1:
        gp.route(net, simp, layer, width)
