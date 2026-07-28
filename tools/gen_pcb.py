#!/usr/bin/env python3
"""Generate pico506.kicad_pcb: outline with keyed card-edge tabs, placement,
routing, zones.  Consumes netlist.py + layout.py + the generated footprints."""

import json
import math
import os
import uuid as uuidlib

import layout as L
import netlist
import sexpr
from sexpr import q

HW = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
KICAD_FP = "/Applications/KiCad/KiCad.app/Contents/SharedSupport/footprints"

OX, OY = L.ORIGIN_X, L.ORIGIN_Y

_uid_counter = 0


def uid():
    global _uid_counter
    _uid_counter += 1
    return str(uuidlib.uuid5(uuidlib.NAMESPACE_URL, f"pico506-pcb-{_uid_counter}"))


def fmt(v):
    s = f"{v:.4f}".rstrip("0").rstrip(".")
    return s if s not in ("-0", "") else "0"


def bx(x):
    return x + OX


def by(y):
    return y + OY


# ---------------------------------------------------------------------------
# nets
# ---------------------------------------------------------------------------

NETS = {"": 0}
for _n in sorted(netlist.nets()):
    NETS[_n] = len(NETS)


# ---------------------------------------------------------------------------
# placement (board-local coords, x east 0..138, y south 0..70, rear = y70)
# ---------------------------------------------------------------------------

PLACE = {
    # rear connector strip
    "J1": (L.J1_CENTER_X, L.BOARD_D, 0),
    "J2": (L.J2_CENTER_X, L.BOARD_D, 0),
    "J3": (L.J3_PIN1_X + 1.5 * L.J3_PITCH, L.BOARD_D - L.J3_ROW_SETBACK, 0),
    "FG1": (L.FG_X, L.BOARD_D - L.FG_Y_FROM_REAR, 0),

    # terminator + drive select row
    # SIP pads on the half-grid: every J1 finger escape passes exactly
    # between two SIP pads with 1.27 mm on each side
    "RN1": (27.43, 64.0, 0),
    "RN2": (52.83, 64.0, 0),
    "J4": (88.12, 61.0, 270),   # pin 1 east; columns DS4..DS1 west->east
    # +0.6 east of the natural 91.0/94.5: clears J4's courtyard to the west
    # and still leaves R22 clear of U6
    "R21": (91.6, 62.0, 90),
    "R22": (95.1, 62.0, 90),

    # DIP row (13 mm pitch leaves cap corridors between sockets)
    "U2": (38.0, 41.0, 0),
    "U3": (51.0, 41.0, 0),
    "U4": (64.0, 41.0, 0),
    "U5": (77.0, 41.0, 0),
    "U6": (98.0, 41.0, 0),
    "U7": (112.0, 41.0, 0),
    "R12": (126.0, 62.0, 90),

    # pull-up banks, horizontal; pin 2 (signal end) lands near its GPIO
    "R1": (34.0, 31.0, 0),      # WG_GATED   -> GP2
    "R9": (34.0, 35.0, 0),      # WR_DATA    -> GP3
    "R4": (57.16, 31.0, 180),   # HS0        -> GP4
    "R8": (60.0, 31.0, 0),      # SELECTED   -> GP11
    "R2": (60.0, 35.0, 0),      # STEP_GATED -> GP12
    "R3": (73.0, 31.0, 0),      # DIR_IN     -> GP13
    "R5": (73.0, 35.0, 0),      # HS1        -> GP14
    "R6": (96.16, 31.0, 180),   # HS2        -> GP16
    "R7": (96.16, 35.0, 180),   # HS3        -> GP17
    # SD pull-ups (pin 1 = 3V3 west)
    "R17": (101.0, 34.8, 0), "R18": (114.5, 34.8, 0),
    "R19": (101.0, 37.8, 0), "R20": (114.5, 37.8, 0),

    # Pico module (long axis E-W, USB west; origin = pin 1 at SW)
    "U1": (35.0, 26.78, 90),

    # power entry area (west)
    "C1": (27.0, 52.0, 0),
    "TP1": (23.0, 47.0, 0),
    "D1": (16.5, 42.0, 0),   # west, so C2 fits between it and C3
    "C2": (29.6, 42.0, 0),      # threads the gap between D1 and C3

    # front strip / indicators (west).  The LEDs, the TO-92 and the buzzer
    # were packed tight enough that their bodies actually fouled each other;
    # these positions give every pair a real gap (see tools/place_check.py).
    "BZ1": (13.0, 12.0, 0),
    "R11": (24.0, 17.4, 90),
    "Q1": (12.3, 30.0, 0),      # east of the LEDs: bodies overlapped at 10.0
    "R13": (18.0, 30.0, 90),
    "R14": (22.0, 30.0, 90),
    "R16": (26.0, 30.0, 90),
    "R15": (30.0, 30.0, 90),
    "D2": (6.0, 32.6, 0),       # spread 7.2 apart, not 6.0
    "D3": (6.0, 25.4, 0),
    "J7": (26.0, 4.0, 90),
    "SW1": (130.5, 20.0, 90),
    "J5": (46.0, 3.0, 90),
    "J6": (58.0, 3.0, 90),
    "JP1": (66.0, 3.0, 90),
    # R10 must stay at x90: the WF_IN riser threads between the +3V3 trunk
    # descent at x87.9 and R10's pad column, and 90.0 is what that fits
    "R10": (90.0, 22.0, 90),

    # SD socket, card exits the front (north) edge
    "SD1": (114.0, 16.0, 180),

    # decoupling (vertical in the inter-DIP corridors, +5V pad north)
    "C3": (35.3, 41.0, 270),   # U2
    "C4": (48.3, 41.0, 270),   # U3
    "C5": (61.3, 41.0, 270),   # U4
    "C6": (74.3, 41.0, 270),   # U5
    "C7": (95.2, 41.0, 270),   # U6
    "C8": (108.8, 41.0, 270),  # U7
    "C9": (92.8, 22.0, 0),     # SD 100n, east of R10's courtyard
    "C10": (93.2, 15.0, 0),    # SD 10u, east of R10's silk

    # mounting holes
    "H1": (5.0, 5.0, 0),
    "H2": (133.0, 5.0, 0),
    "H3": (5.0, 40.0, 0),
    "H4": (133.0, 52.0, 0),
}


# ---------------------------------------------------------------------------
# footprint loading / transformation
# ---------------------------------------------------------------------------

def fp_path(libid):
    lib, name = libid.split(":")
    if lib == "pico506-lib":
        return os.path.join(HW, "pico506-lib.pretty", f"{name}.kicad_mod")
    return os.path.join(KICAD_FP, f"{lib}.pretty", f"{name}.kicad_mod")


_fp_cache = {}


def load_fp(libid):
    if libid not in _fp_cache:
        with open(fp_path(libid)) as f:
            _fp_cache[libid] = sexpr.loads(f.read())
    return sexpr._deep_copy(_fp_cache[libid])


def pad_local(pad):
    at = sexpr.find(pad, "at")
    px, py = float(at[1]), float(at[2])
    pr = float(at[3]) if len(at) > 3 else 0.0
    return px, py, pr


def transform(px, py, X, Y, rot):
    th = math.radians(rot)
    gx = X + px * math.cos(th) + py * math.sin(th)
    gy = Y - px * math.sin(th) + py * math.cos(th)
    return gx, gy


PADS = {}      # (ref, pad) -> (gx, gy) board-local
PAD_INFO = {}  # (ref, pad) -> dict(layers=..., through=bool)

# collision model for the reference-designator placer, all board-local mm
PAD_BOXES = []    # (x0, y0, x1, y1) mask apertures — silk may not touch these
SILK_BOXES = []   # (ref, layer, x0, y0, x1, y1) footprint silk graphics
REF_NODES = {}    # ref -> (property node, X, Y, rot)

REF_SIZE = 0.8    # min_text_height is 0.8; smaller text fits more places
REF_THICK = 0.13


def text_box(s, x, y, size, rot, thick=0.0):
    """Conservative bbox of a stroke-font text centred at (x, y)."""
    w = len(s) * size * 0.85 + thick
    h = size * 1.15 + thick
    if rot % 180:
        w, h = h, w
    return (x - w / 2, y - h / 2, x + w / 2, y + h / 2)


def _custom_pad_reach(pad):
    """Farthest any custom-pad primitive gets from the pad's own origin."""
    prims = sexpr.find(pad, "primitives")
    if not prims:
        return 0.0
    best = 0.0
    for prim in prims[1:]:
        t = sexpr.tag(prim)
        if t == "gr_poly":
            for xy in sexpr.find_all(sexpr.find(prim, "pts"), "xy"):
                best = max(best, math.hypot(float(xy[1]), float(xy[2])))
        elif t == "gr_circle":
            c = sexpr.find(prim, "center")
            e = sexpr.find(prim, "end")
            cx, cy = float(c[1]), float(c[2])
            r = math.hypot(float(e[1]) - cx, float(e[2]) - cy)
            best = max(best, math.hypot(cx, cy) + r)
        else:
            for k in ("start", "mid", "end", "center"):
                n = sexpr.find(prim, k)
                if n:
                    best = max(best, math.hypot(float(n[1]), float(n[2])))
    return best


