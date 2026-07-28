#!/usr/bin/env python3
"""Dump pin tables of the stock symbols used by the pico506 board."""

import sexpr


def _k(n):
    try:
        return (0, int(n))
    except ValueError:
        return (1, n)


KICAD = "/Applications/KiCad/KiCad.app/Contents/SharedSupport/symbols"

WANTED = [
    ("74xx", "74LS05"),
    ("74xx", "74LS38"),
    ("Interface", "AM26LS31CN"),
    ("Interface_LineDriver", "MC3486N"),
    ("MCU_Module", "RaspberryPi_Pico"),
    ("Connector", "SD_Card_Device"),
    ("Connector", "SD_Card_Receptacle"),
    ("Device", "R_Network08"),
    ("Device", "Buzzer"),
    ("Transistor_BJT", "2N3904"),
]

for lib, name in WANTED:
    try:
        sym = sexpr.load_symbol(f"{KICAD}/{lib}.kicad_sym", name)
    except KeyError as e:
        print(f"== {lib}:{name}  MISSING ({e})")
        continue
    print(f"== {lib}:{name}")
    rows = sexpr.pin_table(sym)
    rows.sort(key=lambda r: (r[0], _k(r[1])))
    for suffix, num, pname, ptype in rows:
        print(f"   unit{suffix:<8} pin {num:>3}  {pname:<12} {ptype}")


