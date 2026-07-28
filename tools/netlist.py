"""Pico506 board netlist — the single source of truth.

Every component, its symbol, footprint and pin->net mapping lives here.
Both the schematic generator and the PCB generator consume this module, so
the two can never disagree.

Net naming: 5V-side ST-506 bus signals are active-low and carry an _N
suffix.  3.3V-side (Pico GPIO) signals are active-high, no suffix.
"""

# --------------------------------------------------------------------------
# Nets (documentation of intent; the authoritative list is derived from the
# component pin maps below).
#
#   +5V, +3V3, GND, +12V, VSYS           power
#   WG_N STEP_N DIR_N HS0_N HS1_N HS2_N HS3_RWC_N        J1 control inputs
#   DS1_N DS2_N DS3_N DS4_N DS_SEL_N                     drive select bus
#   INDEX_N READY_N TRK0_N SKC_N WFAULT_N                J1 control outputs
#   DRV_SELD_N                                           J2 pin 1 output
#   WR_DATA_P WR_DATA_N_PAIR RD_DATA_P RD_DATA_N_PAIR    differential data
#   WG_GATED WR_DATA HS0 RD_DATA INDEX SERVO_GATE READY TRK0 SKC SELECTED
#   STEP_GATED DIR_IN HS1 BUZZ HS2 HS3 SD_SCK SD_MOSI SD_MISO SD_CS WF
#   WF_IN WR_RX UART_TX UART_RX RUN BUZZ_DRV Q1_B LED_SINK LED1_A LEDX_A
#   SD_DAT1 SD_DAT2
# --------------------------------------------------------------------------

# J1 34-pin control connector: even pins carry signals, odd pins are GND.
J1_PINS = {
    2: "HS3_RWC_N",   # -HEAD SELECT 2^3 / -REDUCED WRITE CURRENT
    4: "HS2_N",       # -HEAD SELECT 2^2
    6: "WG_N",        # -WRITE GATE
    8: "SKC_N",       # -SEEK COMPLETE
    10: "TRK0_N",     # -TRACK 000
    12: "WFAULT_N",   # -WRITE FAULT
    14: "HS0_N",      # -HEAD SELECT 2^0
    16: None,         # reserved
    18: "HS1_N",      # -HEAD SELECT 2^1
    20: "INDEX_N",    # -INDEX
    22: "READY_N",    # -READY
    24: "STEP_N",     # -STEP
    26: "DS1_N",      # -DRIVE SELECT 1
    28: "DS2_N",      # -DRIVE SELECT 2
    30: "DS3_N",      # -DRIVE SELECT 3
    32: "DS4_N",      # -DRIVE SELECT 4
    34: "DIR_N",      # -DIRECTION IN
}
for _odd in range(1, 35, 2):
    J1_PINS[_odd] = "GND"

J1_NAMES = {
    2: "~{HS3}/~{RWC}", 4: "~{HS2}", 6: "~{WRITE_GATE}", 8: "~{SEEK_COMPLETE}",
    10: "~{TRACK_0}", 12: "~{WRITE_FAULT}", 14: "~{HS0}", 16: "RSVD",
    18: "~{HS1}", 20: "~{INDEX}", 22: "~{READY}", 24: "~{STEP}",
    26: "~{DS1}", 28: "~{DS2}", 30: "~{DS3}", 32: "~{DS4}", 34: "~{DIR_IN}",
}

# J2 20-pin data connector (ST-412 OEM manual).
J2_PINS = {
    1: "DRV_SELD_N",       # -DRIVE SELECTED
    2: "GND",
    3: None,               # reserved
    4: "GND",
    5: None,               # reserved (-WRITE PROTECT on some drives)
    6: "GND",
    7: None,               # reserved
    8: "GND",
    9: None,               # reserved
    10: None,              # reserved
    11: "GND",
    12: "GND",
    13: "WR_DATA_P",       # +MFM WRITE DATA
    14: "WR_DATA_M",       # -MFM WRITE DATA
    15: "GND",
    16: "GND",
    17: "RD_DATA_P",       # +MFM READ DATA
    18: "RD_DATA_M",       # -MFM READ DATA
    19: "GND",
    20: "GND",
}