def _circumcircle(ps):
    """Centre and radius of the circle through three points, or None."""
    (ax, ay), (bx, by), (cx, cy) = ps
    d = 2 * (ax * (by - cy) + bx * (cy - ay) + cx * (ay - by))
    if abs(d) < 1e-9:
        return None
    a2, b2, c2 = ax * ax + ay * ay, bx * bx + by * by, cx * cx + cy * cy
    ux = (a2 * (by - cy) + b2 * (cy - ay) + c2 * (ay - by)) / d
    uy = (a2 * (cx - bx) + b2 * (ax - cx) + c2 * (bx - ax)) / d
    return (ux, uy), math.hypot(ax - ux, ay - uy)


def _shape_local_box(item):
    """Local bbox of a footprint graphic, or None if it isn't silk geometry."""
    t = sexpr.tag(item)
    pts = []
    if t in ("fp_line", "fp_rect"):
        for k in ("start", "end"):
            n = sexpr.find(item, k)
            pts.append((float(n[1]), float(n[2])))
    elif t == "fp_arc":
        # bound the whole circle the arc lies on: the endpoints alone
        # under-report a bulging arc, and under-reporting here lets a
        # reference designator land on top of it
        ps = []
        for k in ("start", "mid", "end"):
            n = sexpr.find(item, k)
            if n:
                ps.append((float(n[1]), float(n[2])))
        c = _circumcircle(ps) if len(ps) == 3 else None
        if c:
            (cx, cy), r = c
            pts = [(cx - r, cy - r), (cx + r, cy + r)]
        else:
            pts = ps
    elif t == "fp_circle":
        c = sexpr.find(item, "center")
        e = sexpr.find(item, "end")
        cx, cy = float(c[1]), float(c[2])
        r = math.hypot(float(e[1]) - cx, float(e[2]) - cy)
        pts = [(cx - r, cy - r), (cx + r, cy + r)]
    elif t == "fp_poly":
        for xy in sexpr.find_all(sexpr.find(item, "pts"), "xy"):
            pts.append((float(xy[1]), float(xy[2])))
    elif t == "fp_text":
        at = sexpr.find(item, "at")
        eff = sexpr.find(item, "effects")
        size = 1.0
        if eff:
            fnt = sexpr.find(eff, "font")
            sz = sexpr.find(fnt, "size") if fnt else None
            if sz:
                size = float(sz[1])
        s = sexpr.uq(item[2])
        b = text_box(s, float(at[1]), float(at[2]), size, 0)
        pts = [(b[0], b[1]), (b[2], b[3])]
    if not pts:
        return None
    return (min(p[0] for p in pts), min(p[1] for p in pts),
            max(p[0] for p in pts), max(p[1] for p in pts))


def _global_box(lx0, ly0, lx1, ly1, X, Y, rot):
    """Transform a local box's corners and re-bound them."""
    cs = [transform(x, y, X, Y, rot)
          for x, y in ((lx0, ly0), (lx1, ly0), (lx1, ly1), (lx0, ly1))]
    return (min(c[0] for c in cs), min(c[1] for c in cs),
            max(c[0] for c in cs), max(c[1] for c in cs))


def _overlaps(a, b, gap=0.0):
    return (a[0] < b[2] + gap and b[0] < a[2] + gap
            and a[1] < b[3] + gap and b[1] < a[3] + gap)


def place_footprint(ref, comp, sch_uuids):
    X, Y, rot = PLACE[ref]
    node = load_fp(comp["footprint"])
    node[0] = "footprint"
    node[1] = q(comp["footprint"])
    # strip any existing at/path/property Reference/Value; keep the rest
    keep = []
    for item in node[2:]:
        t = sexpr.tag(item)
        if t in ("at", "path", "property"):
            continue
        if t == "fp_text" and item[1] in ("reference", "value"):
            continue
        keep.append(item)
    body = node[:2]
    body.append(["layer", q("F.Cu")])
    body.append(["uuid", q(uid())])
    body.append(["at", fmt(bx(X)), fmt(by(Y)), fmt(rot)])
    if ref in sch_uuids:
        body.append(["path", q("/" + sch_uuids[ref])])
    ref_node = ["property", q("Reference"), q(ref),
                ["at", "0", "-2", "0"], ["layer", q("F.SilkS")],
                ["uuid", q(uid())],
                ["effects", ["font", ["size", fmt(REF_SIZE), fmt(REF_SIZE)],
                             ["thickness", fmt(REF_THICK)]]]]
    body.append(ref_node)
    REF_NODES[ref] = (ref_node, X, Y, rot)
    body.append(["property", q("Value"), q(comp["value"]),
                 ["at", "0", "2", fmt(rot)], ["layer", q("F.Fab")],
                 ["uuid", q(uid())],
                 ["effects", ["font", ["size", "0.9", "0.9"],
                              ["thickness", "0.14"]]]])
    anon = 0
    for item in keep:
        t = sexpr.tag(item)
        if t == "pad":
            pnum = sexpr.uq(item[1])
            net_key = pnum
            if not pnum or (ref, pnum) in PADS:
                anon += 1
                pnum = f"{net_key}~{anon}"
            px, py, pr = pad_local(item)
            gx, gy = transform(px, py, X, Y, rot)
            PADS[(ref, pnum)] = (gx, gy)
            layers_node = sexpr.find(item, "layers") or []
            size_node = sexpr.find(item, "size")
            psz = max(float(size_node[1]), float(size_node[2])) if size_node else 1.6
            if item[3] in ("rect", "roundrect"):
                psz *= 1.415
            elif item[3] == "custom":
                # (size) is only the anchor; the real copper is the primitives,
                # and the Pico's castellated pads reach well past it
                psz = max(psz, 2 * _custom_pad_reach(item))
            drill_node = sexpr.find(item, "drill")
            if drill_node:
                try:
                    psz = max(psz, float(drill_node[1]) + 0.2)
                except (TypeError, ValueError):
                    pass
            PAD_INFO[(ref, pnum)] = dict(
                through=item[2] in ("thru_hole", "np_thru_hole"),
                layers=[sexpr.uq(x) for x in layers_node[1:]],
                size=psz,
                net=comp["pins"].get(net_key),
            )
            # rewrite pad angle to include footprint rotation
            at = sexpr.find(item, "at")
            base = pr
            newang = (base + rot) % 360
            if len(at) > 3:
                at[3] = fmt(newang)
            elif newang:
                at.append(fmt(newang))
            # net assignment
            net = comp["pins"].get(pnum)
            item[:] = [x for x in item if sexpr.tag(x) not in ("net",)]
            if net:
                item.append(["net", str(NETS[net]), q(net)])
            # mask aperture, for the reference placer to keep silk off
            sx, sy = (float(size_node[1]), float(size_node[2])) if size_node \
                else (psz, psz)
            if (pr + rot) % 180:
                sx, sy = sy, sx
            PAD_BOXES.append((gx - sx / 2, gy - sy / 2, gx + sx / 2, gy + sy / 2))
        else:
            lb = _shape_local_box(item)
            lay = sexpr.find(item, "layer")
            if lb and lay and sexpr.uq(lay[1]) in ("F.SilkS", "B.SilkS"):
                SILK_BOXES.append((ref, sexpr.uq(lay[1]),
                                   *_global_box(*lb, X, Y, rot)))
        body.append(item)
    return body


def place_references():
    """Choose a spot for every reference designator.

    Every ref used to sit at a fixed local (0, -2), which buried a lot of them
    in pads and in their own footprint's silk.  Instead each one is offered
    positions around its part, working outwards, and takes the first that
    clears all mask apertures, all footprint silk, the board texts, the refs
    already placed, and the board edge.
    """
    own = {}
    for ref, layer, x0, y0, x1, y1 in SILK_BOXES:
        b = own.get(ref)
        own[ref] = (min(b[0], x0), min(b[1], y0), max(b[2], x1),
                    max(b[3], y1)) if b else (x0, y0, x1, y1)
    pads_of = {}
    for (ref, _pad), (gx, gy) in PADS.items():
        b = pads_of.get(ref)
        pads_of[ref] = (min(b[0], gx), min(b[1], gy), max(b[2], gx),
                        max(b[3], gy)) if b else (gx, gy, gx, gy)

    fixed = list(BOARD_TEXT_BOXES)
    placed = []
    unresolved = []
    # tightest parts first: they have the fewest options
    order = sorted(REF_NODES, key=lambda r: _extent_area(own.get(r) or pads_of.get(r)))
    for ref in order:
        node, X, Y, rot = REF_NODES[ref]
        hull = own.get(ref) or pads_of.get(ref) or (X, Y, X, Y)
        best = None
        for gx, gy, trot in _ref_candidates(hull, X, Y):
            box = text_box(ref, gx, gy, REF_SIZE, trot, REF_THICK)
            if not _ref_box_ok(box, ref):
                continue
            if any(_overlaps(box, o, 0.05) for o in fixed + placed):
                continue
            best = (gx, gy, trot, box)
            break
        if best is None:
            unresolved.append(ref)
            gx, gy = transform(0, -2, X, Y, rot)
            best = (gx, gy, 0, text_box(ref, gx, gy, REF_SIZE, 0, REF_THICK))
        gx, gy, trot, box = best
        placed.append(box)
        dx, dy = gx - X, gy - Y
        th = math.radians(rot)
        px = dx * math.cos(th) - dy * math.sin(th)
        py = dx * math.sin(th) + dy * math.cos(th)
        at = sexpr.find(node, "at")
        at[1], at[2], at[3] = fmt(px), fmt(py), fmt(trot)
    if unresolved:
        print("REF placer found no clear spot for:", " ".join(unresolved))


