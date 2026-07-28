#!/usr/bin/env python3
"""Generate pico506.kicad_sch from netlist.py + parts.py.

Connectivity style: every signal pin gets a global label at its tip; power
pins get power symbols (with stub wires when the pin exits sideways); unused
pins get no-connect markers.  Positions are all on the 1.27 mm grid.
"""

import uuid as uuidlib

import netlist
import parts
import sexpr
from sexpr import q

ROOT_UUID = "e5a1a1de-0000-4000-8000-000000000001"
PROJECT = "pico506"

POWER_NETS = {"GND": "power:GND", "+5V": "power:+5V",
              "+3V3": "power:+3V3", "+12V": "power:+12V"}

SYMS = parts.all_symbols()
BYREF = netlist.by_ref()

_uid_counter = 0


def uid():
    global _uid_counter
    _uid_counter += 1
    return str(uuidlib.uuid5(uuidlib.NAMESPACE_URL, f"pico506-sch-{_uid_counter}"))


def snap(v):
    return round(v / 1.27) * 1.27


def fmt(v):
    s = f"{v:.4f}".rstrip("0").rstrip(".")
    return s if s not in ("-0", "") else "0"


# ---------------------------------------------------------------------------
# symbol geometry
# ---------------------------------------------------------------------------

def unit_pins(libid, unit):
    """[(number, lx, ly, angle_deg)] for a unit (styles 0/1 + common unit 0)."""
    sym = SYMS[libid]
    base = sexpr.sym_name(sym).split(":", 1)[-1]
    # embedded parent name contains ':'; children are "<base>_u_s"
    out = []
    for child in sexpr.find_all(sym, "symbol"):
        cn = sexpr.sym_name(child)
        suffix = cn[len(base):] if cn.startswith(base) else cn.split("_", 1)[-1]
        parts_ = suffix.strip("_").split("_")
        if len(parts_) != 2:
            continue
        u, s = int(parts_[0]), int(parts_[1])
        if u not in (0, unit) or s == 2:
            continue
        for pin in sexpr.find_all(child, "pin"):
            at = sexpr.find(pin, "at")
            num = sexpr.uq(sexpr.find(pin, "number")[1])
            out.append((num, float(at[1]), float(at[2]), float(at[3])))
    return out


def n_units(libid):
    sym = SYMS[libid]
    base = sexpr.sym_name(sym).split(":", 1)[-1]
    units = set()
    for child in sexpr.find_all(sym, "symbol"):
        cn = sexpr.sym_name(child)
        if not cn.startswith(base):
            continue
        parts_ = cn[len(base):].strip("_").split("_")
        if len(parts_) == 2 and parts_[0].isdigit():
            u = int(parts_[0])
            if u > 0:
                units.add(u)
    return max(units) if units else 1


def xform(px, py, X, Y, rot):
    """Symbol-local (y-up) -> sheet (y-down) for rotation rot."""
    if rot == 0:
        return X + px, Y - py
    if rot == 90:
        return X - py, Y - px
    if rot == 180:
        return X - px, Y + py
    if rot == 270:
        return X + py, Y + px
    raise ValueError(rot)


def pin_dir(angle, rot):
    """Outward direction of a pin on the sheet, as 0/90/180/270 (sheet deg,
    0=right, 90=up, 180=left, 270=down)."""
    # local outward direction is angle+180 in y-up space
    out_up = (angle + 180.0) % 360
    # apply rotation (still y-up sense), then convert to sheet sense (same
    # names: right/up/left/down), because we only report cardinal names.
    total = (out_up + rot) % 360
    return int(total)


# ---------------------------------------------------------------------------
# emitters
# ---------------------------------------------------------------------------

SCH = []   # accumulated top-level nodes


SYM_UUIDS = {}   # ref -> unit-1 instance uuid (for PCB footprint linkage)


