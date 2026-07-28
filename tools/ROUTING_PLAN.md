# Pico506 PCB — routing plan (handoff notes)

## STATUS after task 11 — CARD-EDGE RELIEF CUT-OUTS

The tabs stood only TAB_PROTRUDE (5 mm) proud of a full-width rear edge, but
the fingers are FINGER_LEN (11.43 mm) long — so a mating socket's shell hit the
board edge with two thirds of the gold unengaged. The board is now cut away
beside each tab, inboard to `L.tab_relief_y()` = 67.57 (level with the finger
tops), leaving each tab a free-standing tongue the full 11.43 mm long. Envelope
unchanged; no pad moved. `TAB_RELIEF_W` (6.0) is the knob.

Consequences handled:

- **J1's GND rail had to change.** Every odd J1 finger is GND and the rail at
  y67.95 used to reach x29.6/x78.4 to meet the pour outside the tab keepout —
  both of which are now cut away. Each half now jogs north to y = ry-0.6 first,
  onto the full-width board, and runs out to the pour from there.
- **The reference placer needed to learn about cut-outs.** It only bounded refs
  by the board rectangle, so it put J3's ref inside the new notch. `CUTOUTS`
  (relief notches + the inboard part of each key slot) is now a hard no.
- J1's **west** relief is clamped to 5.34 mm, not 6.0: the J3 power housing's
  east face is at x25.62 and `L.tab_relief_x()` keeps `J3_RELIEF_GAP` off it.
  If a real socket needs more, the obstruction is the power connector body and
  J3 has to move east, off the measured ST-225 position.
- J2's **east** relief is 2.90 mm because the board ends at x138 — the whole
  south-east corner is simply removed, so nothing is east of that tab at all.

DRC 0, ERC 0, GND still one connected plane after the change.

## STATUS after task 10 — DRC CLEAN, ARTEFACTS EXPORTED

ERC 0, DRC 0 at `--severity-all`. GND is one connected plane (63 fill
islands, no orphans). Board not yet fabricated.

What task 10 actually changed — see [../README.md](../README.md) for the
user-facing write-up and the "things that will bite you" list:

- **6 unconnected items were real defects, not cosmetics.** U4.7, C5.2, C3.2,
  U3.13, SD1.3/SD1.6 and three Pico ground pins were sitting in pour fragments
  that reached nothing. `tools/stitch.py` (new) finds these: it unions every
  GND island with the copper touching it and reports orphans plus a fix.
- Rescues that cannot be fitted after routing now route **inside** the maze
  router's search as first-class nets (`GND_STUBS` in gen_pcb.py) — the
  inter-DIP corridors seal once signals fill them and several have no B.Cu pour
  underneath to via to. A pass only counts if signals *and* ground links fit.
- `router.CLR` 0.25 -> 0.24. At 0.25 the U3/U4 corridor is one track short of
  holding both the signals and C5's rescue.
- Custom pad shapes are now measured from their primitives, not `(size)`; the
  Pico's castellated pads reach 1.13 mm, not 0.8, and the router was routing
  into them.
- Reference designators are auto-placed (`place_references()`), which is what
  cleared ~100 silk violations. Board texts moved off copper; the B.SilkS
  branding now sits between the Pico's two pin rows.
- Real body collisions fixed by placement: Q1 vs D2/D3 overlapped by ~0.85 mm.
  Also nudged C2/C3/C9/C10/D1/BZ1/R11/R21/R22/C7. `tools/place_check.py` (new)
  sizes these instead of guessing.
- J3's silk outline no longer runs off the board edge or across its own pads;
  the SD socket's courtyard was pulled in to the body.
- `lib_footprint_mismatch` set to `ignore` (the board is regenerated from the
  libraries every build, so library drift is structurally impossible here).
- `tools/export.sh` (new) produces renders, schematic PDF, layer PDFs, gerbers,
  drill, BOM and placement into `hardware/doc/`.