def _extent_area(b):
    return (b[2] - b[0]) * (b[3] - b[1]) if b else 0.0


def _ref_candidates(hull, X, Y):
    """Positions to try, nearest-and-tidiest first: centred above the part,
    then below, then the sides, then the corners, each at growing offsets."""
    x0, y0, x1, y1 = hull
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    h = REF_SIZE * 1.15 / 2 + 0.1
    for d in (0.25, 0.6, 1.1, 1.8, 2.6):
        yield (cx, y0 - h - d, 0)
        yield (cx, y1 + h + d, 0)
        yield (x1 + h + d, cy, 90)
        yield (x0 - h - d, cy, 90)
        yield (cx, y0 - h - d, 90)
        yield (cx, y1 + h + d, 90)
        for sx, sy in ((1, -1), (-1, -1), (1, 1), (-1, 1)):
            yield (cx + sx * ((x1 - x0) / 2 + d), cy + sy * ((y1 - y0) / 2 + h + d), 0)


def board_cutouts():
    """Rectangles inside the main outline where there is no board: the relief
    cut-outs beside each tab, and the part of each key slot that runs inboard
    of the rear edge.  The reference placer has to treat these as off-board."""
    D, T = L.BOARD_D, L.TAB_PROTRUDE
    ry = L.tab_relief_y()
    slot_top = D + T - L.KEY_SLOT_DEPTH
    sw = L.KEY_SLOT_W / 2
    out = []
    for cx, tw, ncols in ((L.J1_CENTER_X, L.J1_TAB_W, 17),
                          (L.J2_CENTER_X, L.J2_TAB_W, 10)):
        hw = tw / 2
        west, east = L.tab_relief_x(cx, tw)
        out.append((west, ry, cx - hw, D))
        out.append((cx + hw, ry, east, D))
        sx = L.key_slot_x(cx, ncols)
        out.append((sx - sw, slot_top, sx + sw, D))
    return out


CUTOUTS = board_cutouts()


def _ref_box_ok(box, ref):
    """Clear of every mask aperture, all footprint silk, and the board edge?"""
    if not (0.3 <= box[0] and box[2] <= L.BOARD_W - 0.3
            and 0.3 <= box[1] and box[3] <= L.BOARD_D - 0.3):
        return False
    for co in CUTOUTS:
        if _overlaps(box, co, 0.2):
            return False
    for pb in PAD_BOXES:
        if _overlaps(box, pb, 0.05):
            return False
    for _r, _layer, x0, y0, x1, y1 in SILK_BOXES:
        if _overlaps(box, (x0, y0, x1, y1), 0.05):
            return False
    return True


# ---------------------------------------------------------------------------
# board outline
# ---------------------------------------------------------------------------

def outline_nodes():
    W, D, T = L.BOARD_W, L.BOARD_D, L.TAB_PROTRUDE
    cc = L.TAB_CORNER
    ry = L.tab_relief_y()

    def tab_path(cx, tw, slot_x):
        """West-to-east rear-edge profile of one tab and its relief cut-outs.

        The tab's sides now run all the way from the relief's inboard edge
        (`ry`) out to the tip, so the tab is a free-standing tongue as long as
        the fingers rather than a 5 mm stub in a full-width edge.
        """
        hw = tw / 2
        sw = L.KEY_SLOT_W / 2
        sd = L.KEY_SLOT_DEPTH
        west, east = L.tab_relief_x(cx, tw)
        pts = []
        if west > 0.0:
            pts.append((west, D))
        pts += [(west, ry), (cx - hw, ry),
                (cx - hw, D + T - cc), (cx - hw + cc, D + T)]
        pts += [(slot_x - sw, D + T), (slot_x - sw, D + T - sd),
                (slot_x + sw, D + T - sd), (slot_x + sw, D + T)]
        pts += [(cx + hw - cc, D + T), (cx + hw, D + T - cc),
                (cx + hw, ry), (east, ry)]
        if east < W:
            pts.append((east, D))
        return pts

    rear = [(0.0, D)]
    for cx, tw, ncols in ((L.J1_CENTER_X, L.J1_TAB_W, 17),
                          (L.J2_CENTER_X, L.J2_TAB_W, 10)):
        rear += tab_path(cx, tw, L.key_slot_x(cx, ncols))
    if rear[-1][1] == D:
        rear.append((W, D))        # last relief stopped short of the east edge
    # north edge west-to-east, down the east edge, then the rear profile back
    path = [(0.0, 0.0), (W, 0.0)] + list(reversed(rear)) + [(0.0, 0.0)]

    nodes = []
    for (x1, y1), (x2, y2) in zip(path, path[1:]):
        if (x1, y1) == (x2, y2):
            continue
        nodes.append(["gr_line", ["start", fmt(bx(x1)), fmt(by(y1))],
                      ["end", fmt(bx(x2)), fmt(by(y2))],
                      ["stroke", ["width", "0.1"], ["type", "solid"]],
                      ["layer", q("Edge.Cuts")], ["uuid", q(uid())]])
    return nodes


# ---------------------------------------------------------------------------
# text / silk
# ---------------------------------------------------------------------------

def gr_text(s, x, y, layer, size=1.5, rot=0, bold=False, mirror=False):
    eff = ["effects", ["font", ["size", fmt(size), fmt(size)],
                       ["thickness", fmt(size * (0.2 if bold else 0.15))]]]
    if bold:
        eff[1].append(["bold", "yes"])
    if mirror:
        eff.append(["justify", "mirror"])
    return ["gr_text", q(s), ["at", fmt(bx(x)), fmt(by(y)), fmt(rot)],
            ["layer", q(layer)], ["uuid", q(uid())], eff]


# (string, x, y, layer, size, rot, bold, mirror).  The silk entries double as
# obstacles for the reference-designator placer, so they live in a table.
BOARD_TEXTS = [
    ("PICO506", 20, 34.2, "F.SilkS", 3.0, 0, True, False),
    ("MFM/RLL HDD EMULATOR", 20, 37.5, "F.SilkS", 1.0, 0, False, False),
    # the branding sat over the DIP and Pico pad rows; the clear span on the
    # back is between the Pico's two pin rows, which carry no pads of their own
    # (rows at y = 9.0 and 26.78, 1.6 mm pads, so silk is free from 9.8 to 25.98
    # across x = 35..83.26 — the three lines below are sized to sit inside that)
    ("PICO506  REV 1.0", 59, 19.0, "B.SilkS", 2.4, 0, True, True),
    # this board's own repo, so a bare PCB points at its own design files
    ("github.com/hmerrett/pico506-pcb", 59, 22.0, "B.SilkS", 1.2, 0, False, True),
    # and the firmware it exists to carry, which is someone else's work
    ("FIRMWARE: github.com/kuba2k2/pico506", 59, 24.2, "B.SilkS", 1.0, 0, False, True),
    ("J1 CONTROL", L.J1_CENTER_X, 66.3, "F.SilkS", 1.0, 0, False, False),
    ("J2 DATA", L.J2_CENTER_X, 66.3, "F.SilkS", 1.0, 0, False, False),
    ("DS 4 3 2 1", 84.3, 58.2, "F.SilkS", 0.8, 0, False, False),
    ("TERM: LAST DRIVE ONLY", 12, 59.5, "F.SilkS", 0.9, 0, False, False),
    # header legends (west to east pin order)
    ("RX TX GND", 43.5, 1.2, "F.SilkS", 0.8, 0, False, False),
    ("GND SG", 56.7, 1.2, "F.SilkS", 0.8, 0, False, False),
    ("WF EN", 64.7, 1.2, "F.SilkS", 0.8, 0, False, False),
    ("-  +", 24.7, 1.4, "F.SilkS", 0.8, 0, False, False),
    ("LED", 21.5, 4.0, "F.SilkS", 0.8, 0, False, False),
    ("RST", 130.5, 28.0, "F.SilkS", 0.8, 0, False, False),
    ("ACT", 1.6, 32.0, "F.SilkS", 0.8, 90, False, False),
    ("PWR", 1.6, 26.0, "F.SilkS", 0.8, 90, False, False),
    ("+12V", 23.0, 44.6, "F.SilkS", 0.8, 0, False, False),
]

