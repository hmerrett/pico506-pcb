#!/usr/bin/env python3
"""Generate the custom footprints into ../pico506-lib.pretty/."""

import os
import re
import shutil

import layout
import sexpr
from sexpr import q

OUT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "pico506-lib.pretty"))
KICAD_FP = "/Applications/KiCad/KiCad.app/Contents/SharedSupport/footprints"


def fmt(v):
    s = f"{v:.4f}".rstrip("0").rstrip(".")
    return s if s not in ("-0", "") else "0"


def fp_header(name, descr, attr="smd"):
    node = ["footprint", q(name), ["version", "20240108"],
            ["generator", q("pico506_gen")], ["layer", q("F.Cu")],
            ["descr", q(descr)], ["attr", attr]]
    return node


def text(kind, s, x, y, layer, size=1.0, hide=False, mirror=False):
    just = ["justify", "mirror"] if mirror else None
    eff = ["effects", ["font", ["size", fmt(size), fmt(size)],
                       ["thickness", fmt(size * 0.15)]]]
    if just:
        eff.append(just)
    n = ["fp_text", kind, q(s), ["at", fmt(x), fmt(y), "0"],
         ["layer", q(layer)]]
    if hide:
        n.append(["hide", "yes"])
    n.append(eff)
    return n


def line(x1, y1, x2, y2, layer, w=0.12):
    return ["fp_line", ["start", fmt(x1), fmt(y1)], ["end", fmt(x2), fmt(y2)],
            ["stroke", ["width", fmt(w)], ["type", "solid"]], ["layer", q(layer)]]


def smd_pad(num, x, y, w, h, layers):
    return ["pad", q(str(num)), "smd", "rect",
            ["at", fmt(x), fmt(y)], ["size", fmt(w), fmt(h)],
            ["layers"] + [q(l) for l in layers]]


def tht_pad(num, x, y, dia, drill, shape="circle"):
    return ["pad", q(str(num)), "thru_hole", shape,
            ["at", fmt(x), fmt(y)], ["size", fmt(dia), fmt(dia)],
            ["drill", fmt(drill)],
            ["layers", q("*.Cu"), q("*.Mask")],
            ["remove_unused_layers", "no"]]


def edge_connector(name, n_cols, tab_w, descr):
    """Card-edge footprint.  Local origin: center of finger span, on the MAIN
    board edge line.  +y extends outward (south) to the tab tip at +5.0.

    Even pins (2,4,..) on B.Cu (the face that points down in the drive),
    odd pins (1,3,..) directly opposite on F.Cu.  Pin 2 at the WEST (-x) end.
    """
    fp = fp_header(name, descr)
    tip = layout.TAB_PROTRUDE
    plen = layout.FINGER_LEN - layout.EDGE_SETBACK
    pw = layout.FINGER_W
    span = (n_cols - 1) * layout.FINGER_PITCH
    xs = [-span / 2 + k * layout.FINGER_PITCH for k in range(n_cols)]
    pad_cy = tip - layout.EDGE_SETBACK - plen / 2

    fp.append(text("reference", "REF**", 0, -plen + 2.2, "F.SilkS", hide=False))
    fp.append(text("value", name, 0, -plen - 0.2, "F.Fab"))

    for k, x in enumerate(xs):
        even = 2 * k + 2
        odd = 2 * k + 1
        fp.append(smd_pad(even, x, pad_cy, pw, plen, ["B.Cu", "B.Mask"]))
        fp.append(smd_pad(odd, x, pad_cy, pw, plen, ["F.Cu", "F.Mask"]))

    # silk pin labels above the finger area (clear of gold)
    ytxt = tip - plen - 1.4
    fp.append(text("user", "1", xs[0], ytxt, "F.SilkS", 0.9))
    fp.append(text("user", str(2 * n_cols - 1), xs[-1], ytxt, "F.SilkS", 0.9))
    fp.append(text("user", "2", xs[0], ytxt, "B.SilkS", 0.9, mirror=True))
    fp.append(text("user", str(2 * n_cols), xs[-1], ytxt, "B.SilkS", 0.9, mirror=True))

    # fab outline of the tab (edge cuts themselves live in the board file)
    hw = tab_w / 2
    cc = layout.TAB_CORNER
    for layer in ("F.Fab",):
        fp.append(line(-hw, 0, -hw, tip - cc, layer))
        fp.append(line(-hw, tip - cc, -hw + cc, tip, layer))
        fp.append(line(-hw + cc, tip, hw - cc, tip, layer))
        fp.append(line(hw - cc, tip, hw, tip - cc, layer))
        fp.append(line(hw, tip - cc, hw, 0, layer))
    fp.append(text("user", "hard gold + 30 deg bevel", 0, tip - plen / 2 - 3.2,
                   "F.Fab", 0.8))
    return fp


