"""Symbol sources for the pico506 schematic.

Provides flattened stock symbols (renamed to "Lib:Name" ids for embedding in
the schematic's lib_symbols) and programmatically-built custom symbols for
the ST-506 connectors and the SD socket.
"""

import sexpr
from sexpr import q

KICAD_SYMBOLS = "/Applications/KiCad/KiCad.app/Contents/SharedSupport/symbols"

# stock symbols used, keyed by "Lib:Name"
STOCK = [
    "74xx:74LS05",
    "74xx:74LS38",
    "Interface:AM26LS31CN",
    "Interface_LineDriver:MC3486N",
    "MCU_Module:RaspberryPi_Pico",
    "Device:R_Network08",
    "Device:R",
    "Device:C",
    "Device:C_Polarized",
    "Device:LED",
    "Device:D_Schottky",
    "Device:Buzzer",
    "Transistor_BJT:2N3904",
    "Connector_Generic:Conn_02x04_Odd_Even",
    "Connector_Generic:Conn_01x03",
    "Connector_Generic:Conn_01x02",
    "Connector:TestPoint",
    "Switch:SW_Push",
    "Mechanical:MountingHole",
    "Mechanical:MountingHole_Pad",
    "power:GND",
    "power:+5V",
    "power:+3V3",
    "power:+12V",
    "power:PWR_FLAG",
]


def load_stock():
    """Return {libid: symbol_node} with parent renamed to the full libid and
    child unit names left bare (KiCad's embedded-symbol convention)."""
    out = {}
    for libid in STOCK:
        lib, name = libid.split(":")
        node = sexpr.load_symbol(f"{KICAD_SYMBOLS}/{lib}.kicad_sym", name)
        # Symbols we modify get re-homed into the project library so the
        # embedded copies never mismatch the global libraries.
        if name == "MC3486N":
            libid = f"pico506-lib:{name}"
            node = _prefix_parent_only(node, libid)
            _dedupe_pins(node)
        elif name == "RaspberryPi_Pico":
            libid = f"pico506-lib:{name}"
            node = _prefix_parent_only(node, libid)
            _agnd_passive(node)
        else:
            node = _prefix_parent_only(node, libid)
        out[libid] = node
    return out


def _dedupe_pins(sym):
    """Drop repeated pin numbers (shared power/enable pins drawn on every
    unit) so ERC's duplicate-pin check passes; keep the first occurrence."""
    seen = set()
    for child in sexpr.find_all(sym, "symbol"):
        keep = []
        for item in child:
            if sexpr.tag(item) == "pin":
                num = sexpr.uq(sexpr.find(item, "number")[1])
                if num in seen:
                    continue
                seen.add(num)
            keep.append(item)
        child[:] = keep


def _agnd_passive(sym):
    """The stock Pico symbol makes both GND(3) and AGND(33) power outputs,
    which trips ERC's power-out-to-power-out check when tied together."""
    for child in sexpr.find_all(sym, "symbol"):
        for pin in sexpr.find_all(child, "pin"):
            num = sexpr.uq(sexpr.find(pin, "number")[1])
            if num == "33" and pin[1] == "power_out":
                pin[1] = "passive"


def _prefix_parent_only(node, libid):
    n = sexpr._deep_copy(node)
    n[1] = q(libid)
    return n


# --------------------------------------------------------------------------
# custom symbol construction
# --------------------------------------------------------------------------

def _effects(size=1.27, hide=False, justify=None):
    e = ["effects", ["font", ["size", f"{size}", f"{size}"]]]
    if justify:
        e.append(["justify", justify])
    if hide:
        e.append(["hide", "yes"])
    return e


def _prop(name, val, y, hide=False):
    return ["property", q(name), q(val), ["at", "0", f"{y}", "0"],
            _effects(hide=hide)]


def _pin(num, name, x, y, angle, length=3.81, etype="passive"):
    return ["pin", etype, "line",
            ["at", f"{x}", f"{y}", f"{angle}"],
            ["length", f"{length}"],
            ["name", q(name), _effects()],
            ["number", q(str(num)), _effects()]]