J2_NAMES = {
    1: "~{DRIVE_SELECTED}", 3: "RSVD", 5: "RSVD", 7: "RSVD", 9: "RSVD",
    10: "RSVD", 13: "+WR_DATA", 14: "-WR_DATA", 17: "+RD_DATA", 18: "-RD_DATA",
}

# Raspberry Pi Pico pin map (module pin -> net).
PICO_PINS = {
    1: "UART_TX",      # GP0
    2: "UART_RX",      # GP1
    3: "GND", 8: "GND", 13: "GND", 18: "GND", 23: "GND", 28: "GND",
    33: "GND", 38: "GND",
    4: "WG_GATED",     # GP2  HDD WRITE_GATE (gated by select)
    5: "WR_DATA",      # GP3  HDD WRITE
    6: "HS0",          # GP4  HDD HEAD_1
    7: "RD_DATA",      # GP5  HDD READ
    9: "INDEX",        # GP6  HDD INDEX
    10: "SERVO_GATE",  # GP7  HDD SERVO_GATE (JVC RLL only)
    11: "READY",       # GP8  HDD READY
    12: "TRK0",        # GP9  HDD TRACK_0
    14: "SKC",         # GP10 HDD SEEK_COMPLETE
    15: "SELECTED",    # GP11 HDD SELECT
    16: "STEP_GATED",  # GP12 HDD STEP (gated by select)
    17: "DIR_IN",      # GP13 HDD DIR_IN
    19: "HS1",         # GP14 (future head select 2^1)
    20: "BUZZ",        # GP15 buzzer
    21: "HS2",         # GP16 (future head select 2^2)
    22: "HS3",         # GP17 (future head select 2^3)
    24: "SD_SCK",      # GP18
    25: "SD_MOSI",     # GP19
    26: "SD_MISO",     # GP20
    27: "SD_CS",       # GP21
    29: "WF",          # GP22 (future write fault, via JP1)
    30: "RUN",
    31: None, 32: None, 34: None, 35: None, 37: None, 40: None,
    36: "+3V3",
    39: "VSYS",
}

COMPONENTS = []


def comp(ref, symbol, footprint, value, pins, fields=None, dnp=False):
    COMPONENTS.append(
        dict(ref=ref, symbol=symbol, footprint=footprint, value=value,
             pins=pins, fields=fields or {}, dnp=dnp)
    )


LIB = "pico506-lib"

# ---- connectors -----------------------------------------------------------
comp("J1", f"{LIB}:ST506_J1_Control", f"{LIB}:EdgeConn_ST506_J1_34",
     "ST-506 CONTROL", {str(k): v for k, v in J1_PINS.items()},
     fields={"Description": "34-pin card edge, mates 3M 3463 style IDC"})

comp("J2", f"{LIB}:ST506_J2_Data", f"{LIB}:EdgeConn_ST506_J2_20",
     "ST-506 DATA", {str(k): v for k, v in J2_PINS.items()},
     fields={"Description": "20-pin card edge, mates 3M 3461 style IDC"})

comp("J3", f"{LIB}:ST506_J3_Power", f"{LIB}:PWR_MATE-N-LOK_350211_Horizontal",
     "AMP 350211-1",
     {"1": "+12V", "2": "GND", "3": "GND", "4": "+5V"},
     fields={"Description": "Disk drive power, rear entry; mates AMP 1-480424-0."
                            " Form the vertical header's legs 90 deg (as Seagate"
                            " did) or use a right-angle MATE-N-LOK equivalent"})

comp("J4", "Connector_Generic:Conn_02x04_Odd_Even",
     "Connector_PinHeader_2.54mm:PinHeader_2x04_P2.54mm_Vertical",
     "DRIVE SELECT",
     {"1": "DS1_N", "2": "DS_SEL_N", "3": "DS2_N", "4": "DS_SEL_N",
      "5": "DS3_N", "6": "DS_SEL_N", "7": "DS4_N", "8": "DS_SEL_N"},
     fields={"Description": "Drive select jumper block, columns DS4..DS1"
                            " west to east; fit one shunt"})

comp("J5", "Connector_Generic:Conn_01x03",
     "Connector_PinHeader_2.54mm:PinHeader_1x03_P2.54mm_Vertical",
     "UART",
     {"1": "GND", "2": "UART_TX", "3": "UART_RX"})