**Re-run `tools/stitch.py` after any routing or placement change.** The
coordinate-based `GND_STITCH_VIAS` go stale as soon as the router lands
differently, and a stale via can end up on a signal track.

## STATUS after task 9 — BOARD FULLY ROUTED

Every net is connected: zero shorts, crossings, clearance or hole errors.
Remaining DRC (task 10): 6 unconnected items that are all GND plane-split
pairs (pour fragments each carrying ground but no copper bridge between
them — needs a few stitch vias placed after visual inspection of the fills),
60 silk_overlap + 42 silk_over_copper + 1 silk_edge (text/ref cleanup),
15 courtyards_overlap (mostly ref-text/courtyard cosmetics to review),
1 lib_footprint_mismatch (Pico footprint intentionally differs: harmless).

Task 9 was done with tools/router.py — a net-aware two-layer grid maze
router (0.3175 mm grid, 0.3 mm tracks, 0.6/0.3 vias) run inside
gen_pcb.routes_gpio_auto() with retry/rip-up and randomized restarts;
chronically congested nets got verified hand routes in routes_gpio_hand()
(HS0/HS1/HS2 GPIO drops+links, SELECTED tree incl. R13 leg at y25.4 under
the module, WR_DATA, SD corner joins). The select-monitor inverter moved
from U3 gate 3 (pins 5/6, now spare/NC) to U5's spare NAND gate (pins
12+13 tied = DS_SEL_N in, pin 11 = SELECTED out) — netlist + schematic
updated and ERC re-verified. ~14 GND relief stubs+vias feed THT ground
pads the pours can no longer reach through the routing maze.

check.sh regenerates everything (sch UUIDs assumed current), refills
zones, re-stamps the .kicad_pro (pcbnew's save clobbers it — note the
netclass needs its "priority" field or KiCad ignores the 0.18 clearance)
and runs full-severity DRC into hardware/drc.txt.

## STATUS after tasks 6+7 (power + termination bus routed)

DRC: ZERO copper errors. Remaining: 70 unconnected (tasks 8/9 nets), plus
silk/courtyard warnings (task 10). Regen + check: `tools/check.sh`.

Key learnings that supersede sections below:
- Layer discipline that WORKS: ALL band horizontals on F.Cu in 0.75 mm slots
  y = 57.5, 58.25, 59.0, 59.75, 60.5, 61.25, 62.0; ALL verticals on B.Cu.
  B verticals never cross F horizontals — the only real constraints are
  via spacing: via(0.6/0.3) to parallel track ≥0.75 center-lateral, via-via
  ≥0.85, via-to-DIP-hole ≥~1.0 radial. Slot assignment is nearly free.
- J1 escapes: B verticals from finger pads (y68.5) north across the RN row;
  RN1@(27.43,64)/RN2@(52.83,64) pads sit on the half-grid so every escape
  passes with 1.27 mm to each side. Escape x = finger x (2.54 grid at
  33.78 + 2.54k).
- Slot usage (net@slot): WG/DS1@57.5, STEP/DS2@58.25, DIR@59.0, HS0/DS3@59.75,
  HS1/DS4@60.5, HS2@61.25, HS3@62.0. DS vias at x 64.26..71.88 (DS1's at
  64.9); J4 at (88.12,61) rot 270 => columns DS4..DS1 west->east at
  80.5/83.04/85.58/88.12 (odd row y61, DS_SEL row y63.54).
- RN2 line pins were REMAPPED in netlist.py (2:WG 3:STEP 4:HS3 5:DIR 6:HS0
  7:HS1 8:HS2) so HS3's U3.9 entry vertical (x60.0) shares the RN2.4 stub
  column same-net. RN1 stays in natural order.
- U3 gates swapped in netlist: 3/4 = select-monitor (WG_GATED), 9/8 = HS3.
- Occupied B verticals in the band (do not collide in tasks 8/9):
  escapes at all 17 finger x's up to their slot; SIP stubs at RN1
  29.97..45.21 and RN2 55.37..70.61 (slot..64); entry verts x 36.6, 39.7,
  40.6, 42.15(+jog to 42.67), 42.95, 47.0, 60.0(+jog to 60.45); DS_SEL B at
  x49.6 (46.08..58.0), jog y58.0 x49.6..53.2, x51.56 (58..65.5),
  x53.2 (56.55..58).