def emit_symbol_instance(ref, libid, unit, X, Y, rot, value, footprint,
                         extra_fields=None, dnp=False, value_hide=False):
    pins = unit_pins(libid, unit)
    iu = uid()
    if unit == 1:
        SYM_UUIDS[ref] = iu
    node = ["symbol", ["lib_id", q(libid)],
            ["at", fmt(X), fmt(Y), str(rot)],
            ["unit", str(unit)],
            ["exclude_from_sim", "no"], ["in_bom", "yes"],
            ["on_board", "yes"], ["dnp", "yes" if dnp else "no"],
            ["uuid", q(iu)]]
    ys = [xform(px, py, X, Y, rot)[1] for _, px, py, _ in pins] or [Y]
    topy, boty = min(ys) - 2.54, max(ys) + 2.54
    node.append(["property", q("Reference"), q(ref),
                 ["at", fmt(X), fmt(topy - 1.27), "0"], _ef()])
    node.append(["property", q("Value"), q(value),
                 ["at", fmt(X), fmt(boty + 1.27), "0"], _ef(hide=value_hide)])
    node.append(["property", q("Footprint"), q(footprint),
                 ["at", fmt(X), fmt(boty + 3.81), "0"], _ef(hide=True)])
    node.append(["property", q("Datasheet"), q(""),
                 ["at", fmt(X), fmt(boty + 6.35), "0"], _ef(hide=True)])
    for fname, fval in (extra_fields or {}).items():
        node.append(["property", q(fname), q(fval),
                     ["at", fmt(X), fmt(boty + 8.89), "0"], _ef(hide=True)])
    for num, _, _, _ in sorted(pins, key=lambda p: p[0]):
        node.append(["pin", q(num), ["uuid", q(uid())]])
    node.append(["instances",
                 ["project", q(PROJECT),
                  ["path", q("/" + ROOT_UUID),
                   ["reference", q(ref)], ["unit", str(unit)]]]])
    SCH.append(node)
    return pins


def _ef(hide=False, justify=None):
    e = ["effects", ["font", ["size", "1.27", "1.27"]]]
    if justify:
        e.append(["justify", justify])
    if hide:
        e.append(["hide", "yes"])
    return e


def emit_glabel(net, x, y, direction):
    rot = {0: "0", 90: "90", 180: "180", 270: "270"}[direction]
    justify = "left" if direction in (0, 90) else "right"
    SCH.append(["global_label", q(net), ["shape", "passive"],
                ["at", fmt(x), fmt(y), rot],
                _ef(justify=justify),
                ["uuid", q(uid())],
                ["property", q("Intersheetrefs"), q("${INTERSHEET_REFS}"),
                 ["at", fmt(x), fmt(y), "0"], _ef(hide=True)]])


def emit_wire(x1, y1, x2, y2):
    SCH.append(["wire", ["pts", ["xy", fmt(x1), fmt(y1)],
                         ["xy", fmt(x2), fmt(y2)]],
                ["stroke", ["width", "0"], ["type", "default"]],
                ["uuid", q(uid())]])


def emit_nc(x, y):
    SCH.append(["no_connect", ["at", fmt(x), fmt(y)], ["uuid", q(uid())]])


def emit_junction(x, y):
    SCH.append(["junction", ["at", fmt(x), fmt(y)], ["diameter", "0"],
                ["color", "0", "0", "0", "0"], ["uuid", q(uid())]])


def emit_text(s, x, y, size=2.0, bold=False):
    e = ["effects", ["font", ["size", fmt(size), fmt(size)]]]
    if bold:
        e[1].append(["bold", "yes"])
    e.append(["justify", "left", "bottom"])
    SCH.append(["text", q(s), ["exclude_from_sim", "no"],
                ["at", fmt(x), fmt(y), "0"], e, ["uuid", q(uid())]])


_power_seq = 0