FAB_NOTES = [
    ("FAB: 1.6mm FR4, 1oz Cu. Card edge fingers hard gold "
     "(Ni 2.5um min / Au 0.4um min), bevel 30deg both card edges.",
     69, 78.5, "Cmts.User", 1.2),
    ("Key slots 0.91mm routed through. Board rear edge = drive "
     "rear plane; tabs protrude 5mm for cable access.",
     69, 81.0, "Cmts.User", 1.2),
]

BOARD_TEXT_BOXES = [
    text_box(s, x, y, size, rot, size * 0.2)
    for s, x, y, layer, size, rot, bold, mirror in BOARD_TEXTS
]


def texts():
    out = [gr_text(s, x, y, layer, size, rot=rot, bold=bold, mirror=mirror)
           for s, x, y, layer, size, rot, bold, mirror in BOARD_TEXTS]
    out += [gr_text(s, x, y, layer, size) for s, x, y, layer, size in FAB_NOTES]
    return out


# ---------------------------------------------------------------------------
# zones
# ---------------------------------------------------------------------------

def zones():
    W, D, T = L.BOARD_W, L.BOARD_D, L.TAB_PROTRUDE
    pts = [(-1, -1), (W + 1, -1), (W + 1, D + T + 1), (-1, D + T + 1)]
    out = []
    # keepouts: no pour between the gold fingers on either tab
    for cx, tw in ((L.J1_CENTER_X, L.J1_TAB_W), (L.J2_CENTER_X, L.J2_TAB_W)):
        hw = tw / 2 + 0.3
        kpts = [(cx - hw, D - 7.2), (cx + hw, D - 7.2),
                (cx + hw, D + T + 1), (cx - hw, D + T + 1)]
        poly = ["polygon", ["pts"] + [["xy", fmt(bx(x)), fmt(by(y))]
                                      for x, y in kpts]]
        out.append(["zone", ["net", "0"], ["net_name", q("")],
                    ["layers", q("F.Cu"), q("B.Cu")], ["uuid", q(uid())],
                    ["hatch", "edge", "0.5"], ["connect_pads",
                    ["clearance", "0"]], ["min_thickness", "0.25"],
                    ["keepout", ["tracks", "allowed"], ["vias", "not_allowed"],
                     ["pads", "allowed"], ["copperpour", "not_allowed"],
                     ["footprints", "allowed"]],
                    ["fill", ["thermal_gap", "0.5"],
                     ["thermal_bridge_width", "0.5"]],
                    poly])
    for layer in ("F.Cu", "B.Cu"):
        poly = ["polygon", ["pts"] + [["xy", fmt(bx(x)), fmt(by(y))]
                                      for x, y in pts]]
        out.append(["zone", ["net", str(NETS["GND"])], ["net_name", q("GND")],
                    ["layer", q(layer)], ["uuid", q(uid())],
                    ["hatch", "edge", "0.5"],
                    ["connect_pads", ["clearance", "0.4"]],
                    ["min_thickness", "0.25"],
                    ["filled_areas_thickness", "no"],
                    ["fill", "yes", ["thermal_gap", "0.5"],
                     ["thermal_bridge_width", "0.6"]],
                    poly])
    return out


# ---------------------------------------------------------------------------
# tracks
# ---------------------------------------------------------------------------

TRACKS = []


SEGS = []    # (x1, y1, x2, y2, layer, width, net) board-local, for the router
VIAS = []    # (x, y, size, net)


def seg(x1, y1, x2, y2, layer, width, net):
    SEGS.append((x1, y1, x2, y2, layer, width, net))
    TRACKS.append(["segment", ["start", fmt(bx(x1)), fmt(by(y1))],
                   ["end", fmt(bx(x2)), fmt(by(y2))],
                   ["width", fmt(width)], ["layer", q(layer)],
                   ["net", str(NETS[net])], ["uuid", q(uid())]])


def via(x, y, net, size=0.8, drill=0.4):
    VIAS.append((x, y, size, net))
    TRACKS.append(["via", ["at", fmt(bx(x)), fmt(by(y))],
                   ["size", fmt(size)], ["drill", fmt(drill)],
                   ["layers", q("F.Cu"), q("B.Cu")],
                   ["net", str(NETS[net])], ["uuid", q(uid())]])


def P(ref, pad):
    return PADS[(ref, str(pad))]


def route(net, pts, layer, width=0.4):
    for (x1, y1), (x2, y2) in zip(pts, pts[1:]):
        if (x1, y1) != (x2, y2):
            seg(x1, y1, x2, y2, layer, width, net)


def wire_pads(net, a, b, layer, width=0.4, bend="x"):
    """L-shaped route between two pads."""
    x1, y1 = P(*a)
    x2, y2 = P(*b)
    if bend == "x":
        route(net, [(x1, y1), (x2, y1), (x2, y2)], layer, width)
    else:
        route(net, [(x1, y1), (x1, y2), (x2, y2)], layer, width)


