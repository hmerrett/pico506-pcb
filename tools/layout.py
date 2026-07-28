"""Board geometry constants shared by the footprint and PCB generators.

Coordinate system: KiCad page coords, +x east, +y south.  The board's REAR
edge (connector edge) is the SOUTH edge.  Viewed from the rear of the
installed drive, the left-right order is J2 (data), J1 (control), J3
(power) — which in this top view (from the component side) maps to
J3 west, J1 center, J2 east.  Lateral positions follow the measured
ST-225 arrangement so standard cable dressing just works.
"""

# board envelope (main outline, excluding the protruding connector tabs)
BOARD_W = 138.0
BOARD_D = 74.0
ORIGIN_X = 30.0            # page offset of board west edge
ORIGIN_Y = 30.0            # page offset of board north (front) edge

TAB_PROTRUDE = 5.0          # card-edge tabs stand this proud of the main edge
FINGER_LEN = 11.43          # 0.450 in gold from tab tip
EDGE_SETBACK = 0.45         # copper pulled back from the routed tip (DRC);
                            # the 30 deg bevel eats this zone anyway
FINGER_W = 1.40             # 0.055 in pad width
FINGER_PITCH = 2.54         # 0.100 in
KEY_SLOT_W = 0.914          # 0.036 in
KEY_SLOT_DEPTH = 12.5       # from tab tip, cuts past the fingers
TAB_CORNER = 1.0            # 45 deg corner cut at tab tip

# Relief cut-outs either side of each tab.  The fingers are FINGER_LEN long but
# the tab only stands TAB_PROTRUDE proud, so a mating socket's shell hits the
# main board edge with most of the finger length still unengaged.  The cut-outs
# take the board away beside each tab, as far inboard as the fingers reach, so
# the socket can seat fully.  Increasing TAB_PROTRUDE instead would work but
# moves every finger pad south and grows the board's depth.
TAB_RELIEF_W = 6.0

# ST-225 measured lateral positions, remapped to this top view.
# x measured from board WEST edge; board is 138 wide, centerline at 69.
J1_CENTER_X = 69.0 - 14.9   # = 54.1   central 34-pin control tab
J1_TAB_W = 45.09            # 1.775 in
J2_CENTER_X = 69.0 + 52.45  # = 121.45 eastern 20-pin data tab
J2_TAB_W = 27.30            # 1.075 in

# J3 power: pin 1 (+12V) at the far west, 5.08 pitch
J3_PIN1_X = 5.30
J3_PITCH = 5.08
J3_ROW_SETBACK = 10.16      # hole row this far north of the rear edge
J3_HOUSING_W = 25.4         # AMP 350211-1 body: exactly 1.00 in
J3_RELIEF_GAP = 0.6         # keep J1's west relief off the J3 housing outline

# frame ground faston between J1 and J2 tabs
FG_X = 93.5
FG_Y_FROM_REAR = 6.0


def finger_xs(center_x, n_cols):
    span = (n_cols - 1) * FINGER_PITCH
    return [center_x - span / 2 + k * FINGER_PITCH for k in range(n_cols)]


def tab_relief_y():
    """Inboard edge of the relief cut-outs — level with the finger tops, so a
    socket can travel until its face reaches the end of the gold."""
    return BOARD_D + TAB_PROTRUDE - FINGER_LEN


def j3_east_edge():
    """East face of the J3 power housing (its own footprint is centred on the
    middle of the 4-hole row)."""
    return J3_PIN1_X + 1.5 * J3_PITCH + J3_HOUSING_W / 2


def tab_relief_x(center_x, tab_w):
    """(west, east) x of one tab's relief cut-outs, clamped to the board and
    kept clear of the J3 housing."""
    hw = tab_w / 2
    west = max(center_x - hw - TAB_RELIEF_W, j3_east_edge() + J3_RELIEF_GAP, 0.0)
    east = min(center_x + hw + TAB_RELIEF_W, BOARD_W)
    return west, east


def key_slot_x(center_x, n_cols):
    """Key slot between pins 4 and 6 = between finger columns 1 and 2
    (0-based) counting from the pin-2 (west) end."""
    xs = finger_xs(center_x, n_cols)
    return (xs[1] + xs[2]) / 2.0
