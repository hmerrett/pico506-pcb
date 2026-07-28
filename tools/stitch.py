#!/usr/bin/env python3
"""Find GND pour fragments that no copper bridges to the main plane, and print
stitch-via coordinates that would join them.

Must run under KiCad's python:
  /Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/\
Versions/Current/bin/python3 stitch.py ../pico506.kicad_pcb

Builds a union-find over every GND copper item (zone fill islands, tracks,
vias, pads).  Islands are joined to a track/via/pad when that item's copper
lands inside them; through-hole items also join their F and B sides.  Anything
left outside the largest component is an orphan fragment.

For each orphan it then SOLVES for a stitch, in increasing order of intrusion:
  1. a plain via where the fragment overlaps main-plane pour on the other layer
  2. a via plus a short bridge track on the other layer
  3. a bridge track on the same layer (pinched-neck fragments, where the
     filler dropped a sub-min_thickness neck and nothing is in the gap)
Every candidate is clearance-checked against all foreign copper, board edge,
and the via keepout areas, so what it prints is safe to paste in as-is.
"""

import sys

import pcbnew

IU = 1e6                     # internal units per mm
NET = "GND"
VIA_R = 0.4                  # stitch via copper radius
MARGIN = 0.15                # keep via copper this far inside the pour edge
CLEAR = 0.20                 # min_clearance 0.18 + slack
TRK_W = 0.4                  # bridge track width
HOLE_CLEAR = 0.25            # min_hole_to_hole
STEP = 0.5                   # via candidate grid
ORIGIN_X, ORIGIN_Y = 30.0, 30.0   # layout.ORIGIN_* (board-local -> page)


def mm(v):
    return v / IU


def iu(v):
    return int(round(v * IU))


class UF:
    def __init__(self):
        self.p = {}

    def find(self, a):
        self.p.setdefault(a, a)
        while self.p[a] != a:
            self.p[a] = self.p[self.p[a]]
            a = self.p[a]
        return a

    def union(self, a, b):
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.p[ra] = rb


def island_polys(board, netcode):
    """[(key, layer, SHAPE_POLY_SET single-island, parent set, index)]"""
    out = []
    for zi, zone in enumerate(board.Zones()):
        if zone.GetNetCode() != netcode or zone.GetIsRuleArea():
            continue
        for layer in zone.GetLayerSet().Seq():
            ps = zone.GetFilledPolysList(layer)
            for i in range(ps.OutlineCount()):
                one = pcbnew.SHAPE_POLY_SET()
                one.AddOutline(ps.Outline(i))
                for h in range(ps.HoleCount(i)):
                    one.AddHole(ps.Hole(i, h), 0)
                out.append((("island", zi, layer, i), layer, one))
    return out


def deepest_point(ps, erode):
    """A point inside ps at least `erode` mm from its boundary, or None."""
    work = pcbnew.SHAPE_POLY_SET(ps)
    work.Inflate(-iu(erode), pcbnew.CORNER_STRATEGY_ROUND_ALL_CORNERS,
                 iu(0.005))
    work.Simplify()
    best = None
    for i in range(work.OutlineCount()):
        bb = work.Outline(i).BBox()
        area = abs(work.Outline(i).Area())
        c = bb.Centre()
        if work.Contains(pcbnew.VECTOR2I(c.x, c.y), i):
            pt = (c.x, c.y)
        else:
            pt = None
            for fx in (0.25, 0.5, 0.75):
                for fy in (0.25, 0.5, 0.75):
                    p = pcbnew.VECTOR2I(int(bb.GetLeft() + fx * bb.GetWidth()),
                                        int(bb.GetTop() + fy * bb.GetHeight()))
                    if work.Contains(p, i):
                        pt = (p.x, p.y)
                        break
                if pt:
                    break
        if pt and (best is None or area > best[0]):
            best = (area, pt)
    return best[1] if best else None