def routes_power():
    """+5V spine (B.Cu y39.5), +3V3 trunk (B.Cu y29.45), VSYS (F), +12V (F)."""
    W5, W3 = 0.8, 0.6
    # ---- +5V ----
    # feed riser from J3.4 up to the spine, and west along y64 to RN1.1
    j34 = P("J3", 4)
    route("+5V", [j34, (j34[0], 39.5)], "B.Cu", W5)
    # RN1 pin 1 is the westernmost pad: approach from the west
    route("+5V", [j34, (23.0, j34[1]), (23.0, 64.0), P("RN1", 1)], "B.Cu", W5)
    # spine
    route("+5V", [(20.54, 39.5), (121.3, 39.5)], "B.Cu", W5)
    # DIP power stubs (pin 14 / 16 tops sit at y41 right under the spine)
    for ref, pin in [("U2", 14), ("U3", 14), ("U4", 14), ("U5", 14),
                     ("U6", 16), ("U7", 16)]:
        x, y = P(ref, pin)
        route("+5V", [(x, 39.5), (x, y)], "B.Cu", W5)
    # decoupling caps: +5V pad is the north pad at y41; stub through it
    for ref in ["C3", "C4", "C5", "C6", "C7", "C8"]:
        x, y = P(ref, 1)
        route("+5V", [(x, 39.5), (x, y)], "B.Cu", W5)
    # U7 spare receiver bias pins: east rail x121.3 + west corridor x109
    for pin in (16, 15, 12, 9):
        x, y = P("U7", pin)
        route("+5V", [(121.3, 39.5), (121.3, y), (x, y)], "B.Cu", 0.5)
    for pin in (4, 7):
        x, y = P("U7", pin)
        route("+5V", [(110.3, 39.5), (110.3, y), (x, y)], "B.Cu", 0.5)
    # LED resistor drops (pin 1 south ends at y30)
    for ref in ["R14", "R16", "R15"]:
        x, y = P(ref, 1)
        route("+5V", [(x, 39.5), (x, y)], "B.Cu", 0.5)
    # D1 anode + C1 bulk chain
    d1a = P("D1", 2)
    route("+5V", [(d1a[0], 39.5), d1a], "B.Cu", W5)
    c1 = P("C1", 1)
    route("+5V", [d1a, (d1a[0], 48.0), (c1[0], 48.0), c1], "B.Cu", W5)
    # R21 (fixed DS termination pull-up): drop east of R21, enter pad at y62
    r21 = P("R21", 1)
    route("+5V", [(r21[0] + 1.75, 39.5), (r21[0] + 1.75, r21[1]), r21],
          "B.Cu", 0.5)

    # ---- +3V3 ----
    # exit U1.36 south and run east under the module to a descent at x87.9
    # (a west-side descent walls off the whole indicator/R13 region)
    u36 = P("U1", 36)
    route("+3V3", [u36, (u36[0], 12.6), (87.9, 12.6), (87.9, 29.45)],
          "B.Cu", W3)
    # trunk, jogged south at x100 to clear the SD socket locating pegs
    route("+3V3", [(34.0, 29.45), (100.0, 29.45), (100.0, 30.6),
                   (115.42, 30.6)], "B.Cu", W3)
    # pull-up bank supply stubs (through the y31 pad into the y35 pad)
    for x in (34.0, 60.0, 73.0, 96.16):
        route("+3V3", [(x, 29.45), (x, 35.0)], "B.Cu", W3)
    route("+3V3", [(57.16, 29.45), (57.16, 31.0)], "B.Cu", W3)
    # SD pull-up banks (fed from the jogged trunk section)
    for x in (101.0, 114.5):
        route("+3V3", [(x, 30.6), (x, 37.8)], "B.Cu", W3)
    # SD VDD via + F stub
    sd4 = P("SD1", 4)
    via(sd4[0], 30.6, "+3V3")
    route("+3V3", [(sd4[0], 30.6), sd4], "F.Cu", W3)
    # C9/C10
    c9 = P("C9", 1)
    route("+3V3", [(c9[0], 29.45), c9, P("C10", 1)], "B.Cu", W3)

    # ---- VSYS (all F.Cu, west of the 3V3 trunk start) ----
    d1k = P("D1", 1)
    c2 = P("C2", 1)
    u39 = P("U1", 39)
    route("VSYS", [d1k, (d1k[0], 44.5), (c2[0], 44.5), c2], "F.Cu", W5)
    # north out of C2 pin 1, then into the x32 corridor between the R15
    # column and C2's own ground pad (which the corridor passes north of)
    route("VSYS", [c2, (c2[0], 38.5), (32.0, 38.5), (32.0, 10.5),
                   (u39[0], 10.5), u39], "F.Cu", W5)

    # ---- +12V (F.Cu) ----
    j31 = P("J3", 1)
    tp = P("TP1", 1)
    route("+12V", [j31, (j31[0], 50.0), (tp[0], 50.0), tp], "F.Cu", 0.5)

    # ---- GND rails through the finger pads (pours can't enter the tab
    # keepouts, so the ground fingers get explicit rails out to the pours) --
    # J1: every odd (F.Cu) pad is GND; rail through the pad tops, broken
    # around the key slot.  The relief cut-outs mean there is no longer any
    # board beside the tab at this y, so each half of the rail jogs north onto
    # the full-width board first and only then runs out past the keepout edge
    # to meet the pour.
    y = 67.95
    jog = L.tab_relief_y() - 0.6        # north of the reliefs' inboard edge
    s1 = L.key_slot_x(L.J1_CENTER_X, 17)
    hw = L.J1_TAB_W / 2
    wx, ex = L.J1_CENTER_X - hw + 0.65, L.J1_CENTER_X + hw - 0.65
    route("GND", [(29.6, jog), (wx, jog), (wx, y), (s1 - 0.85, y)], "F.Cu", 0.5)
    route("GND", [(s1 + 0.85, y), (ex, y), (ex, jog), (78.4, jog)], "F.Cu", 0.5)
    # J2: GNDs alternate faces and rails would wall off the signal escapes,
    # so each ground column gets a short stub to a via into the pours just
    # north of the keepout (vias are banned inside it).
    for p in (4, 6, 8):                      # B-only ground columns
        x, _ = P("J2", p)
        route("GND", [(x, 68.2), (x, 66.05)], "B.Cu", 0.5)
        via(x, 66.05, "GND", size=0.6, drill=0.3)
    # pin 2 shares its column with the DRV_SELD escape on F: offset its via
    x2, _ = P("J2", 2)
    route("GND", [(x2, 68.2), (x2, 67.1), (x2 + 1.28, 67.1),
                  (x2 + 1.28, 66.05)], "B.Cu", 0.5)
    via(x2 + 1.28, 66.05, "GND", size=0.6, drill=0.3)
    # columns with grounds on both faces share one via
    for pf, pb in ((11, 12), (15, 16), (19, 20)):
        x, _ = P("J2", pf)
        route("GND", [(x, 68.2), (x, 66.05)], "F.Cu", 0.5)
        route("GND", [(x, 68.2), (x, 66.05)], "B.Cu", 0.5)
        via(x, 66.05, "GND", size=0.6, drill=0.3)

    # ---- GND stitching vias ----
    for x, y in [(46, 18), (60, 18), (74, 18), (82, 18),
                 (104, 44), (120, 26), (128, 45), (88.5, 56), (17, 58),
                 (103, 62)]:
        via(x, y, "GND")


def routes_termbus():
    """J1 control inputs -> terminator SIPs -> 74LS05 inputs, plus the
    drive-select jumper wiring.

    Scheme: J1 finger escapes run north on B.Cu on the 2.54 grid (SIP pads
    sit on the half-grid, so escapes thread between them with 1.27 mm each
    side).  Horizontal runs live on F.Cu in 0.75 mm slots y=57.5..62.0;
    every B-vertical meets its F-horizontal at a 0.6/0.3 via.  SIP and DIP
    pads are through-hole, so they accept either layer directly."""
    V = dict(size=0.6, drill=0.3)

    def esc(x):                     # J1 finger escape start (inside pad)
        return (x, 68.5)

    def jx(ref, pin):
        return P(ref, pin)[0]

    # term nets: (slot_y, finger_x, rn1_pin, rn2_pin, U-entry (x_v, uref, upin))
    TERM = [
        ("WG_N",      57.5,  jx("J1", 6),  2, 2, (40.6,  "U2", 1)),
        ("STEP_N",    58.25, jx("J1", 24), 3, 3, (39.7,  "U2", 3)),
        ("DIR_N",     59.0,  jx("J1", 34), 4, 5, (36.6,  "U2", 5)),
        ("HS0_N",     59.75, jx("J1", 14), 5, 6, (47.0,  "U2", 9)),
        # HS1's entry horizontal crosses the TRK0 escape on B: hop it on F
        ("HS1_N",     60.5,  jx("J1", 18), 6, 7, (42.95, "U2", 11, "F")),
        ("HS2_N",     61.25, jx("J1", 4),  7, 8, (42.15, "U2", 13)),
        ("HS3_RWC_N", 62.0,  jx("J1", 2),  8, 4, (60.0,  "U3", 9)),
    ]
    for net, sy, xf, rp1, rp2, uentry in TERM:
        xv, uref, upin = uentry[0], uentry[1], uentry[2]
        entry_f = len(uentry) > 3
        p1 = P("RN1", rp1)[0]
        p2 = P("RN2", rp2)[0]
        ux, uy = P(uref, upin)
        # escape
        route(net, [esc(xf), (xf, sy)], "B.Cu")
        via(xf, sy, net, **V)
        # F horizontal across all taps
        lo, hi = min(p1, p2, xf, xv), max(p1, p2, xf, xv)
        route(net, [(lo, sy), (hi, sy)], "F.Cu")
        # SIP stubs (B)
        for p in (p1, p2):
            via(p, sy, net, **V)
            route(net, [(p, sy), (p, 64.0)], "B.Cu")
        # LS05 input entry: B vertical beside the DIP column + short jog.
        # If the vertical lands within via-pitch of a SIP stub, join the
        # stub with a B jog instead of adding a second via.
        near = min((p1, p2), key=lambda p: abs(xv - p))
        if entry_f:
            via(xv, sy, net, **V)
            route(net, [(xv, sy), (xv, uy)], "B.Cu")
            via(xv, uy, net, **V)
            route(net, [(xv, uy), (ux, uy)], "F.Cu")
        elif abs(xv - near) < 0.85:
            route(net, [(near, sy), (xv, sy), (xv, uy), (ux, uy)], "B.Cu")
        else:
            via(xv, sy, net, **V)
            route(net, [(xv, sy), (xv, uy), (ux, uy)], "B.Cu")

    # drive select lines: J4 columns run DS4..DS1 west->east (pin 1 east),
    # so the south-going stubs nest without crossing shallower slots
    DS = [
        ("DS4_N", 60.5,  jx("J1", 32), P("J4", 7), None),
        ("DS3_N", 59.75, jx("J1", 30), P("J4", 5), None),
        ("DS2_N", 58.25, jx("J1", 28), P("J4", 3), None),
        # DS1's via shifts east along its slot to clear the U4 pin-7 hole
        ("DS1_N", 57.5,  jx("J1", 26), P("J4", 1), 64.9),
    ]
    for net, sy, xf, (jxp, jyp), vx in DS:
        if vx is None:
            route(net, [esc(xf), (xf, sy)], "B.Cu")
            vx = xf
        else:
            route(net, [esc(xf), (xf, sy + 0.3), (vx, sy + 0.3), (vx, sy)],
                  "B.Cu")
        via(vx, sy, net, **V)
        route(net, [(vx, sy), (jxp, sy), (jxp, jyp)], "F.Cu")

    # ---- DS_SEL_N tree ----
    n = "DS_SEL_N"
    # main run above the SIP row, ending south into the J4 even-pad bus
    route(n, [(51.56, 65.5), (80.5, 65.5), (80.5, 63.54), (88.12, 63.54)],
          "F.Cu")
    # U3 pins 3+5: B collector in the gap EAST of the U3 column (keeps the
    # western lane region open), then a B jog at y58 to the unused pin-16
    # finger column, down to the main
    u33 = P("U3", 3)
    route(n, [u33, (52.6, u33[1]), (52.6, 58.0)], "B.Cu")
    route(n, [(51.56, 58.0), (53.2, 58.0)], "B.Cu")
    route(n, [(51.56, 58.0), (51.56, 65.5)], "B.Cu")
    via(51.56, 65.5, n, **V)
    # U3.11 leg: F west + south, via, join the B jog
    u311 = P("U3", 11)
    route(n, [u311, (53.2, u311[1]), (53.2, 56.55)], "F.Cu")
    via(53.2, 56.55, n, **V)
    route(n, [(53.2, 56.55), (53.2, 58.0)], "B.Cu")
    # east legs: J4.8 -> R22.1, then R21.2 and U6.12 via the pad-gap lane
    r221 = P("R22", 1)
    route(n, [(88.12, 63.54), (89.3, 63.54), (89.3, 63.9), (r221[0] + 1.7, 63.9),
              (r221[0] + 1.7, r221[1]), r221], "F.Cu")
    r212 = P("R21", 2)
    u612 = P("U6", 12)
    route(n, [r221, (r221[0], 60.3), (96.5, 60.3), (96.5, 49.89),
              (r212[0], 49.89), r212], "F.Cu")
    route(n, [(96.5, 49.89), (106.8, 49.89), (106.8, u612[1]), u612], "F.Cu")
    # select-monitor gate lives in U5's spare NAND (inputs tied): feed both
    # inputs from R21.2 via a vertical east of the U5 column
    route(n, [P("U5", 13), (86.2, 43.54), (86.2, 51.62), (r212[0] - 1.8, 51.62),
              r212], "B.Cu")
    route(n, [P("U5", 12), (86.2, 46.08)], "B.Cu")


