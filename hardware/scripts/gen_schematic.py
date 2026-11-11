#!/usr/bin/env python3
"""Generate the Circuit schematic sheets that can be drawn from vetted KiCad library pinouts.

Run: python3 scripts/gen_schematic.py   (KiCad 7 libraries must be installed)
Overwrites circuit/*.kicad_sch. Stop using this once sheets are edited by hand in KiCad.
Component VALUES are engineering defaults and must be checked against datasheets.
"""
import os, subprocess, sys, tempfile
import schgen as g

OUT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "circuit"))
prj = g.Project(OUT, "A0-draft")

# ---------------------------------------------------------------- sheet 2: USB-C input
s = prj.sheet("usb", "USB-C input, CC, ESD")
s.text("USB-C INPUT (5 V sink, USB 2.0 device, no Power Delivery)\n"
       "- R1/R2: 5.1k Rd on each CC pin separately (USB Type-C sink requirement).\n"
       "- USB_CC1/USB_CC2 go to MCU ADC inputs to read source current (0.5/1.5/3 A).\n"
       "- U2 clamps D+/D- and VBUS. Both pins of each I/O pair are one node: route through the part.\n"
       "- C1 kept small: a sink may present at most 10 uF on VBUS.\n"
       "TODO before review: 20 V-tolerant CC protection (TPD4S311-class, no library symbol yet);\n"
       "VBUS over-voltage is handled by the charger input rating - confirm from charger datasheet;\n"
       "shield-to-ground scheme (R3) to be decided with the enclosure ESD path.", 20, 20)
s.place("Connector", "USB_C_Receptacle_USB2.0_16P", "J1", 60, 110,
        {"VBUS": "VBUS", "GND": "GND", "CC1": "USB_CC1", "CC2": "USB_CC2", "D+": "USB_DP", "D-": "USB_DM",
         "SBU1": "NC", "SBU2": "NC", "SHIELD": "USB_SHIELD"},
        "USB4105-GF-A (candidate)", "Connector_USB:USB_C_Receptacle_GCT_USB4105-xx-A_16P_TopMnt_Horizontal")
s.R("R1", 130, 80, "USB_CC1", "GND", "5.1k 1%")
s.R("R2", 150, 80, "USB_CC2", "GND", "5.1k 1%")
s.R("R3", 170, 80, "USB_SHIELD", "GND", "0R (TBD)")
s.C("C1", 190, 80, "VBUS", "GND", "1uF 25V", "Capacitor_SMD:C_0603_1608Metric")
s.place("Power_Protection", "USBLC6-2SC6", "U2", 150, 130,
        {"1": "USB_DP", "6": "USB_DP", "3": "USB_DM", "4": "USB_DM", "5": "VBUS", "2": "GND"})

# ---------------------------------------------------------------- sheet 3: haptics, buttons, debug
s = prj.sheet("hmi", "Haptics, buttons, debug")
s.text("HAPTICS: DRV2605L drives an 8 mm LRA from the switched rail +3V3_HAPT.\n"
       "R4 holds EN low while the MCU is in reset. Pin 6 (VDD/NC) left open - CHECK datasheet.\n"
       "C2/C3 values (1 uF) are defaults - CHECK datasheet.", 20, 20)
s.place("Driver_Haptic", "DRV2605LDGS", "U3", 70, 90,
        {"REG": "HAPT_REG", "VDD": "+3V3_HAPT", "VDD/NC": "NC", "SCL": "I2C_SYS_SCL", "SDA": "I2C_SYS_SDA",
         "IN/TRIG": "HAPT_TRIG", "EN": "HAPT_EN", "OUT+": "LRA_P", "OUT-": "LRA_N", "GND": "GND"})
s.place("Connector_Generic", "Conn_01x02", "J3", 135, 90, {"1": "LRA_P", "2": "LRA_N"}, "LRA pads", "")
s.C("C2", 60, 135, "+3V3_HAPT", "GND", "1uF")
s.C("C3", 80, 135, "HAPT_REG", "GND", "1uF")
s.R("R4", 100, 135, "HAPT_EN", "GND", "100k")