comp("J6", "Connector_Generic:Conn_01x02",
     "Connector_PinHeader_2.54mm:PinHeader_1x02_P2.54mm_Vertical",
     "SERVO GATE 3V3",
     {"1": "SERVO_GATE", "2": "GND"})

comp("J7", "Connector_Generic:Conn_01x02",
     "Connector_PinHeader_2.54mm:PinHeader_1x02_P2.54mm_Vertical",
     "FRONT LED",
     {"1": "LEDX_A", "2": "LED_SINK"})

comp("JP1", "Connector_Generic:Conn_01x02",
     "Connector_PinHeader_2.54mm:PinHeader_1x02_P2.54mm_Vertical",
     "WF EN",
     {"1": "WF", "2": "WF_IN"},
     fields={"Description": "Close when firmware drives WRITE FAULT (GP22)"})

# ---- Raspberry Pi Pico ----------------------------------------------------
comp("U1", f"{LIB}:RaspberryPi_Pico", f"{LIB}:RaspberryPi_Pico_Common_THT",
     "Raspberry Pi Pico", {str(k): v for k, v in PICO_PINS.items()},
     fields={"Description": "Socket with two 1x20 2.54mm female headers"})

# ---- input inverters: 74LS05 open-collector hex inverters ------------------
# U2: units 1..6 = (in, out): WG, STEP, DIR, HS0, HS1, HS2
comp("U2", "74xx:74LS05", "Package_DIP:DIP-14_W7.62mm", "74LS05",
     {"1": "WG_N", "2": "WG_GATED",
      "3": "STEP_N", "4": "STEP_GATED",
      "5": "DIR_N", "6": "DIR_IN",
      "9": "HS0_N", "8": "HS0",
      "11": "HS1_N", "10": "HS1",
      "13": "HS2_N", "12": "HS2",
      "7": "GND", "14": "+5V"})

# U3: WR data post-receiver inverter, HS3, select, and the two select
# "monitor" channels that wire-AND onto the gated WG/STEP nodes.
comp("U3", "74xx:74LS05", "Package_DIP:DIP-14_W7.62mm", "74LS05",
     {"1": "WR_RX", "2": "WR_DATA",
      "3": "DS_SEL_N", "4": "WG_GATED",
      "5": None, "6": None,
      "9": "HS3_RWC_N", "8": "HS3",
      "11": "DS_SEL_N", "10": "STEP_GATED",
      "13": "GND", "12": None,
      "7": "GND", "14": "+5V"})

# ---- output drivers: 74LS38 open-collector NAND, gated by SELECTED --------
comp("U4", "74xx:74LS38", "Package_DIP:DIP-14_W7.62mm", "7438",
     {"1": "INDEX", "2": "SELECTED", "3": "INDEX_N",
      "4": "READY", "5": "SELECTED", "6": "READY_N",
      "9": "TRK0", "10": "SELECTED", "8": "TRK0_N",
      "12": "SKC", "13": "SELECTED", "11": "SKC_N",
      "7": "GND", "14": "+5V"})

comp("U5", "74xx:74LS38", "Package_DIP:DIP-14_W7.62mm", "7438",
     {"1": "WF_IN", "2": "SELECTED", "3": "WFAULT_N",
      "4": "SELECTED", "5": "SELECTED", "6": "DRV_SELD_N",
      "9": "GND", "10": "GND", "8": None,
      "12": "DS_SEL_N", "13": "DS_SEL_N", "11": "SELECTED",
      "7": "GND", "14": "+5V"})

# ---- differential data path ------------------------------------------------
# Read: AM26LS31 driver, output pair enabled only while selected (~G <- DS_SEL_N)
comp("U6", "Interface:AM26LS31CN", "Package_DIP:DIP-16_W7.62mm",
     "AM26LS31CN",
     {"1": "RD_DATA", "2": "RD_DATA_P", "3": "RD_DATA_M",
      "4": "GND",              # G  (active-high enable) tied off
      "12": "DS_SEL_N",        # ~G (active-low enable)  <- selected DS line
      "7": "GND", "9": "GND", "15": "GND",   # unused inputs
      "5": None, "6": None, "10": None, "11": None, "13": None, "14": None,
      "8": "GND", "16": "+5V"})