def routes_outputs():
    """7438 outputs -> J1 fingers, J2 pin 1, differential data pairs,
    the receiver output (WR_RX) and WRITE FAULT input (WF_IN).

    Output escapes are B verticals like the term bus; they turn west/east
    on B 'lanes' threaded between the DIP pad rows (y = 41 + 2.54k + 1.27),
    which cross the F slot horizontals freely."""
    V = dict(size=0.6, drill=0.3)

    # SKC_N: J1-8 -> U4.11 via lane y42.27 and the U4/C6 gap vertical
    xf = P("J1", 8)[0]
    u = P("U4", 11)
    route("SKC_N", [(xf, 68.5), (xf, 42.27), (73.0, 42.27), (73.0, u[1]),
                    u], "B.Cu")

    # TRK0_N: J1-10 -> U4.8 via lane y44.81, jogging north around the
    # C4/C5 decoupling pads whose south pads pinch the lane
    xf = P("J1", 10)[0]
    u = P("U4", 8)
    route("TRK0_N", [(xf, 68.5), (xf, 44.81),
                     (47.0, 44.81), (47.0, 43.98), (49.6, 43.98),
                     (49.6, 44.81),
                     (60.0, 44.81), (60.0, 43.98), (62.6, 43.98),
                     (62.6, 44.81),
                     (70.3, 44.81), (70.3, u[1]), u], "B.Cu")

    # INDEX_N: J1-20 -> U4.3 via lane y47.35 (clear east of x49.6)
    xf = P("J1", 20)[0]
    u = P("U4", 3)
    route("INDEX_N", [(xf, 68.5), (xf, 47.35), (62.65, 47.35), (62.65, u[1]),
                      u], "B.Cu")

    # READY_N: escape stops at slot 57.5 (U3 col2 blocks further north),
    # crosses the STEP escape on F, then B down into U4.6
    xf = P("J1", 22)[0]
    u = P("U4", 6)
    route("READY_N", [(xf, 68.5), (xf, 57.5)], "B.Cu")
    via(xf, 57.5, "READY_N", **V)
    route("READY_N", [(xf, 57.5), (62.75, 57.5)], "F.Cu")
    via(62.75, 57.5, "READY_N", **V)
    route("READY_N", [(62.75, 57.5), (62.75, u[1]), u], "B.Cu")

    # WFAULT_N: the x47.0 HS0 entry blocks a straight climb; via at the
    # 8th sub-slot y62.75, F east past the DS region, B down into U5.3
    xf = P("J1", 12)[0]
    u = P("U5", 3)
    route("WFAULT_N", [(xf, 68.5), (xf, 62.75)], "B.Cu")
    via(xf, 62.75, "WFAULT_N", **V)
    route("WFAULT_N", [(xf, 62.75), (75.5, 62.75)], "F.Cu")
    via(75.5, 62.75, "WFAULT_N", **V)
    route("WFAULT_N", [(75.5, 62.75), (75.5, u[1]), u], "B.Cu")

    # DRV_SELD_N: J2-1 (F-only pad) -> U5.6, swinging around FG1 and J4
    n = "DRV_SELD_N"
    xf = P("J2", 1)[0]
    u = P("U5", 6)
    route(n, [(xf, 68.5), (xf, 65.9)], "F.Cu")
    via(xf, 65.9, n, **V)
    route(n, [(xf, 65.9), (97.7, 65.9), (97.7, 64.0), (89.5, 64.0),
              (89.5, 52.43), (78.6, 52.43), (78.6, u[1]), u], "B.Cu")

    # ---- write data pair: J2-13/14 -> R12 -> U7.1/2 --------------------
    # +WR: F-only finger pad, all-F to R12.1, then B west on lane y60.3
    # (south of the U7 +5V rail), via up to enter U7.1 from the north
    p13 = P("J2", 13)[0]
    r1 = P("R12", 1)
    route("WR_DATA_P", [(p13, 68.5), (p13, 64.2), (123.85, 64.2),
                        (123.85, r1[1]), r1], "F.Cu")
    u71 = P("U7", 1)
    route("WR_DATA_P", [r1, (124.6, r1[1]), (124.6, 60.3), (122.05, 60.3),
                        (122.05, 42.27)], "B.Cu")
    via(122.05, 42.27, "WR_DATA_P", **V)
    route("WR_DATA_P", [(122.05, 42.27), (u71[0], 42.27), u71], "F.Cu")

    # -WR: B finger pad, B to R12.2 (east swing around the R12 column),
    # then north and over to U7.2 on F
    p14 = P("J2", 14)[0]
    r2 = P("R12", 2)
    route("WR_DATA_M", [(p14, 68.5), (p14, 65.2), (127.4, 65.2),
                        (127.4, r2[1]), r2], "B.Cu")
    u72 = P("U7", 2)
    route("WR_DATA_M", [r2, (r2[0], 44.81)], "B.Cu")
    via(r2[0], 44.81, "WR_DATA_M", **V)
    route("WR_DATA_M", [(r2[0], 44.81), (113.35, 44.81), (113.35, u72[1]),
                        u72], "F.Cu")

    # ---- read data pair: U6.2/3 -> J2-17/18 ----------------------------
    # +RD on F via lane y47.35; -RD on B via y64.5
    # +RD swings north over the resistor rows (the U7 +5V rails wall off
    # the middle); -RD hops the two rail walls on F at the y49.89 pad gap
    p17 = P("J2", 17)[0]
    u62 = P("U6", 2)
    route("RD_DATA_P", [u62, (99.6, u62[1]), (99.6, 36.3), (p17, 36.3),
                        (p17, 68.5)], "F.Cu")
    p18 = P("J2", 18)[0]
    u63 = P("U6", 3)
    route("RD_DATA_M", [u63, (99.6, u63[1]), (99.6, 49.89),
                        (108.6, 49.89)], "B.Cu")
    via(108.6, 49.89, "RD_DATA_M", **V)
    route("RD_DATA_M", [(108.6, 49.89), (127.0, 49.89)], "F.Cu")
    via(127.0, 49.89, "RD_DATA_M", **V)
    route("RD_DATA_M", [(127.0, 49.89), (p18, 49.89), (p18, 68.5)], "B.Cu")

    # ---- WR_RX: U7.3 -> U3.1, all-F on the y47.35 pad-gap lane ---------
    u73 = P("U7", 3)
    u31 = P("U3", 1)
    route("WR_RX", [u73, (113.5, u73[1]), (113.5, 47.35), (49.75, 47.35),
                    (49.75, u31[1]), u31], "F.Cu")

    # ---- WF_IN: JP1.2 -> R10.1 -> U5.1 ---------------------------------
    n = "WF_IN"
    jp = P("JP1", 2)
    r10 = P("R10", 1)
    esc = r10[0] - 1.4          # riser column just west of R10
    route(n, [jp, (jp[0], 4.6), (69.29, 4.6), (69.29, 11.9), (esc, 11.9),
              (esc, r10[1]), r10], "B.Cu")
    u51 = P("U5", 1)
    route(n, [r10, (r10[0], 26.2)], "B.Cu")
    via(r10[0], 26.2, n, **V)
    route(n, [(r10[0], 26.2), (r10[0], 39.75), (78.3, 39.75),
              (78.3, u51[1]), u51], "F.Cu")