s.text("BUTTONS: active low. Pull-up, series resistor, RC debounce and ESD clamp per button.\n"
       "The MCU reads BTN_CONFIRM_N directly in the secure world; it is the only signing approval input.\n"
       "BTN_POWER_RAW also goes to the charger push-button input (power sheet, not drawn yet).\n"
       "Switch and TVS part numbers TBD (candidates: Panasonic EVQ-P7 side-push; 0402 ESD diode).", 170, 20)
for i, (name, y) in enumerate([("CONFIRM", 90), ("POWER", 150)]):
    raw, out, k = f"BTN_{name}_RAW", f"BTN_{name}_N", 5 + 3 * i
    s.place("Switch", "SW_Push", f"SW{i + 1}", 185, y, {"1": raw, "2": "GND"}, name, "")
    s.place("Device", "D_TVS", f"D{i + 1}", 185, y + 20, {"1": raw, "2": "GND"}, "ESD 0402 (TBD)", "")
    s.R(f"R{k}", 215, y, "+3V3", raw, "100k")
    s.R(f"R{k + 1}", 235, y, raw, out, "1k")
    s.C(f"C{4 + i}", 255, y, out, "GND", "100nF")

s.text("DEBUG: Tag-Connect TC2030-NL pads,\nno connector fitted. Internal only.\n"
       "Production: debug locked in the MCU;\npads not reachable with the case closed.", 310, 40)
s.place("Connector", "Conn_ARM_SWD_TagConnect_TC2030-NL", "J2", 330, 100,
        {"VCC": "+3V3", "SWDIO": "SWDIO", "~{RESET}": "NRST", "SWCLK": "SWCLK", "GND": "GND", "SWO": "SWO"}, "SWD TC2030-NL")

# ---------------------------------------------------------------- root
prj.root.text("CIRCUIT main board - schematic status\n\n"
              "Drawn (draft, from KiCad library pinouts): 2 USB-C input; 3 Haptics, buttons, debug\n\n"
              "Not drawn yet:\n"
              "- Charger, battery, fuel gauge; 3V3 buck-boost, load switches, backlight driver;\n"
              "  secure element; NFC; BLE module - these need pinouts from datasheets (no library symbols)\n"
              "- Main MCU and display/touch connectors - blocked on gate G1 and panel selection\n\n"
              "Signals between sheets use global labels. No routing before this schematic is complete and reviewed.", 30, 30, 2.2)
prj.write()

# ---------------------------------------------------------------- self-check against KiCad's own netlist
with tempfile.TemporaryDirectory() as d:
    nl = os.path.join(d, "n.net")
    subprocess.run(["kicad-cli", "sch", "export", "netlist", "-o", nl, os.path.join(OUT, "circuit.kicad_sch")],
                   check=True, capture_output=True)
    tree = g.parse(open(nl).read())
got = {}
for sec in tree:
    if isinstance(sec, list) and sec[0] == "nets":
        for net in sec[1:]:
            d = {c[0]: c for c in net if isinstance(c, list) and c[0] != "node"}
            nodes = {f"{dict((x[0], x[1]) for x in c if isinstance(x, list))['ref']}."
                     f"{dict((x[0], x[1]) for x in c if isinstance(x, list))['pin']}"
                     for c in net if isinstance(c, list) and c[0] == "node"}
            got[str(d["name"][1]).lstrip("/")] = nodes
exp = prj.expected()
bad = [(n, sorted(exp[n] ^ got.get(n, set()))) for n in exp if exp[n] != got.get(n, set())]
extra = [n for n in got if n not in exp and not n.startswith("unconnected-")]
print(f"nets expected {len(exp)}, matched {len(exp) - len(bad)}, unexpected nets {extra}")
for b in bad:
    print("  MISMATCH", b)
sys.exit(1 if bad or extra else 0)