# Write: MC3486 receiver (= AM26LS32A with pins 4+12 tied high).  Inputs are
# deliberately swapped (+WR into E-, -WR into E+) so OUT idles high and the
# following 74LS05 restores active-high pulses at GP3.
comp("U7", f"{LIB}:MC3486N", "Package_DIP:DIP-16_W7.62mm",
     "MC3486N",
     {"1": "WR_DATA_P", "2": "WR_DATA_M", "3": "WR_RX",
      "4": "+5V", "12": "+5V",
      "6": "GND", "7": "+5V",     # unused ch2 biased inactive
      "10": "GND", "9": "+5V",    # unused ch3
      "14": "GND", "15": "+5V",   # unused ch4
      "5": None, "11": None, "13": None,
      "8": "GND", "16": "+5V"},
     fields={"Description": "MC3486 or AM26LS32AC"})

# ---- terminator: ST-506 spec is a 220/330 split on each control input, ----
# ---- removable on all but the last drive of the daisy chain            ----
_TERM_LINES = {"2": "WG_N", "3": "STEP_N", "4": "DIR_N", "5": "HS0_N",
               "6": "HS1_N", "7": "HS2_N", "8": "HS3_RWC_N", "9": None}
comp("RN1", "Device:R_Network08", "Resistor_THT:R_Array_SIP9", "220",
     dict(_TERM_LINES, **{"1": "+5V"}),
     fields={"Description": "Terminator pull-up half; fit in SIP socket, remove"
                            " on all but the last drive on the control cable"})
# RN2 line order differs from RN1: the router assigns each net the SIP pin
# whose stub drops cleanly between the J1 finger escape columns.
comp("RN2", "Device:R_Network08", "Resistor_THT:R_Array_SIP9", "330",
     {"1": "GND", "2": "WG_N", "3": "STEP_N", "4": "HS3_RWC_N",
      "5": "DIR_N", "6": "HS0_N", "7": "HS1_N", "8": "HS2_N", "9": None},
     fields={"Description": "Terminator pull-down half; fit in SIP socket"})

# Fixed 220/330 on the selected drive-select line (ST-225 style, after jumper)
comp("R21", "Device:R", "Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P10.16mm_Horizontal",
     "220", {"1": "+5V", "2": "DS_SEL_N"})
comp("R22", "Device:R", "Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P10.16mm_Horizontal",
     "330", {"1": "DS_SEL_N", "2": "GND"})

# ---- pull-ups to 3V3 on every 74LS05 output feeding the Pico ---------------
_PULLUPS = [
    ("R1", "WG_GATED"), ("R2", "STEP_GATED"), ("R3", "DIR_IN"),
    ("R4", "HS0"), ("R5", "HS1"), ("R6", "HS2"), ("R7", "HS3"),
    ("R8", "SELECTED"), ("R9", "WR_DATA"),
]
for _ref, _net in _PULLUPS:
    comp(_ref, "Device:R", "Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P10.16mm_Horizontal",
         "1k", {"1": "+3V3", "2": _net})

comp("R10", "Device:R", "Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P10.16mm_Horizontal",
     "470", {"1": "WF_IN", "2": "GND"},
     fields={"Description": "Holds WRITE FAULT inactive while JP1 open"})

comp("R11", "Device:R", "Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P10.16mm_Horizontal",
     "100", {"1": "BUZZ", "2": "BUZZ_DRV"})

comp("R12", "Device:R", "Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P10.16mm_Horizontal",
     "100", {"1": "WR_DATA_P", "2": "WR_DATA_M"},
     fields={"Description": "Write data pair termination"})

comp("R13", "Device:R", "Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P10.16mm_Horizontal",
     "4.7k", {"1": "SELECTED", "2": "Q1_B"})

comp("R14", "Device:R", "Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P10.16mm_Horizontal",
     "470", {"1": "+5V", "2": "LED1_A"})

comp("R15", "Device:R", "Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P10.16mm_Horizontal",
     "470", {"1": "+5V", "2": "LEDX_A"})

comp("R16", "Device:R", "Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P10.16mm_Horizontal",
     "1k", {"1": "+5V", "2": "LED2_A"})

# SD card pull-ups
for _ref, _net in [("R17", "SD_CS"), ("R18", "SD_MISO"),
                   ("R19", "SD_DAT1"), ("R20", "SD_DAT2")]:
    comp(_ref, "Device:R", "Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P10.16mm_Horizontal",
         "10k", {"1": "+3V3", "2": _net})