- DS_SEL_N is an all-F tree: main y65.5 from x51.56 to (80.5,63.54) bus
  through J4 evens to 88.12; east legs y63.9 / y60.3 / lane y49.89 to
  R21.2 (91,51.84), R22.1 (94.5,62), U6.12; vias at (51.56,65.5),
  (53.2,56.55).
- FG1 moved to (93.5, 68).

## STATUS after task 8 — outputs + data pairs routed, ZERO copper errors

Remaining 56 unconnected = task 9 nets only (GPIO, pull-up pin2s, SD, UART,
RUN, buzzer, LED chain, SERVO_GATE header, +2 GND pads to check).

New occupied resources (add to the task-7 list):
- B lanes: y42.27 (SKC, x41.4-73), y44.81 (TRK0, 43.94-70.3, jogs to y43.98
  around x47-49.6 and x60-62.6), y47.35 (INDEX, 56.64-62.65), y49.89 (RD_M,
  99.6-108.6 and 127.0-130.34), y52.43 (DRV, 78.6-89.5), y60.3 (WR_P,
  122.05-124.6), y64.0+65.9 (DRV, 89.5-110.02), y65.2 (WR_M jog), y11.9
  (WF_IN, 69.29-88.6); B verts x69.29(4.6-11.9), x88.6(11.9-22),
  x90(22-26.2), x70.3, x73.0, x62.65, x62.75(53.7-57.5), x75.5(46.08-62.75),
  x78.6, x89.5, x97.7, x99.6(46.08-49.89), x122.05(42.27-60.3),
  x124.6(60.3-62), x126(44.81-51.84), x127.4(51.84-65.2),
  x130.34(49.89-68.5).
- F lanes: y36.3 (RD_P, 99.6-130.34), y42.27 (WR_P, 112-122.05), y44.81
  (WR_M, 113.35-126), y47.35 (WR_RX, 49.75-113.5), y49.89 (RD_M hop,
  108.6-127.0), y57.5 (READY, 59.18-62.75), y62.75 (WF, 46.48-75.5),
  y39.75 (WF_IN, 78.3-90) + F verts x49.75, x113.5, x113.35, x123.85,
  x130.34(36.3-68.5), x90(26.2-39.75).
- J2 grounds are now per-column stub+via at y66.05 (pin 2's via offset to
  x111.3); no rails. Stitch vias moved: (85,18), (103,62).
- HS1's U2.11 entry is B-vert + via pair at x42.95 with an F entry at
  y48.62 (B entry would cross the TRK0 escape).

## Task 9 leftovers/reminders
- RUN lane planned y13.4 B (WF_IN sits at y11.9; keep 0.65 apart).
- GPIO drops: jog level y28.5 F, corridors x84.6/x86.4 east of module.
- 2 GND unconnected items to inspect (likely Q1.1/D3.1 zone spokes).

## Original notes for task 8 (superseded, kept for reference)
- Outputs' J1 fingers: SKC 41.4, TK0 43.94, WF 46.48, INDEX 56.64,
  READY 59.18. Their B escapes can run north PAST the band (B verticals
  cross F slots freely) and past the DIP pad rows using the between-rows
  B lanes at y = 42.27, 44.81, 47.35, 49.89(used west of x91 by DS_SEL —
  that piece is F so B is still free), 52.43, 54.97 (rows at 41+2.54k,
  pad edge gaps 0.94 -> lane centered, 0.27 clearance). Enter U4/U5 pins
  via col-gap verticals like task 7 did.