def power_header():
    """AMP 350211-1 formed for rear entry: face flush with the rear edge,
    hole row 0.400 in inboard.  Local origin: center of the 4-hole row;
    +y toward the rear edge (face at +10.16)."""
    fp = fp_header("PWR_MATE-N-LOK_350211_Horizontal",
                   "AMP/TE 350211-1 4-pos MATE-N-LOK, legs formed 90 deg for "
                   "rear entry (as on Seagate drives); mates AMP 1-480424-0",
                   attr="through_hole")
    xs = [-7.62, -2.54, 2.54, 7.62]
    for i, x in enumerate(xs):
        fp.append(tht_pad(i + 1, x, 0, 3.6, 1.8,
                          shape="rect" if i == 0 else "circle"))
    face = layout.J3_ROW_SETBACK
    back = 0.9
    # exactly the 1.00 in housing width, no slop: the connector sits far enough
    # west that even 0.3 mm of margin pushed its outline off the board edge,
    # and the RN1 terminator is only just clear to the east
    hw = 25.4 / 2
    fp.append(text("reference", "REF**", 0, -4.4, "F.SilkS"))
    fp.append(text("value", "AMP 350211-1", 0, -6.2, "F.Fab"))
    # Housing outline (lying flat, openings toward the rear edge).  The body's
    # true north face is at `back`, but the pin pads straddle it, so the silk
    # edge is drawn at `silk_back` to stay off them; F.Fab below keeps the real
    # outline.  Pin labels likewise sit north of the pads, not on them.
    silk_back = 2.2
    fp.append(line(-hw, silk_back, hw, silk_back, "F.SilkS"))
    fp.append(line(-hw, silk_back, -hw, face - 0.2, "F.SilkS"))
    fp.append(line(hw, silk_back, hw, face - 0.2, "F.SilkS"))
    fp.append(text("user", "1:+12V", xs[0], -2.7, "F.SilkS", 0.8))
    fp.append(text("user", "4:+5V", xs[3], -2.7, "F.SilkS", 0.8))
    for layer in ("F.Fab",):
        fp.append(line(-hw, back, hw, back, layer))
        fp.append(line(-hw, face, hw, face, layer))
        fp.append(line(-hw, back, -hw, face, layer))
        fp.append(line(hw, back, hw, face, layer))
    # courtyard: the housing footprint itself is the limit here
    fp.append(line(-hw, -2.2, hw, -2.2, "F.CrtYd", 0.05))
    fp.append(line(-hw, face + 0.3, hw, face + 0.3, "F.CrtYd", 0.05))
    fp.append(line(-hw, -2.2, -hw, face + 0.3, "F.CrtYd", 0.05))
    fp.append(line(hw, -2.2, hw, face + 0.3, "F.CrtYd", 0.05))
    return fp


def faston_tab():
    fp = fp_header("Faston_Tab_AMP61761",
                   "Frame ground: AMP 61761-2 0.187in PCB faston tab "
                   "(3.3mm hole), or bolt a ring lug", attr="through_hole")
    fp.append(tht_pad(1, 0, 0, 7.0, 3.3))
    fp.append(text("reference", "REF**", 0, -4.8, "F.SilkS"))
    fp.append(text("value", "FRAME GND", 0, 4.8, "F.Fab"))
    fp.append(text("user", "FRAME GND", 0, 4.8, "F.SilkS", 0.8))
    return fp


def write(fp_node):
    name = sexpr.uq(fp_node[1])
    path = os.path.join(OUT, f"{name}.kicad_mod")
    with open(path, "w") as f:
        f.write(sexpr.dumps(fp_node) + "\n")
    print("wrote", os.path.basename(path))


