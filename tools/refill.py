#!/usr/bin/env python3
"""Open the generated board in pcbnew, fill zones, save.  Doubles as a
format validator: if pcbnew can load and re-save it, KiCad is happy."""

import sys

import pcbnew

path = sys.argv[1]
board = pcbnew.LoadBoard(path)
filler = pcbnew.ZONE_FILLER(board)
filler.Fill(board.Zones())
pcbnew.SaveBoard(path, board)
print("filled + saved:", path)
print("footprints:", len(board.GetFootprints()),
      " nets:", board.GetNetCount(),
      " tracks:", len(board.GetTracks()))