- CONSTRAINT: WF escape (46.48) may not pass y53.7..59.75 next to HS0's
  entry vert at x47.0 (lateral 0.52). Either put WF's turn NORTH of y53.4
  (lane 52.43 or above), or dogleg WF's escape east to x48.3 above y67
  (48.3 is free below y41 only up to the C4 stub — the vertical must end
  south of y41; C4 stub occupies 48.3 x at y39.5..41).
- READY escape (59.18) cannot pass the U3 col2 pad column (58.62,
  y41..56.24) — clearance 0.04. Turn READY east/west in the band slots
  region or south of y57.04. Its target U4.5/U4.6 area is east anyway.
- U4/U5 pin nets: U4: 1 INDEX, 2 SELECTED, 3 INDEX_N(out), 4 READY,
  5 SELECTED, 6 READY_N, 9 TRK0, 10 SELECTED, 8 TRK0_N, 12 SKC,
  13 SELECTED, 11 SKC_N. U5: 1 WF_IN, 2 SELECTED, 3 WFAULT_N,
  4+5 SELECTED, 6 DRV_SELD_N (-> J2 pin 1 at x110.02, F.Cu odd side!).
- J2 write pair: 13 (+WR, F.Cu x125.26!) and 14 (-WR, B.Cu x125.26) —
  note odd pins are F, even are B, SAME column x = 110.02+2.54k for pins
  (2k+1, 2k+2). R12 at (126, 51.84..62). U7.1 (112,41) WR_DATA_P,
  U7.2 (112,43.54) WR_DATA_M, U7.3 (112,46.08) WR_RX -> U3.1 (51,41).
  Read pair: U6.2 (98,43.54) -> J2-17 (F, x130.34), U6.3 (98,46.08) ->
  J2-18 (B, x130.34).

State: schematic ERC-clean (0 violations, `--severity-all`). Board generated,
placement v3 verified by render: all 62 footprints, outline with keyed
card-edge tabs, GND zones both layers, 0 tracks routed yet.

Regenerate everything:
```
cd hardware/tools
python3 gen_sch.py ../pico506.kicad_sch      # + writes sch_uuids.json
python3 gen_footprints.py                     # -> ../pico506-lib.pretty/
python3 gen_pcb.py                            # -> ../pico506.kicad_pcb
<KiCad python> refill.py ../pico506.kicad_pcb # fill zones + validate
```
KiCad python: /Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/Current/bin/python3
kicad-cli:    /Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli

Routes go in `build_routes()` in gen_pcb.py using `P(ref,pad)`, `route()`,
`wire_pads()`, `seg()`, `via()`. All coords are board-local (x 0..138 E,
y 0..74 S; rear/connector edge = y74). Pad coords: dict PADS after build().

## Layer discipline
- B.Cu: rear horizontal band slots y≈57.5..67.3 (0.65 pitch), the +5V spine
  at y=39.5 (0.8 mm), west power drops, LED chain y=19.84, +3V3 trunk y=29.45
  (0.6 mm).
- F.Cu: verticals north of the band zone, Pico escapes, jogs at y=28.5.
- THT pads double as layer changes (no via needed). GND: zones only.

## Key coordinates (board-local)
- J1 even-finger columns x = 33.78 + 2.54k: HS3/RWC 33.78, HS2 36.32,
  WG 38.86, SKC 41.4, TK0 43.94, WF 46.48, HS0 49.02, (16) 51.56, HS1 54.1,
  INDEX 56.64, READY 59.18, STEP 61.72, DS1 64.26, DS2 66.8, DS3 69.34,
  DS4 71.88, DIR 74.42. Finger pads span y 67.57..74.55 (B.Cu only!).
- J2 even cols x = 110.02 + 2.54k (2..20): 13 +WR = x-col? J2 signal pins:
  1 (F.Cu odd!) DSELD 110.02; 13/+WR 123.25? -> compute: even p col
  k=(p-2)/2 at 110.02+2.54k: 14 -WR 125.26, 18 -RD 130.34; odd pins 13
  (+WR) and 17 (+RD) are F.Cu at same columns as 14/18 minus… NOTE: odd
  pins are F.Cu at the SAME x as their even partner k=(p-1)/2:
  13 -> x=125.26 F.Cu, 17 -> x=130.34 F.Cu. Pin 1 -> x=110.02 F.Cu.