def connector_symbol(name, refprefix, left, right, width=27.94,
                     value_offset=None):
    """Build a box connector symbol.

    left/right: [(pin_number, pin_name), ...] top to bottom.  Connection
    points sit `length` outside the box on a 2.54 grid.
    """
    rows = max(len(left), len(right))
    pitch = 2.54
    top = (rows - 1) * pitch / 2.0
    top = round(top / 1.27) * 1.27
    half_w = width / 2.0
    length = 3.81
    body_top = top + pitch
    body_bot = -(top + pitch)

    unit1 = ["symbol", q(f"{name}_1_1")]
    unit0 = ["symbol", q(f"{name}_0_1"),
             ["rectangle",
              ["start", f"{-half_w}", f"{body_top}"],
              ["end", f"{half_w}", f"{body_bot}"],
              ["stroke", ["width", "0.254"], ["type", "default"]],
              ["fill", ["type", "background"]]]]

    for i, (num, pname) in enumerate(left):
        y = top - i * pitch
        unit1.append(_pin(num, pname, -half_w - length, y, 0))
    for i, (num, pname) in enumerate(right):
        y = top - i * pitch
        unit1.append(_pin(num, pname, half_w + length, y, 180))

    return ["symbol", q(name),
            ["pin_names", ["offset", "1.016"]],
            ["exclude_from_sim", "no"], ["in_bom", "yes"], ["on_board", "yes"],
            _prop("Reference", refprefix, body_top + 2.54),
            _prop("Value", name, body_bot - 2.54),
            _prop("Footprint", "", body_bot - 5.08, hide=True),
            _prop("Datasheet", "", body_bot - 7.62, hide=True),
            _prop("Description", "", body_bot - 10.16, hide=True),
            unit0, unit1]


def custom_symbols(libname="pico506-lib"):
    import netlist

    j1_left = [(n, netlist.J1_NAMES[n]) for n in range(2, 35, 2)]
    j1_right = [(n, "GND") for n in range(1, 34, 2)]
    j1 = connector_symbol("ST506_J1_Control", "J", j1_left, j1_right,
                          width=33.02)

    j2_sig = [1, 3, 5, 7, 9, 10, 13, 14, 17, 18]
    j2_gnd = [2, 4, 6, 8, 11, 12, 15, 16, 19, 20]
    j2_left = [(n, netlist.J2_NAMES.get(n, "RSVD")) for n in j2_sig]
    j2_right = [(n, "GND") for n in j2_gnd]
    j2 = connector_symbol("ST506_J2_Data", "J", j2_left, j2_right,
                          width=33.02)

    j3 = connector_symbol("ST506_J3_Power", "J",
                          [(1, "+12V"), (2, "+12V_RET"),
                           (3, "+5V_RET"), (4, "+5V")], [],
                          width=25.4)

    sd = connector_symbol("SD_FullSize", "SD",
                          [(1, "DAT3/CS"), (2, "CMD/DI"), (3, "VSS"),
                           (4, "VDD"), (5, "CLK"), (6, "VSS"),
                           (7, "DAT0/DO"), (8, "DAT1"), (9, "DAT2")],
                          [("SH", "SHELL"), ("SW", "CD_SW"),
                           ("WP", "WP_SW"), ("CP", "COM")],
                          width=25.4)

    return {f"{libname}:{sexpr.sym_name(s)}": _prefix_parent_only(s, f"{libname}:{sexpr.sym_name(s)}")
            for s in [j1, j2, j3, sd]}


def all_symbols():
    syms = load_stock()
    syms.update(custom_symbols())
    return syms


def write_symbol_lib(path, libname="pico506-lib"):
    """Write the custom + re-homed symbols as a standalone .kicad_sym lib."""
    lib = ["kicad_symbol_lib", ["version", "20231120"],
           ["generator", q("pico506_gen")]]
    entries = dict(custom_symbols(libname))
    for libid, node in load_stock().items():
        if libid.startswith(f"{libname}:"):
            entries[libid] = node
    for libid, node in entries.items():
        bare = sexpr._deep_copy(node)
        bare[1] = q(libid.split(":", 1)[1])
        lib.append(bare)
    with open(path, "w") as f:
        f.write(sexpr.dumps(lib) + "\n")


if __name__ == "__main__":
    syms = all_symbols()
    print(f"{len(syms)} symbols loaded/built")
    for k in syms:
        print(" ", k)
