#!/usr/bin/env python3
"""Report courtyard boxes and how deeply overlapping pairs interpenetrate, so
placement nudges can be sized instead of guessed.

  /Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/\
Versions/Current/bin/python3 place_check.py ../pico506.kicad_pcb
"""

import sys

import pcbnew

IU = 1e6
OX = OY = 30.0          # layout.ORIGIN_*


def mm(v):
    return v / IU


def main():
    board = pcbnew.LoadBoard(sys.argv[1])
    boxes = {}
    for fp in board.GetFootprints():
        for layer in (pcbnew.F_CrtYd, pcbnew.B_CrtYd):
            items = [g for g in fp.GraphicalItems() if g.GetLayer() == layer]
            if not items:
                continue
            bb = items[0].GetBoundingBox()
            for g in items[1:]:
                bb.Merge(g.GetBoundingBox())
            boxes.setdefault(fp.GetReference(), []).append(
                (board.GetLayerName(layer),
                 mm(bb.GetLeft()) - OX, mm(bb.GetTop()) - OY,
                 mm(bb.GetRight()) - OX, mm(bb.GetBottom()) - OY))
    refs = sorted(boxes)
    print(f"{len(refs)} footprints with a courtyard\n")
    hits = []
    for i, a in enumerate(refs):
        for b in refs[i + 1:]:
            for la, ax0, ay0, ax1, ay1 in boxes[a]:
                for lb, bx0, by0, bx1, by1 in boxes[b]:
                    if la != lb:
                        continue
                    ox = min(ax1, bx1) - max(ax0, bx0)
                    oy = min(ay1, by1) - max(ay0, by0)
                    if ox > 0 and oy > 0:
                        hits.append((min(ox, oy), a, b, la, ox, oy))
    for depth, a, b, la, ox, oy in sorted(hits, reverse=True):
        print(f"{a:>4s} <-> {b:<4s} {la:8s} overlap x {ox:6.2f}  y {oy:6.2f}"
              f"   -> separate by {depth:.2f} mm")
    print()
    for r in refs:
        for la, x0, y0, x1, y1 in boxes[r]:
            print(f"{r:>4s} {la:8s} ({x0:7.2f},{y0:7.2f})-({x1:7.2f},{y1:7.2f})"
                  f"  {x1 - x0:5.2f} x {y1 - y0:5.2f}")


if __name__ == "__main__":
    main()