def obstacle_model(board, netcode):
    """Everything a stitch must stay clear of: foreign copper per copper layer,
    drilled holes, and the via keepout areas."""
    foreign = {pcbnew.F_Cu: pcbnew.SHAPE_POLY_SET(),
               pcbnew.B_Cu: pcbnew.SHAPE_POLY_SET()}
    holes = []          # (x, y, drill radius)
    keepout = pcbnew.SHAPE_POLY_SET()

    def add(item, layers):
        for layer in layers:
            if layer in foreign:
                item.TransformShapeToPolygon(foreign[layer], layer, 0,
                                             iu(0.005), pcbnew.ERROR_OUTSIDE)

    for t in board.GetTracks():
        if t.Type() == pcbnew.PCB_VIA_T:
            c = t.GetPosition()
            holes.append((c.x, c.y, t.GetDrillValue() / 2))
        if t.GetNetCode() != netcode:
            add(t, t.GetLayerSet().Seq())
    for fp in board.GetFootprints():
        for pad in fp.Pads():
            if pad.GetDrillSize().x > 0:
                c = pad.GetPosition()
                holes.append((c.x, c.y, pad.GetDrillSize().x / 2))
            if pad.GetNetCode() != netcode:
                add(pad, pad.GetLayerSet().Seq())
    for zone in board.Zones():
        if zone.GetIsRuleArea() and not zone.GetDoNotAllowVias():
            continue
        if zone.GetIsRuleArea():
            keepout.BooleanAdd(zone.Outline())
    # board edge: copper must stay min_copper_edge_clearance off it
    edge = pcbnew.SHAPE_POLY_SET()
    for d in board.GetDrawings():
        if d.GetLayer() == pcbnew.Edge_Cuts:
            d.TransformShapeToPolygon(edge, pcbnew.Edge_Cuts, iu(0.1),
                                      iu(0.005), pcbnew.ERROR_OUTSIDE)
    for layer in foreign:
        foreign[layer].BooleanAdd(edge)
        foreign[layer].Simplify()
    return foreign, holes, keepout


class Checker:
    def __init__(self, board, netcode):
        self.foreign, self.holes, self.keepout = obstacle_model(board, netcode)

    def _hits(self, poly, layer, clearance):
        test = pcbnew.SHAPE_POLY_SET(poly)
        test.Inflate(iu(clearance), pcbnew.CORNER_STRATEGY_ROUND_ALL_CORNERS,
                     iu(0.005))
        test.BooleanIntersection(self.foreign[layer])
        return any(abs(test.Outline(i).Area()) > iu(0.005) * iu(0.005)
                   for i in range(test.OutlineCount()))

    def via_ok(self, p):
        circle = pcbnew.SHAPE_POLY_SET()
        circle.NewOutline()
        for k in range(24):
            import math
            a = 2 * math.pi * k / 24
            circle.Append(int(p[0] + iu(VIA_R) * math.cos(a)),
                          int(p[1] + iu(VIA_R) * math.sin(a)))
        for layer in (pcbnew.F_Cu, pcbnew.B_Cu):
            if self._hits(circle, layer, CLEAR):
                return False
        if self.keepout.OutlineCount() and self.keepout.Contains(
                pcbnew.VECTOR2I(int(p[0]), int(p[1])), -1):
            return False
        for hx, hy, hr in self.holes:
            d = ((hx - p[0]) ** 2 + (hy - p[1]) ** 2) ** 0.5
            if d < iu(0.2) + hr + iu(HOLE_CLEAR):
                return False
        return True

    def track_ok(self, a, b, layer):
        seg = pcbnew.SHAPE_POLY_SET()
        chain = pcbnew.SHAPE_LINE_CHAIN()
        chain.Append(int(a[0]), int(a[1]))
        chain.Append(int(b[0]), int(b[1]))
        chain.SetClosed(False)
        seg = pcbnew.SHAPE_POLY_SET()
        seg.NewOutline()
        # rectangle of width TRK_W around the segment, with square ends
        import math
        dx, dy = b[0] - a[0], b[1] - a[1]
        ln = (dx * dx + dy * dy) ** 0.5
        if ln < 1:
            return False
        nx, ny = -dy / ln * iu(TRK_W / 2), dx / ln * iu(TRK_W / 2)
        for px, py in ((a[0] + nx, a[1] + ny), (b[0] + nx, b[1] + ny),
                       (b[0] - nx, b[1] - ny), (a[0] - nx, a[1] - ny)):
            seg.Append(int(px), int(py))
        return not self._hits(seg, layer, CLEAR)