# ---- LEDs / transistor ------------------------------------------------------
comp("Q1", "Transistor_BJT:2N3904", "Package_TO_SOT_THT:TO-92_Inline",
     "2N3904", {"1": "GND", "2": "Q1_B", "3": "LED_SINK"})

comp("D1", "Device:D_Schottky", "Diode_THT:D_DO-41_SOD81_P10.16mm_Horizontal",
     "1N5817", {"1": "VSYS", "2": "+5V"})   # pin1 = K, pin2 = A

comp("D2", "Device:LED", "LED_THT:LED_D5.0mm", "ACT amber",
     {"1": "LED_SINK", "2": "LED1_A"})       # 1 = K, 2 = A

comp("D3", "Device:LED", "LED_THT:LED_D5.0mm", "PWR green",
     {"1": "GND", "2": "LED2_A"})

# ---- decoupling / bulk ------------------------------------------------------
comp("C1", "Device:C_Polarized", "Capacitor_THT:CP_Radial_D6.3mm_P2.50mm",
     "100u/16V", {"1": "+5V", "2": "GND"})
comp("C2", "Device:C_Polarized", "Capacitor_THT:CP_Radial_D5.0mm_P2.50mm",
     "22u/16V", {"1": "VSYS", "2": "GND"})
for _i, _ref in enumerate(["C3", "C4", "C5", "C6", "C7", "C8"]):
    comp(_ref, "Device:C", "Capacitor_THT:C_Disc_D5.0mm_W2.5mm_P5.00mm",
         "100n", {"1": "+5V", "2": "GND"})
comp("C9", "Device:C", "Capacitor_THT:C_Disc_D5.0mm_W2.5mm_P5.00mm",
     "100n", {"1": "+3V3", "2": "GND"})
comp("C10", "Device:C_Polarized", "Capacitor_THT:CP_Radial_D5.0mm_P2.50mm",
     "10u/16V", {"1": "+3V3", "2": "GND"})

# ---- SD card socket ---------------------------------------------------------
comp("SD1", f"{LIB}:SD_FullSize", f"{LIB}:SD_Hirose_DM1AA_SF_PEJ82",
     "SD socket",
     {"1": "SD_CS", "2": "SD_MOSI", "3": "GND", "4": "+3V3", "5": "SD_SCK",
      "6": "GND", "7": "SD_MISO", "8": "SD_DAT1", "9": "SD_DAT2",
      "SH": "GND", "SW": None, "WP": None, "CP": None},
     fields={"Description": "Hirose DM1AA-SF-PEJ(82) full-size SD"})

# ---- buzzer / button --------------------------------------------------------
comp("BZ1", "Device:Buzzer", "Buzzer_Beeper:Buzzer_TDK_PS1240P02BT_D12.2mm_H6.5mm",
     "PS1240", {"1": "BUZZ_DRV", "2": "GND"})

comp("SW1", "Switch:SW_Push", "Button_Switch_THT:SW_PUSH_6mm_H4.3mm",
     "RESET", {"1": "RUN", "2": "GND"})

comp("TP1", "Connector:TestPoint", "TestPoint:TestPoint_Pad_D2.0mm",
     "+12V", {"1": "+12V"},
     fields={"Description": "+12V unused by the emulator; spare for mods"})

# ---- mechanical -------------------------------------------------------------
for _ref in ["H1", "H2", "H3", "H4"]:
    comp(_ref, "Mechanical:MountingHole", "MountingHole:MountingHole_3.2mm_M3",
         "M3", {})

comp("FG1", "Mechanical:MountingHole_Pad", f"{LIB}:Faston_Tab_AMP61761",
     "FRAME GND", {"1": "GND"},
     fields={"Description": "AMP 61761-2 0.187in faston tab, or bolt a lug"})


def nets():
    """net name -> [(ref, pin), ...]"""
    out = {}
    for c in COMPONENTS:
        for pin, net in c["pins"].items():
            if net:
                out.setdefault(net, []).append((c["ref"], pin))
    return out


def by_ref():
    return {c["ref"]: c for c in COMPONENTS}


if __name__ == "__main__":
    n = nets()
    print(f"{len(COMPONENTS)} components, {len(n)} nets")
    single = {k: v for k, v in n.items() if len(v) < 2}
    if single:
        print("single-pin nets:", single)