def routes_led_cluster():
    """Hand-routed west indicator cluster: the TO-92 needs exact-column
    entries (1.27 mm pad pitch) that the grid router can't guarantee."""
    # every elbow here rides on a pad column, so derive them from the pads
    q1b, q1c = P("Q1", 2), P("Q1", 3)
    d2k, d2a = P("D2", 1), P("D2", 2)
    d3a = P("D3", 2)
    # Q1 base from R13
    route("Q1_B", [P("R13", 2), (18.0, 21.3), (q1b[0], 21.3), q1b], "B.Cu")
    # LED_SINK: front-LED header -> Q1 collector -> ACT LED cathode
    route("LED_SINK", [P("J7", 2), (28.54, 26.5), (q1c[0], 26.5), q1c], "F.Cu")
    route("LED_SINK", [q1c, (q1c[0], 34.6), (d2k[0], 34.6), d2k], "B.Cu")
    # LED anodes, each on its own lane: LED1 loops west around D3 to come at
    # D2's anode from below, LED2 drops straight onto D3's
    route("LED1_A", [P("R14", 2), (22.0, 23.0), (4.0, 23.0), (4.0, 30.4),
                     (d2a[0], 30.4), d2a], "F.Cu")
    route("LED2_A", [P("R16", 2), (26.0, 24.2), (9.9, 24.2), (9.9, d3a[1]), d3a],
          "F.Cu")


def routes_gpio_hand():
    """Verified hand routes for the two chronically failing nets; the maze
    router seeds its tree from these and finishes the stragglers."""
    V = dict(size=0.6, drill=0.3)
    # HS1: U2.10 -> R5.2 -> GP14, all F (crosses only B verticals)
    route("HS1", [P("U2", 10), (46.9, 51.16), (46.9, 36.6), (81.6, 36.6),
                  (81.6, 29.0), (80.72, 29.0), P("U1", 19)], "F.Cu", 0.3)
    route("HS1", [(81.6, 35.0), P("R5", 2)], "F.Cu", 0.3)

    # SELECTED: GP11/R8.2 node, link over the +5V spine on F, mid-gap trunk
    # between the U4 columns, row taps straight through to U5
    n = "SELECTED"
    route(n, [P("U1", 15), (69.29, 26.78), (69.29, 31.0), P("R8", 2)],
          "F.Cu", 0.3)
    route(n, [P("R8", 2), (66.35, 31.0), (66.35, 38.5)], "B.Cu", 0.3)
    via(66.35, 38.5, n, **V)
    route(n, [(66.35, 38.5), (66.35, 43.54)], "F.Cu", 0.3)
    route(n, [P("U4", 2), P("U5", 2)], "F.Cu", 0.3)          # y43.54 row
    route(n, [(66.35, 43.54), (66.35, 46.6)], "F.Cu", 0.3)
    via(66.35, 46.6, n, **V)
    route(n, [(66.35, 46.6), (66.35, 51.16)], "B.Cu", 0.3)
    via(66.35, 51.16, n, **V)
    route(n, [P("U4", 5), P("U5", 5)], "F.Cu", 0.3)          # y51.16 row
    route(n, [(75.75, 51.16), (75.75, 48.62), P("U5", 4)], "F.Cu", 0.3)
    route(n, [P("U5", 4), P("U5", 11)], "F.Cu", 0.3)   # spare-gate output
    # R13 base-divider leg: straight run under the socketed module at
    # y25.4, jogging around the U1.13 relief via, into GP11's pad
    route(n, [P("R13", 1), (18.0, 28.9), (19.5, 28.9), (19.5, 25.4),
              (39.2, 25.4), (39.2, 24.5), (40.95, 24.5), (40.95, 25.4),
              (64.6, 25.4), (64.6, 24.5), (66.35, 24.5), (66.35, 25.4),
              (70.56, 25.4), P("U1", 15)], "B.Cu", 0.3)

    # HS2: U2.12 -> north over the module (threading the pad-row mid-gaps
    # at x38.81) -> east along y7.6 -> down the module's east flank to R6.2,
    # with a T-stub into GP16 on the way
    n = "HS2"
    route(n, [P("U2", 12), (44.3, 46.08), (44.3, 47.9), (39.3, 47.9),
              (39.3, 39.8), (38.81, 39.8), (38.81, 7.6), (84.9, 7.6),
              (84.9, 29.2), (86.0, 29.2), P("R6", 2)], "F.Cu", 0.3)
    route(n, [P("U1", 21), (83.26, 7.6)], "F.Cu", 0.3)

    # HS0: GP4 drop into R4.2, then straight up the C4/U2 corridor to U2.10
    n = "HS0"
    route(n, [P("U1", 6), (47.7, 28.5), (47.0, 28.5), P("R4", 2)],
          "F.Cu", 0.3)

    # WR_DATA: GP3 drop into R9.2, then B under the west walls, hopping to
    # F for the U3.2 entry (SKC's B lane blocks a straight climb)
    n = "WR_DATA"
    route(n, [P("U1", 5), (45.16, 28.5), (45.75, 28.5), (45.75, 33.2),
              (44.16, 33.2), P("R9", 2)], "F.Cu", 0.3)
    route(n, [P("R9", 2), (44.16, 37.35), (52.5, 37.35), (52.5, 37.9)],
          "B.Cu", 0.3)
    via(52.5, 37.9, n, **V)
    route(n, [(52.5, 37.9), (52.5, 43.54), P("U3", 2)], "F.Cu", 0.3)

    # GND relief for pads the pours can no longer reach through the
    # routed maze: short links to neighbouring GND pads or stitch vias
    g = "GND"
    c22 = P("C2", 2)
    route(g, [P("C1", 2), (29.5, 44.3), (c22[0], 44.3), c22], "B.Cu", 0.4)
    route(g, [P("U3", 13), (59.9, 43.54), (59.9, 46.0), P("C5", 2)],
          "F.Cu", 0.3)
    route(g, [P("U4", 7), (68.9, 56.24), (68.9, 56.5), (69.5, 56.5)],
          "B.Cu", 0.3)
    via(69.5, 56.5, g, size=0.6, drill=0.3)
    route(g, [P("U5", 7), (78.7, 56.24), (78.7, 56.5)], "B.Cu", 0.3)
    via(78.7, 56.5, g, size=0.6, drill=0.3)
    route(g, [P("C6", 2), (74.3, 44.3)], "F.Cu", 0.3)
    via(74.3, 44.3, g, size=0.6, drill=0.3)
    route(g, [P("U1", 18), (78.18, 28.6)], "F.Cu", 0.3)
    via(78.18, 28.6, g, size=0.6, drill=0.3)
    r102 = P("R10", 2)
    route(g, [r102, (r102[0] + 1.6, r102[1])], "B.Cu", 0.3)
    via(r102[0] + 1.6, r102[1], g, size=0.6, drill=0.3)
    route(g, [P("U2", 7), (34.9, 56.24)], "F.Cu", 0.3)
    via(34.9, 56.24, g, size=0.6, drill=0.3)
    route(g, [P("U1", 13), (65.48, 25.2)], "B.Cu", 0.3)
    via(65.48, 25.2, g, size=0.6, drill=0.3)
    route(g, [P("U1", 23), (78.18, 6.6)], "B.Cu", 0.3)
    via(78.18, 6.6, g, size=0.6, drill=0.3)
    route(g, [P("C10", 2), (99.2, 15.0)], "B.Cu", 0.3)
    via(99.2, 15.0, g, size=0.6, drill=0.3)
    route(g, [P("U1", 3), (40.08, 25.2)], "B.Cu", 0.3)
    via(40.08, 25.2, g, size=0.6, drill=0.3)
    route(g, [P("J5", 1), (46.0, 1.5)], "B.Cu", 0.3)
    via(46.0, 1.5, g, size=0.6, drill=0.3)
    route(g, [P("U1", 38), (40.08, 10.6)], "B.Cu", 0.3)
    via(40.08, 10.6, g, size=0.6, drill=0.3)
    bz2 = P("BZ1", 2)
    route(g, [bz2, (22.4, bz2[1])], "F.Cu", 0.3)
    via(22.4, bz2[1], g, size=0.6, drill=0.3)   # clear of BZ1's silk ring

    # SD pull-up corner joins (the SD pad row + 3V3 stubs pinch this zone)
    n = "SD_MISO"
    route(n, [P("SD1", 7), (122.85, 32.15)], "F.Cu", 0.3)
    via(122.85, 32.15, n, **V)
    route(n, [(122.85, 32.15), (122.85, 33.5), (124.66, 33.5), P("R18", 2)],
          "B.Cu", 0.3)
    n = "SD_DAT1"
    route(n, [P("SD1", 8), (124.55, 32.9), (112.75, 32.9)], "F.Cu", 0.3)
    via(112.75, 32.9, n, **V)
    route(n, [(112.75, 32.9), (112.75, 37.8), P("R19", 2)], "B.Cu", 0.3)