def main():
    os.makedirs(OUT, exist_ok=True)
    write(edge_connector("EdgeConn_ST506_J1_34", 17, layout.J1_TAB_W,
                         "ST-506 J1 control, 34-pin card edge, 0.100in pitch, "
                         "key slot pins 4-6, mates 3M 3463 / AMP 88373-3"))
    write(edge_connector("EdgeConn_ST506_J2_20", 10, layout.J2_TAB_W,
                         "ST-506 J2 data, 20-pin card edge, 0.100in pitch, "
                         "key slot pins 4-6, mates 3M 3461 / AMP 88373-6"))
    write(power_header())
    write(faston_tab())
    # stock copies so the project is self-contained
    copy_pico(f"{KICAD_FP}/Module.pretty/RaspberryPi_Pico_Common_THT.kicad_mod",
              os.path.join(OUT, "RaspberryPi_Pico_Common_THT.kicad_mod"))
    print("copied RaspberryPi_Pico_Common_THT (inner layers dropped)")
    tighten_sd_courtyard(
        f"{KICAD_FP}/Connector_Card.pretty/SD_Hirose_DM1AA_SF_PEJ82.kicad_mod",
        os.path.join(OUT, "SD_Hirose_DM1AA_SF_PEJ82.kicad_mod"))
    print("copied SD_Hirose_DM1AA_SF_PEJ82 (courtyard tightened)")


def copy_pico(src, dst):
    """Copy the Pico module footprint, dropping inner-layer references.

    Its "Antenna Copper Keep Out" zone enumerates every copper layer up to
    In30.Cu.  This board only has F.Cu and B.Cu, so pcbnew silently drops the
    rest whenever it saves — which left the board's copy permanently
    "not matching" the library.  Same keepout, just the layers we have.
    """
    with open(src) as f:
        node = sexpr.loads(f.read())
    for item in node:
        if not isinstance(item, list) or sexpr.tag(item) != "zone":
            continue
        lays = sexpr.find(item, "layers")
        if lays:
            lays[:] = [lays[0]] + [l for l in lays[1:]
                                   if not re.fullmatch(r'"In\d+\.Cu"', l)]
    with open(dst, "w") as f:
        f.write(sexpr.dumps(node) + "\n")


def tighten_sd_courtyard(src, dst):
    """Copy the stock SD socket, pulling its courtyard in to the body.

    The stock courtyard stands 1.6 mm off the socket outline.  Nothing here
    needs that much: the card ejects over the board's north edge rather than
    across the board, so the margin is plain assembly slop, and at 1.6 mm it
    collides with C9 and the H2 mounting hole even though those are 1-2 mm
    clear of the actual socket.  Redrawn as the silk outline + 0.25 mm.
    """
    with open(src) as f:
        node = sexpr.loads(f.read())
    box = None
    for item in node:
        if not isinstance(item, list) or sexpr.tag(item) not in (
                "fp_line", "fp_rect", "fp_poly", "fp_circle", "fp_arc"):
            continue
        lay = sexpr.find(item, "layer")
        if not lay or sexpr.uq(lay[1]) != "F.SilkS":
            continue
        for key in ("start", "end", "center", "mid"):
            n = sexpr.find(item, key)
            if not n:
                continue
            x, y = float(n[1]), float(n[2])
            box = (min(box[0], x), min(box[1], y), max(box[2], x),
                   max(box[3], y)) if box else (x, y, x, y)
    m = 0.25
    x0, y0, x1, y1 = box[0] - m, box[1] - m, box[2] + m, box[3] + m
    kept = [i for i in node
            if not (isinstance(i, list)
                    and sexpr.find(i, "layer")
                    and sexpr.uq(sexpr.find(i, "layer")[1]) == "F.CrtYd")]
    for a, b in (((x0, y0), (x1, y0)), ((x1, y0), (x1, y1)),
                 ((x1, y1), (x0, y1)), ((x0, y1), (x0, y0))):
        kept.append(line(a[0], a[1], b[0], b[1], "F.CrtYd", 0.05))
    with open(dst, "w") as f:
        f.write(sexpr.dumps(kept) + "\n")


if __name__ == "__main__":
    main()