- RN1 pads (33.5+2.54(k-1), 64): pin1 +5V, pins2-8 = WG,STEP,DIR,HS0,HS1,
  HS2,HS3. RN2 identical at x 56.5+..., pin1 GND.
- DIP pads: U at (X,41): col1 pins 1..7 y=41+2.54(n-1) at x=X; col2 pins
  (14..8 top->bottom for DIP14; 16..9 for DIP16) at x=X+7.62.
- Pico U1 at (35,26.78) rot 90: south row y26.78 = pins 1..20 at
  x=35+2.54(k-1); north row y9.0 = pins 40..21 at x=35..83.26 (pin40 x35,
  pin21 x83.26). GP2 42.62, GP3 45.16, GP4 47.7, GP5 50.24, GP6 55.32,
  GP7 57.86, GP8 60.4, GP9 62.94, GP10 68.02, GP11 70.56, GP12 73.1,
  GP13 75.64, GP14 80.72, GP15 83.26 (all south row y26.78);
  north row y9: GP16 83.26, GP17 80.72, GP18 75.64, GP19 73.1, GP20 70.56,
  GP21 68.02, GP22 62.94, RUN 60.4, 3V3 45.16, VSYS 37.54.
- Pull-up signal ends (pin2): R1 44.16/31 ->GP2; R9 44.16/35 ->GP3;
  R4 47/31 ->GP4; R8 70.16/31 ->GP11; R2 70.16/35 ->GP12; R3 83.16/31
  ->GP13; R5 83.16/35 ->GP14; R6 86/31 ->GP16(N); R7 86/35 ->GP17(N).
  3V3 ends at x34 (R1,R9), 57.16 (R4), 60 (R8,R2), 73 (R3,R5), 96.16 (R6,R7).
- F corridors for GPIO drops: jogs at y=28.5; north-row access via x=84.6
  and x=86.4 (east of module, west of SW1).
- +5V pin pads: U2/U3/U4/U5 pin14 = (X+7.62, 41); U6/U7 pin16 = same.
  Stub down from B spine y39.5. RN1.1 (33.5,64) via B vertical x33.5
  (passes between C3 pads, edges 31.2/34.8). R21.1 (92.5,62->51.84?):
  R21 rot90 pads (92.5,62)+(92.5,51.84); pin1(=+5V)=(92.5,62).
  Corridor x92.5 crosses J4? J4 pads x82..89.62 — clear.
- Term bus (J1->RN1->RN2->U2/U3 in): B band slots; RN pads = layer change;
  from RN2 pin go north on F to the LS05 input pad.
- Diff pair: J2 13(F)/14(B) -> R12 (126, 51.84..62) -> U7 pins 1 (112,41)
  /2 (112,43.54) — swapped wiring is IN THE NETLIST already (U7.1=WR_DATA_P).
  Keep +/− runs paired, similar length; they're short (~15 mm).
  RD: U6.2 (98,43.54)=1Y ->J2-17 (130.34 F), U6.3 (98,46.08)=1Z ->J2-18
  (130.34 B col? no: -RD even pin 18 x=130.34 B). ~32 mm run; keep paired
  gap ~0.6.
- U6 ~G (pin 12) = DS_SEL_N — also to RN?? no: DS_SEL_N nodes: J4 evens
  (82..89.62 y63.54), R21.2 (92.5,51.84), R22.1 (95,62), U3 pins 5,9,11
  and U6.12. Bus it along y≈60 B slot between J4 and U3/U6.
- DS1..4: J1 cols 64.26..71.88 -> J4 odd pads (82,61),(84.54,61),(87.08,61),
  (89.62,61): B slots eastward, short.