def emit_power(net, x, y, direction):
    """Attach a power symbol directly at (x,y), rotated so its body extends
    along the pin's outward direction (no stub wires: they can collide)."""
    global _power_seq
    _power_seq += 1
    libid = POWER_NETS[net]
    down = net == "GND"
    if down:
        rot = {270: 0, 0: 90, 180: 270, 90: 180}[direction]
    else:
        rot = {90: 0, 0: 270, 180: 90, 270: 180}[direction]
    px, py = x, y
    ref = f"#PWR{_power_seq:03d}"
    vdx = {0: 6.35, 180: -6.35}.get(direction, 0)
    vdy = {270: 6.35, 90: -6.35}.get(direction, 0)
    node = ["symbol", ["lib_id", q(libid)],
            ["at", fmt(px), fmt(py), str(rot)],
            ["unit", "1"],
            ["exclude_from_sim", "no"], ["in_bom", "yes"],
            ["on_board", "yes"], ["dnp", "no"],
            ["uuid", q(uid())],
            ["property", q("Reference"), q(ref),
             ["at", fmt(px), fmt(py + 5.08), "0"], _ef(hide=True)],
            ["property", q("Value"), q(net),
             ["at", fmt(px + vdx), fmt(py + vdy), "0"],
             _ef()],
            ["property", q("Footprint"), q(""),
             ["at", fmt(px), fmt(py), "0"], _ef(hide=True)],
            ["property", q("Datasheet"), q(""),
             ["at", fmt(px), fmt(py), "0"], _ef(hide=True)],
            ["pin", q("1"), ["uuid", q(uid())]],
            ["instances",
             ["project", q(PROJECT),
              ["path", q("/" + ROOT_UUID),
               ["reference", q(ref)], ["unit", "1"]]]]]
    SCH.append(node)


def emit_pwr_flag(net, x, y):
    global _power_seq
    _power_seq += 1
    x, y = snap(x), snap(y)
    ref = f"#FLG{_power_seq:03d}"
    node = ["symbol", ["lib_id", q("power:PWR_FLAG")],
            ["at", fmt(x), fmt(y), "0"],
            ["unit", "1"],
            ["exclude_from_sim", "no"], ["in_bom", "yes"],
            ["on_board", "yes"], ["dnp", "no"],
            ["uuid", q(uid())],
            ["property", q("Reference"), q(ref),
             ["at", fmt(x), fmt(y - 5.08), "0"], _ef(hide=True)],
            ["property", q("Value"), q("PWR_FLAG"),
             ["at", fmt(x), fmt(y - 3.81), "0"], _ef()],
            ["property", q("Footprint"), q(""),
             ["at", fmt(x), fmt(y), "0"], _ef(hide=True)],
            ["property", q("Datasheet"), q(""),
             ["at", fmt(x), fmt(y), "0"], _ef(hide=True)],
            ["pin", q("1"), ["uuid", q(uid())]],
            ["instances",
             ["project", q(PROJECT),
              ["path", q("/" + ROOT_UUID),
               ["reference", q(ref)], ["unit", "1"]]]]]
    SCH.append(node)
    # tie the flag to the net with a label at the same point
    emit_glabel(net, x, y, 270)


# ---------------------------------------------------------------------------
# placement helper: place a unit and wire up all its pins from the netlist
# ---------------------------------------------------------------------------

def place(ref, unit, X, Y, rot=0, label_len=0.0, skip_pins=(), power_as_label=()):
    """Place symbol unit; every pin gets its net decoration.

    label_len: optional straight wire stub before the global label.
    """
    c = BYREF[ref]
    X, Y = snap(X), snap(Y)
    pins = emit_symbol_instance(
        ref, c["symbol"], unit, X, Y, rot, c["value"], c["footprint"],
        extra_fields=c.get("fields"), dnp=c.get("dnp", False))
    seen = set()
    for num, px, py, ang in pins:
        if num in seen:
            continue          # stacked duplicate pin
        seen.add(num)
        if num in skip_pins:
            continue
        gx, gy = xform(px, py, X, Y, rot)
        d = pin_dir(ang, rot)
        if num not in c["pins"]:
            raise KeyError(f"{ref} pin {num} has no net entry")
        net = c["pins"][num]
        if net is None:
            emit_nc(gx, gy)
            continue
        if net in POWER_NETS and net not in power_as_label:
            emit_power(net, gx, gy, d)
            continue
        lx, ly = gx, gy
        if label_len:
            dx = {0: label_len, 180: -label_len}.get(d, 0)
            dy = {90: -label_len, 270: label_len}.get(d, 0)
            emit_wire(gx, gy, gx + dx, gy + dy)
            lx, ly = gx + dx, gy + dy
        emit_glabel(net, lx, ly, d)
    return X, Y