def vsub(a, b):
    return (a[0] - b[0], a[1] - b[1])


def vnorm(v):
    ln = (v[0] ** 2 + v[1] ** 2) ** 0.5
    return (v[0] / ln, v[1] / ln) if ln else (0.0, 0.0)


def solve_stitch(group, main_islands, chk, other):
    """Cheapest safe way to tie this orphan component to the main plane.
    Returns (kind, via_pt, track_a, track_b, layer, length_mm) or None."""
    best = None

    def offer(kind, via_pt, a, b, layer, length):
        nonlocal best
        if best is None or length < best[5]:
            best = (kind, via_pt, a, b, layer, length)

    # 1. plain via where the fragment overlaps main pour on the other layer
    for _, layer, ps in group:
        for _, mlayer, mps in main_islands:
            if mlayer == layer:
                continue
            inter = pcbnew.SHAPE_POLY_SET(ps)
            inter.BooleanIntersection(mps)
            if inter.OutlineCount() == 0:
                continue
            pt = deepest_point(inter, VIA_R + MARGIN)
            if pt and chk.via_ok(pt):
                offer("via", pt, None, None, None, 0.0)
    if best:
        return best

    # 2/3. bridge track, with a via first if the main pour is on the far layer
    for _, layer, ps in group:
        eroded_via = pcbnew.SHAPE_POLY_SET(ps)
        eroded_via.Inflate(-iu(VIA_R + MARGIN),
                           pcbnew.CORNER_STRATEGY_ROUND_ALL_CORNERS, iu(0.005))
        eroded_trk = pcbnew.SHAPE_POLY_SET(ps)
        eroded_trk.Inflate(-iu(TRK_W / 2 + MARGIN),
                           pcbnew.CORNER_STRATEGY_ROUND_ALL_CORNERS, iu(0.005))
        oc = ps.Outline(0)
        for _, mlayer, mps in main_islands:
            mc = mps.Outline(0)
            # closest-approach samples between this fragment and this island
            cands = []
            for i in range(oc.PointCount()):
                p = oc.CPoint(i)
                n = mc.NearestPoint(p)
                d = ((n.x - p.x) ** 2 + (n.y - p.y) ** 2) ** 0.5
                cands.append((d, (p.x, p.y), (n.x, n.y)))
            cands.sort()
            for d, p, n in cands[:8]:
                inward = vnorm(vsub(p, n))
                if inward == (0.0, 0.0):
                    continue
                # target sits just inside the main pour
                t = (n[0] - inward[0] * iu(0.35), n[1] - inward[1] * iu(0.35))
                if not mps.Contains(pcbnew.VECTOR2I(int(t[0]), int(t[1])), 0):
                    continue
                same = (mlayer == layer)
                room = eroded_trk if same else eroded_via
                for back in (0.6, 0.9, 1.3, 1.8):
                    s = (p[0] + inward[0] * iu(back), p[1] + inward[1] * iu(back))
                    sv = pcbnew.VECTOR2I(int(s[0]), int(s[1]))
                    if not room.OutlineCount():
                        break
                    if not any(room.Contains(sv, i)
                               for i in range(room.OutlineCount())):
                        continue
                    length = mm(((t[0] - s[0]) ** 2 + (t[1] - s[1]) ** 2) ** 0.5)
                    if same:
                        if chk.track_ok(s, t, layer):
                            offer("track", None, s, t, layer, length)
                    else:
                        if chk.via_ok(s) and chk.track_ok(s, t, mlayer):
                            offer("via+track", s, s, t, mlayer, length)
                    break
    return best