# Decoupling-cap grounds that end up fenced in.  Their inter-DIP corridors
# seal once the signals fill them, and there is no B.Cu pour beneath to via
# down to, so these rescues compete for space as first-class nets in the
# router's search instead of being fitted afterwards.  Each lists alternate
# destinations; the first the maze can reach wins.  (U3.13, a spare-gate
# tie-down, rides along on its existing relief stub to C5.2.)
GND_STUBS = [
    ("GND:C5.2", ("C5", 2),
     (("U4", 7), ("C4", 2), ("C6", 2), ("U3", 7), ("U5", 7))),
    ("GND:C3.2", ("C3", 2),
     (("C2", 2), ("C1", 2), ("U2", 7), ("C4", 2))),
    # the SD socket's second ground and the Pico's pin 23 box in the same way
    ("GND:SD1.3", ("SD1", 3),
     (("SD1", 6), ("U6", 15), ("C8", 2), ("U7", 14))),
    ("GND:U1.23", ("U1", 23),
     (("R10", 2), ("U1", 28), ("U1", 18), ("C10", 2))),
    ("GND:U1.3", ("U1", 3),
     (("C2", 2), ("U1", 38), ("C3", 2), ("U1", 8))),
    ("GND:U1.8", ("U1", 8),
     (("U1", 13), ("U1", 3), ("U3", 13), ("C4", 2))),
]


def routes_gpio_auto():
    """Everything else: grid maze router over the as-built obstacles."""
    import netlist
    import router
    import sys
    order = ["HS0", "TRK0", "SKC", "HS1", "HS2", "HS3", "BUZZ", "RD_DATA",
             "SERVO_GATE", "WF", "UART_TX", "UART_RX", "INDEX", "READY",
             "WR_DATA", "WG_GATED", "STEP_GATED", "DIR_IN", "HS0",
             "SD_CS", "SD_MISO", "SD_SCK", "SD_MOSI", "SD_DAT1", "SD_DAT2",
             "RUN", "BUZZ_DRV", "LEDX_A", "SELECTED"] \
        + [s[0] for s in GND_STUBS]
    import random
    gp = sys.modules[__name__]
    nets = netlist.nets()
    snap = (len(SEGS), len(VIAS), len(TRACKS))
    best = None
    for attempt in range(40):
        del SEGS[snap[0]:], VIAS[snap[1]:], TRACKS[snap[2]:]
        g = router.build_grid(gp)
        fails = []
        for n in order:
            stub = next((s for s in GND_STUBS if s[0] == n), None)
            if stub:
                if not any(gnd_link(g, stub[1], d, quiet=True)
                           for d in stub[2]):
                    fails.append(n)
            elif router.route_net(gp, g, n, nets[n]):
                fails.append(n)
        if not fails:
            print(f"ROUTER complete on pass {attempt}")
            return
        if best is None or len(fails) < len(best[0]):
            best = (list(fails), SEGS[snap[0]:], VIAS[snap[1]:],
                    TRACKS[snap[2]:])
        if attempt < 2:
            order = fails + [n for n in order if n not in fails]
        else:
            random.Random(attempt).shuffle(order)
    del SEGS[snap[0]:], VIAS[snap[1]:], TRACKS[snap[2]:]
    SEGS.extend(best[1]); VIAS.extend(best[2]); TRACKS.extend(best[3])
    print("ROUTER best-pass unresolved:", best[0])


def gnd_link(g, src, dst, width=0.3, quiet=False):
    """Maze-route GND between two specific pads.  The pours are the primary
    ground path, but the routing maze walls some pads off into fill fragments
    that reach nothing; these links tie them back to the main plane."""
    import router
    import sys
    gp = sys.modules[__name__]
    net = "GND"

    def pad_at(ref, pad):
        x, y = P(ref, pad)
        info = PAD_INFO[(ref, str(pad))]
        lay = router.LAYERS if info["through"] else tuple(
            l for l in router.LAYERS if l in info["layers"])
        return (x, y), router.cell(x, y), lay

    (sx, sy), (si, sj), slay = pad_at(*src)
    (dx, dy), (di, dj), dlay = pad_at(*dst)
    path = router.bfs(g, {(l, si, sj) for l in slay}, (di, dj), dlay, net)
    if path is None:
        if not quiet:
            print(f"GND link FAIL {src} -> {dst}")
        return False
    n0 = len(SEGS)
    router.emit_path(gp, g, net, path, (dx, dy), width)
    gx, gy = router.pos(si, sj)
    if abs(gx - sx) > 0.02 or abs(gy - sy) > 0.02:
        route(net, [(sx, sy), (gx, gy)], slay[0], width)
    for s in SEGS[n0:]:
        g.add_seg(*s)
    return True


# Worklist for routes_gnd_stitch, produced by tools/stitch.py under KiCad's
# python.  Re-run it after ANY routing or placement change: the pours
# re-fragment and these entries go stale.
# Coordinate-based entries are the fragile ones: they go stale the moment the
# maze router lands differently, so re-derive them (not just the links) from a
# filled board whenever routing changes.
GND_STITCH_VIAS = [
    (11.75, 35.98),     # west pour: BZ1 / D3 / Q1 region
    (54.92, 54.28),     # U3/U4 corridor: C5.2, U3.13, U4.7
]
GND_BRIDGES = []        # ((x1, y1), (x2, y2), layer) same-layer pour bridges
GND_LINKS = [
    (("C6", 2), ("U5", 7)),
    (("SD1", 6), ("SD1", "SH")),
    (("U1", 18), ("R10", 2)),       # Pico pins straddle the pour seams
    (("C7", 2), ("U6", 4), ("R22", 2), ("U6", 7)),
]


def routes_gnd_stitch():
    """Rescue GND pads the pours can't reach once everything else is routed."""
    import router
    import sys
    g = router.build_grid(sys.modules[__name__])
    for x, y in GND_STITCH_VIAS:
        via(x, y, "GND")
    for a, b, layer in GND_BRIDGES:
        route("GND", [a, b], layer, 0.4)
    for src, *dsts in GND_LINKS:
        if not any(gnd_link(g, src, d, quiet=True) for d in dsts):
            print(f"GND link FAIL {src} -> any of {dsts}")


def build_routes():
    routes_power()
    routes_termbus()
    routes_outputs()
    routes_led_cluster()
    routes_gpio_hand()
    routes_gpio_auto()
    routes_gnd_stitch()


# ---------------------------------------------------------------------------
# assemble
# ---------------------------------------------------------------------------

def build():
    with open(os.path.join(os.path.dirname(__file__), "sch_uuids.json")) as f:
        sch_uuids = json.load(f)

    doc = ["kicad_pcb", ["version", "20240108"], ["generator", q("pico506_gen")],
           ["general", ["thickness", "1.6"], ["legacy_teardrops", "no"]],
           ["paper", q("A3")],
           ["title_block",
            ["title", q("Pico506 — ST-506/MFM/RLL hard drive emulator")],
            ["date", q("2026-07-27")], ["rev", q("1.0")]],
           ["layers",
            ["0", q("F.Cu"), "signal"],
            ["31", q("B.Cu"), "signal"],
            ["32", q("B.Adhes"), "user", q("B.Adhesive")],
            ["33", q("F.Adhes"), "user", q("F.Adhesive")],
            ["34", q("B.Paste"), "user"],
            ["35", q("F.Paste"), "user"],
            ["36", q("B.SilkS"), "user", q("B.Silkscreen")],
            ["37", q("F.SilkS"), "user", q("F.Silkscreen")],
            ["38", q("B.Mask"), "user"],
            ["39", q("F.Mask"), "user"],
            ["40", q("Dwgs.User"), "user", q("User.Drawings")],
            ["41", q("Cmts.User"), "user", q("User.Comments")],
            ["44", q("Edge.Cuts"), "user"],
            ["45", q("Margin"), "user"],
            ["46", q("B.CrtYd"), "user", q("B.Courtyard")],
            ["47", q("F.CrtYd"), "user", q("F.Courtyard")],
            ["48", q("B.Fab"), "user"],
            ["49", q("F.Fab"), "user"]],
           ["setup", ["pad_to_mask_clearance", "0"],
            ["allow_soldermask_bridges_in_footprints", "no"]]]

    for name, num in NETS.items():
        doc.append(["net", str(num), q(name)])

    for c in netlist.COMPONENTS:
        doc.append(place_footprint(c["ref"], c, sch_uuids))
    place_references()

    build_routes()
    doc.extend(TRACKS)
    doc.extend(outline_nodes())
    doc.extend(texts())
    doc.extend(zones())
    return doc


if __name__ == "__main__":
    out = os.path.join(HW, "pico506.kicad_pcb")
    doc = build()
    with open(out, "w") as f:
        f.write(sexpr.dumps(doc) + "\n")
    print(f"wrote {out}  ({len(TRACKS)} track items)")