- WF: JP1.1 (66,3)=GP22? NO: JP1.1 = WF net = GP22 (62.94, 9 north row);
  JP1.2 = WF_IN -> R10 (90, 22..11.84) + U5.1 (74,41). Route WF: GP22
  (62.94,9)->(F north zone)->JP1 pin1 (66,3). WF_IN: JP1.2 (63.46,3) ->
  east/south to R10 top (90,11.84) then U5.1 (74,41): use F verticals +
  B horizontal at y≈20?
- SD: SPI from north row GP18/19/20/21 (75.64/73.1/70.56/68.02, y9) east to
  SD pads 5,2,7,1 at y30.95 (CLK 116.5? pads: gx=114-px: p5 117.93,
  p2 110.43, p7 122.85, p1 107.93, p8 124.55, p9 105.43, p3 112.93 GND,
  p4 115.43 3V3, p6 120.43 GND). Route around module east end (x84.6/86.4
  corridors busy) — better via B: drop to B at y~11..14 and run east under
  SW1/R10 area, then F stubs. R17-20 pin2 (111.16, 34.8/37.8 rows) join.
- Buzzer: GP15 (83.26, 26.78 south row) -> R11 (24,18)!! R11 is far west:
  B horizontal y19.84 zone? BUZZ_DRV: R11.2 (24,7.84) -> BZ1.1 (14,12)+7.6?
  BZ1 pads: TDK PS1240: (14,12)±(2.5,0)? check PADS. Also LED nets west:
  SELECTED spur to R13.2, Q1 pads (10/12.54/15.08, 30), LED_SINK to D2.1
  (6,32) & J7.2 (23.46,4), LED1_A D2.2 (8.54,32)<-R14.2 (22,19.84),
  LEDX_A R15.2 (30,19.84)->J7.1 (26,4), PWR: R16.2 (26,19.84)->D3.2 (8.54,26),
  D3.1 GND zone.
- UART: GP0 (35,26.78), GP1 (37.54,26.78) -> J5 pins 2/3 at (43.46,3)/(40.92,3):
  F verticals west of module? x<35 region + jog — or B. RUN: SW1.1/2 pads
  (both ends 6mm switch) -> Pico RUN (60.4,9): F via x86.4? SW1 at (91,5):
  pads (88.6,5)+(93.4,5)? check PADS; RUN net = whichever pair per SW_PUSH
  symbol (1/2). B route y~7 under? x 86..60 at y9.8 F is close to north row
  pads — use B y≈5 then via.
- TP1 +12V: J3.1 (5.3,63.84) -> TP1 (23,47): F vertical x5.3?? J3 area free;
  route B (5.3,63.84)->(5.3,49)->(23,49)->(23,47)? watch C1 (27,52) clear.
  0.5 mm width fine.

## DRC loop
kicad-cli pcb drc --severity-all --format report -o drc.txt pico506.kicad_pcb
(refill zones first via refill.py, else zone-connection items are stale).
Expect to iterate: unconnected-items list = worklist.

## Remaining fine-placement nits seen in render v3
- R13/R14/R16/R15 sit close to Pico west end — verify courtyards in DRC.
- J4 silk "1 2 3 4" position vs header; TERM text now west (17,61.5).
- J3 pin-label silk may clip west edge (cosmetic).

## After DRC-clean
- Re-render top/bottom, export schematic PDF.
- Write hardware/README.md: BOM (with 7438-vs-74LS38 note, MC3486/AM26LS32A
  alternates, Bourns 4609X-101-221/331 SIPs, Hirose DM1AA-SF-PEJ(82),
  AMP 350211-1 + 1-480424-0 mate, AMP 61761-2 faston), jumper settings
  (DS2 default for IBM twisted cable), terminator rule, fab notes (hard
  gold + 30deg bevel, 1.6mm), case-design dimensions (board 138x74+5mm tabs,
  edge-connector positions match ST-225 lateral layout, PCB rear edge =
  drive rear plane, card-edge mid-plane ~4.8mm above bay floor on real
  drives, SFF-8501 / Seagate bay hole positions), firmware GPIO map table.