def main():
    board = pcbnew.LoadBoard(sys.argv[1])
    netcode = board.GetNetInfo().GetNetItem(NET).GetNetCode()
    islands = island_polys(board, netcode)
    print(f"{NET} net code {netcode}: {len(islands)} fill islands")

    uf = UF()
    for key, _, _ in islands:
        uf.find(key)

    # Island membership must be tested against real copper shapes, not centres:
    # thermally-relieved pads sit in a HOLE of the island and only the spokes
    # touch, so a point-in-polygon test on the pad centre reports "outside".
    by_layer = {}
    for key, layer, ps in islands:
        by_layer.setdefault(layer, []).append((key, ps, ps.BBox()))

    def shape_poly(item, layer):
        poly = pcbnew.SHAPE_POLY_SET()
        item.TransformShapeToPolygon(poly, layer, 0, iu(0.005),
                                     pcbnew.ERROR_INSIDE)
        return poly

    def join_shape(item, layers, tag):
        """Union `tag` with every island whose copper the item's copper meets."""
        for layer in layers:
            cands = by_layer.get(layer)
            if not cands:
                continue
            poly = shape_poly(item, layer)
            if poly.OutlineCount() == 0:
                continue
            pbb = poly.BBox()
            for key, ps, ibb in cands:
                if not ibb.Intersects(pbb):
                    continue
                inter = pcbnew.SHAPE_POLY_SET(poly)
                inter.BooleanIntersection(ps)
                if inter.OutlineCount() and any(
                        abs(inter.Outline(i).Area()) > iu(0.01) * iu(0.01)
                        for i in range(inter.OutlineCount())):
                    uf.union(tag, key)

    cu = (pcbnew.F_Cu, pcbnew.B_Cu)
    for t in board.GetTracks():
        if t.GetNetCode() != netcode:
            continue
        join_shape(t, [l for l in t.GetLayerSet().Seq() if l in cu],
                   ("trk", t.m_Uuid.AsString()))
    # a through pad bridges F and B just like a via
    for fp in board.GetFootprints():
        for pad in fp.Pads():
            if pad.GetNetCode() != netcode:
                continue
            join_shape(pad, [l for l in pad.GetLayerSet().Seq() if l in cu],
                       ("pad", fp.GetReference(), pad.GetNumber()))

    # track-to-track / track-to-pad continuity by shared endpoints
    ends = {}
    for t in board.GetTracks():
        if t.GetNetCode() != netcode:
            continue
        tag = ("trk", t.m_Uuid.AsString())
        pts = ([t.GetPosition()] if t.Type() == pcbnew.PCB_VIA_T
               else [t.GetStart(), t.GetEnd()])
        for c in pts:
            k = (c.x, c.y)
            if k in ends:
                uf.union(tag, ends[k])
            ends[k] = tag
    for fp in board.GetFootprints():
        for pad in fp.Pads():
            if pad.GetNetCode() != netcode:
                continue
            c = pad.GetPosition()
            k = (c.x, c.y)
            if k in ends:
                uf.union(("pad", fp.GetReference(), pad.GetNumber()), ends[k])

    # component sizes by island area, so the main plane wins
    comp = {}
    for key, layer, ps in islands:
        r = uf.find(key)
        comp.setdefault(r, []).append((key, layer, ps))
    main_root = max(comp, key=lambda r: sum(abs(ps.Outline(0).Area())
                                            for _, _, ps in comp[r]))
    print(f"{len(comp)} connected component(s); "
          f"main has {len(comp[main_root])} island(s)")

    orphan_roots = [r for r in comp if r != main_root]
    if not orphan_roots:
        print("no orphan fragments")
        return
    main_islands = comp[main_root]
    chk = Checker(board, netcode)
    lines = []
    # GND pad positions, and which of them the main plane already reaches
    pad_pos = {}
    for fp in board.GetFootprints():
        for pad in fp.Pads():
            if pad.GetNetCode() != netcode:
                continue
            c = pad.GetPosition()
            pad_pos[(fp.GetReference(), pad.GetNumber())] = (c.x, c.y)
    main_pads = {(t[1], t[2]) for t in uf.p
                 if t[0] == "pad" and uf.find(t) == main_root}
    # One stitch per orphan COMPONENT: its islands are already joined to each
    # other by copper, so bridging any one of them to the main plane is enough.
    for r in sorted(orphan_roots,
                    key=lambda r: -sum(abs(p.Outline(0).Area())
                                       for _, _, p in comp[r])):
        group = comp[r]
        tot = sum(abs(p.Outline(0).Area()) for _, _, p in group) / IU / IU
        print(f"\norphan component: {len(group)} island(s), {tot:.1f} mm^2 total")
        members = [t for t in uf.p if uf.find(t) == r and t[0] != "island"]
        pads = sorted(f"{t[1]}.{t[2]}" for t in members if t[0] == "pad")
        if pads:
            print(f"  FLOATING PADS: {', '.join(pads)}")
        print(f"  ({len([t for t in members if t[0] == 'trk'])} track/via items)")
        for _, layer, ps in sorted(group, key=lambda t: -abs(t[2].Outline(0).Area())):
            bb = ps.Outline(0).BBox()
            print(f"  {board.GetLayerName(layer):5s} "
                  f"{abs(ps.Outline(0).Area()) / IU / IU:8.2f} mm^2  "
                  f"({mm(bb.GetLeft()) - ORIGIN_X:7.2f},"
                  f"{mm(bb.GetTop()) - ORIGIN_Y:7.2f})-"
                  f"({mm(bb.GetRight()) - ORIGIN_X:7.2f},"
                  f"{mm(bb.GetBottom()) - ORIGIN_Y:7.2f})")
        sol = solve_stitch(group, main_islands, chk, None)
        if sol is None:
            print("  !! no straight-line stitch — maze-route these links:")
            for t in members:
                if t[0] != "pad":
                    continue
                here = pad_pos[(t[1], t[2])]
                near = sorted(
                    (((here[0] - p[0]) ** 2 + (here[1] - p[1]) ** 2) ** 0.5, r)
                    for r, p in pad_pos.items() if r in main_pads)
                opts = ", ".join(f'("{r[0]}",{r[1]}) {mm(d):.1f}mm'
                                 for d, r in near[:3])
                print(f"     {t[1]}.{t[2]} -> {opts}")
                lines.append(f'    gnd_link(g, ("{t[1]}", {t[2]}), '
                             f'("{near[0][1][0]}", {near[0][1][1]}))')
            continue
        kind, via_pt, a, b, layer, length = sol

        def bl(p):
            return (mm(p[0]) - ORIGIN_X, mm(p[1]) - ORIGIN_Y)

        tag = pads[0] if pads else "fragment"
        if kind == "via":
            x, y = bl(via_pt)
            print(f"  -> plain stitch via at ({x:.2f}, {y:.2f})")
            lines.append(f'    via({x:.2f}, {y:.2f}, g)            # {tag}')
        elif kind == "track":
            ax, ay = bl(a)
            bx_, by_ = bl(b)
            ln = board.GetLayerName(layer)
            print(f"  -> {length:.2f} mm bridge on {ln}: "
                  f"({ax:.2f},{ay:.2f}) -> ({bx_:.2f},{by_:.2f})")
            lines.append(f'    route(g, [({ax:.2f}, {ay:.2f}), '
                         f'({bx_:.2f}, {by_:.2f})], "{ln}", 0.4)  # {tag}')
        else:
            ax, ay = bl(a)
            bx_, by_ = bl(b)
            ln = board.GetLayerName(layer)
            print(f"  -> via at ({ax:.2f},{ay:.2f}) + {length:.2f} mm on {ln} "
                  f"-> ({bx_:.2f},{by_:.2f})")
            lines.append(f'    via({ax:.2f}, {ay:.2f}, g)            # {tag}')
            lines.append(f'    route(g, [({ax:.2f}, {ay:.2f}), '
                         f'({bx_:.2f}, {by_:.2f})], "{ln}", 0.4)')
    print("\npaste into the GND relief block in gen_pcb.py:")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