# ---------------------------------------------------------------------------
# sheet layout
# ---------------------------------------------------------------------------

def build():
    # ---- headline notes ----
    emit_text("PICO506 — ST-506 / MFM / RLL HARD DRIVE EMULATOR", 20, 20, 3.0, bold=True)
    emit_text("Firmware: github.com/kuba2k2/pico506 (RP2040).  Bus signals are active-low 5V TTL;"
              " Pico-side signals are active-high 3V3 behind 74LS05 open-collector inverters.", 20, 26, 1.5)
    emit_text("Outputs are 74LS38 open-collector NAND gated by SELECTED, so a deselected drive"
              " releases the daisy-chained control bus, as ST-506 requires.", 20, 30, 1.5)

    # ================= left column: connectors =================
    # J1 control connector
    x, y = place("J1", 1, 50, 90, label_len=2.54,
                 skip_pins={str(n) for n in range(1, 34, 2)})
    tipx = x + 16.51 + 3.81
    ytop = y - 16 * 2.54 / 2
    for i in range(17):
        emit_wire(tipx, ytop + i * 2.54, tipx, ytop + (i + 1) * 2.54)
    emit_power("GND", tipx, ytop + 17 * 2.54, 270)

    # J2 data connector
    x, y = place("J2", 1, 50, 190, label_len=2.54,
                 skip_pins={"2", "4", "6", "8", "11", "12", "15", "16", "19", "20"})
    tipx = x + 16.51 + 3.81
    ytop = y - 9 * 2.54 / 2
    for i in range(10):
        emit_wire(tipx, ytop + i * 2.54, tipx, ytop + (i + 1) * 2.54)
    emit_power("GND", tipx, ytop + 10 * 2.54, 270)

    # J3 power in + flags + bulk caps
    place("J3", 1, 50, 250)
    emit_pwr_flag("+5V", 80, 243.84)
    emit_pwr_flag("+12V", 100, 243.84)
    place("TP1", 1, 110, 250)
    place("C1", 1, 125, 252)
    place("D1", 1, 145, 246, rot=90)
    emit_pwr_flag("VSYS", 155, 243.84)
    place("C2", 1, 165, 252)

    # ================= column 2: terminator + input inverters =================
    emit_text("Bus termination — 220/330 split per ST-506 spec; SIPs socketed,"
              " remove on all but the last drive", 105, 55, 1.5)
    place("RN1", 1, 120, 70, rot=0, label_len=2.54)
    place("RN2", 1, 150, 70, rot=0, label_len=2.54)
    place("R21", 1, 175, 70)
    place("R22", 1, 185, 70)
    place("U2", 1, 130, 100, label_len=2.54)
    place("U2", 2, 130, 115, label_len=2.54)
    place("U2", 3, 130, 130, label_len=2.54)
    place("U2", 4, 130, 145, label_len=2.54)
    place("U2", 5, 130, 160, label_len=2.54)
    place("U2", 6, 130, 175, label_len=2.54)
    place("U2", 7, 130, 195)
    place("U3", 1, 175, 100, label_len=2.54)
    place("U3", 2, 175, 115, label_len=2.54)
    place("U3", 3, 175, 130, label_len=2.54)
    place("U3", 4, 175, 145, label_len=2.54)
    place("U3", 5, 175, 160, label_len=2.54)
    place("U3", 6, 175, 175, label_len=2.54)
    place("U3", 7, 175, 195)

    # ================= column 3: output drivers + differential =================
    place("U4", 1, 225, 100, label_len=2.54)
    place("U4", 2, 225, 115, label_len=2.54)
    place("U4", 3, 225, 130, label_len=2.54)
    place("U4", 4, 225, 145, label_len=2.54)
    place("U4", 5, 225, 165)
    place("U5", 1, 265, 100, label_len=2.54)
    place("U5", 2, 265, 115, label_len=2.54)
    place("U5", 3, 265, 130, label_len=2.54)
    place("U5", 4, 265, 145, label_len=2.54)
    place("U5", 5, 265, 165)
    place("U6", 1, 225, 210, label_len=2.54)
    place("U7", 1, 265, 195, label_len=2.54)
    place("U7", 2, 265, 215, label_len=2.54)
    place("U7", 3, 265, 230, label_len=2.54)
    place("U7", 4, 265, 245, label_len=2.54)
    place("R12", 1, 296, 195)

    # ================= column 4: Pico + pull-ups =================
    place("U1", 1, 330, 130, label_len=2.54)
    rx = 310
    for i, r in enumerate(["R1", "R2", "R3", "R4", "R5", "R6", "R7", "R8", "R9"]):
        place(r, 1, rx + i * 10, 220)
    for i, r in enumerate(["R17", "R18", "R19", "R20"]):
        place(r, 1, rx + i * 10, 245)

    # ================= right column: SD, indicators, misc =================
    place("SD1", 1, 385, 60, label_len=2.54)
    place("J4", 1, 385, 100, label_len=2.54)
    place("J5", 1, 385, 120, label_len=2.54)
    place("J6", 1, 385, 135, label_len=2.54)
    place("JP1", 1, 385, 150, label_len=2.54)
    place("SW1", 1, 385, 165, label_len=2.54)
    place("BZ1", 1, 385, 180, label_len=2.54)
    place("R11", 1, 360, 180, rot=90)
    place("Q1", 1, 385, 205, label_len=2.54)
    place("R13", 1, 362, 205, rot=90)
    place("R14", 1, 340, 240)
    place("D2", 1, 352, 252, rot=0)
    place("R15", 1, 370, 240)
    place("J7", 1, 382, 252, label_len=2.54)
    place("R16", 1, 400, 240)
    place("D3", 1, 410, 252, rot=0)
    place("R10", 1, 240, 165)

    # decoupling
    emit_text("Decoupling — one 100n per DIP", 190, 270, 1.5)
    for i, ref in enumerate(["C3", "C4", "C5", "C6", "C7", "C8", "C9"]):
        place(ref, 1, 195 + i * 12, 280)
    place("C10", 1, 279, 280)

    # mechanical
    for i, ref in enumerate(["H1", "H2", "H3", "H4"]):
        place(ref, 1, 30 + i * 12, 280)
    place("FG1", 1, 80, 280)

    # ---- assemble document ----
    doc = ["kicad_sch", ["version", "20231120"], ["generator", q("pico506_gen")],
           ["uuid", q(ROOT_UUID)], ["paper", q("A3")],
           ["title_block",
            ["title", q("Pico506 — ST-506/MFM/RLL hard drive emulator")],
            ["date", q("2026-07-27")], ["rev", q("1.0")],
            ["comment", "1", q("Drop-in replacement PCB for classic 5.25-inch MFM drives")],
            ["comment", "2", q("Board: github.com/hmerrett/pico506-pcb")],
            ["comment", "3", q("Firmware: github.com/kuba2k2/pico506 "
                               "(c) 2025 Kuba Szczodrzynski")],
            ["comment", "4", q("Licensed GPL-3.0-or-later. Design files: "
                               "see Board above.")]]]
    lib = ["lib_symbols"]
    for libid in sorted(set(BYREF[c]["symbol"] for c in BYREF) |
                        set(POWER_NETS.values()) | {"power:PWR_FLAG"}):
        lib.append(sexpr._deep_copy(SYMS[libid]))
    doc.append(lib)
    doc.extend(SCH)
    doc.append(["sheet_instances", ["path", q("/"), ["page", q("1")]]])
    return doc


if __name__ == "__main__":
    import json
    import sys
    out = sys.argv[1] if len(sys.argv) > 1 else "../pico506.kicad_sch"
    doc = build()
    with open(out, "w") as f:
        f.write(sexpr.dumps(doc) + "\n")
    with open("sch_uuids.json", "w") as f:
        json.dump(SYM_UUIDS, f, indent=1)
    print(f"wrote {out}: {len(SCH)} top-level items")
