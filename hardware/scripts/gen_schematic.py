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

# ---------------------------------------------------------------- sheet 4: main MCU
PINMAP = {
    # display: LTDC RGB565 (same balls as ST's STM32U5G9J-DK2), SPI1 for panel init
    "PD8": "LCD_R3", "PD9": "LCD_R4", "PD10": "LCD_R5", "PD11": "LCD_R6", "PD12": "LCD_R7",
    "PE9": "LCD_G2", "PE10": "LCD_G3", "PE11": "LCD_G4", "PE12": "LCD_G5", "PE13": "LCD_G6", "PE14": "LCD_G7",
    "PD15": "LCD_B3", "PD0": "LCD_B4", "PD1": "LCD_B5", "PE7": "LCD_B6", "PE8": "LCD_B7",
    "PD3": "LCD_CLK", "PD6": "LCD_DE", "PE0": "LCD_HSYNC", "PD13": "LCD_VSYNC",
    "PA5": "LCD_SPI_SCK", "PA7": "LCD_SPI_MOSI", "PA4": "LCD_SPI_CS", "PA6": "LCD_DC", "PA3": "LCD_RST", "PA2": "LCD_TE",
    "PB0": "LCD_BL_PWM", "PF0": "EN_3V3_LCD",
    # touch (I2C1, dedicated bus)
    "PB8": "I2C_TP_SCL", "PB9": "I2C_TP_SDA", "PB5": "TP_INT_N", "PB4": "TP_RST_N",
    # secure element (I2C2, dedicated bus)
    "PB10": "I2C_SE_SCL", "PB11": "I2C_SE_SDA", "PB12": "SE_RST_N",
    # system bus (I2C3): charger, haptic driver, NFC tag
    "PC0": "I2C_SYS_SCL", "PC1": "I2C_SYS_SDA", "PB15": "CHG_INT_N", "PB1": "NFC_FD", "PF4": "EN_3V3_NFC",
    # BLE module (USART1, untrusted transport)
    "PG9": "BLE_UART_TX", "PG10": "BLE_UART_RX", "PG11": "BLE_UART_CTS", "PG12": "BLE_UART_RTS",
    "PG13": "BLE_RST_N", "PG14": "EN_3V3_BLE", "PB7": "BLE_WAKE",
    # USB, CC sense, battery sense
    "PA12": "USB_DP", "PA11": "USB_DM", "PC2": "USB_CC1", "PC3": "USB_CC2", "PC4": "VBAT_SENSE", "PC5": "VBAT_SENSE_EN",
    # buttons (wake-up pins), haptics, tamper
    "PC13": "BTN_CONFIRM_N", "PA0": "BTN_POWER_N", "PF1": "HAPT_EN", "PF2": "HAPT_TRIG", "PF3": "EN_3V3_HAPT",
    "PE3": "TAMPER_1", "PE4": "TAMPER_2",
    # debug, clocks, boot
    "PA13": "SWDIO", "PA14": "SWCLK", "PB3": "SWO", "NRST": "NRST", "PH3": "BOOT0",
    "PH0": "HSE_IN", "PH1": "HSE_OUT", "PC14": "LSE_IN", "PC15": "LSE_OUT",
    # supplies
    "VDD": "+3V3", "VDDIO2": "+3V3", "VDDUSB": "+3V3", "VDDSMPS": "+3V3", "VSS": "GND", "VSSA": "GND", "VSSSMPS": "GND",
    "VSSDSI": "GND", "VREF-": "GND", "VDDA": "+3V3A", "VREF+": "+3V3A", "VBAT": "VBAT_MCU",
    "VDD11": "VDD11", "VLXSMPS": "SMPS_LX", "VDD11USB": "VDD11USB", "VDDDSI": "+3V3", "VDD11DSI": "VCAPDSI",
}
s = prj.sheet("mcu", "Main MCU STM32U5G9", "A2")
s.text("MAIN MCU: STM32U5G9NJH6Q, TFBGA-216 13x13 mm, 0.8 mm pitch. Pin functions are taken from the KiCad library's\n"
       "alternate-function data. Every ball not listed in PINMAP is left unconnected (spare GPIO).\n\n"
       "MUST BE CONFIRMED AGAINST THE DATASHEET AND AN5373 BEFORE REVIEW (st.com was not reachable):\n"
       " 1. SMPS network: L1 value and the capacitor on each VDD11 ball (C20-C22).\n"
       " 2. VDD11USB: whether it is tied to VDD11 (R20 fitted) or only decoupled (R20 not fitted).\n"
       " 3. DSI unused: required connection of VDDDSI, VDD11DSI/VCAPDSI and the DSI balls.\n"
       " 4. VBAT: tied to +3V3 through R21 for now; becomes the coin-cell backup rail if tamper-in-storage is adopted.\n"
       " 5. HSE 16 MHz (as on ST's dev kit) is assumed valid for the USB HS PHY; crystal load capacitors C30-C33 are placeholders.\n"
       " 6. Decoupling count and values (C10-C19, C23-C29) are defaults.\n"
       "Nets ending in another sheet that is not drawn yet (display, touch, secure element, BLE, NFC, charger) are single-ended for now.", 25, 20, 2.0)
s.place("MCU_ST_STM32U5", "STM32U5G9NJHxQ", "U1", 400, 215, PINMAP, "STM32U5G9NJH6Q", default="NC")

x0 = 30
for i in range(10):                      # one 100 nF per VDD ball
    s.C(f"C{10 + i}", x0 + i * 16, 120, "+3V3", "GND", "100nF")
s.C("C23", x0, 160, "+3V3", "GND", "10uF", "Capacitor_SMD:C_0603_1608Metric")
s.C("C24", x0 + 16, 160, "+3V3", "GND", "100nF")      # VDDIO2
s.C("C25", x0 + 32, 160, "+3V3", "GND", "100nF")      # VDDIO2
s.C("C26", x0 + 48, 160, "+3V3", "GND", "100nF")      # VDDUSB
s.C("C27", x0 + 64, 160, "+3V3", "GND", "10uF", "Capacitor_SMD:C_0603_1608Metric")   # VDDSMPS
s.C("C28", x0 + 80, 160, "+3V3", "GND", "100nF")      # VDDDSI
s.text("Decoupling: C10-C19 at VDD balls; C24/C25 VDDIO2; C26 VDDUSB; C27 VDDSMPS; C28 VDDDSI", x0, 100)

s.text("Core supply (internal SMPS) - values TBD from datasheet", x0, 185)
s.place("Device", "L", "L1", x0, 205, {"1": "SMPS_LX", "2": "VDD11"}, "2.2uH (TBD)", "Inductor_SMD:L_0805_2012Metric")
for i in range(3):
    s.C(f"C{20 + i}", x0 + 20 + i * 16, 205, "VDD11", "GND", "2.2uF (TBD)")
s.R("R20", x0 + 76, 205, "VDD11USB", "VDD11", "0R (TBD, see note 2)")
s.C("C29", x0 + 100, 205, "VDD11USB", "GND", "100nF (TBD)")
s.C("C34", x0 + 124, 205, "VCAPDSI", "GND", "2.2uF (TBD)")

s.text("Analog supply and reference", x0, 230)
s.place("Device", "FerriteBead", "FB1", x0, 250, {"1": "+3V3", "2": "+3V3A"}, "600R@100MHz", "Inductor_SMD:L_0402_1005Metric")
s.C("C35", x0 + 20, 250, "+3V3A", "GND", "1uF")
s.C("C36", x0 + 36, 250, "+3V3A", "GND", "100nF")
s.R("R21", x0 + 60, 250, "+3V3", "VBAT_MCU", "0R")
s.C("C37", x0 + 80, 250, "VBAT_MCU", "GND", "100nF")

s.text("Reset and boot", x0, 275)
s.C("C38", x0, 295, "NRST", "GND", "100nF")
s.R("R22", x0 + 20, 295, "BOOT0", "GND", "10k")

s.text("Clocks: 16 MHz HSE, 32.768 kHz LSE (load capacitors depend on the crystals chosen)", x0, 320)
s.place("Device", "Crystal_GND24", "Y1", x0 + 10, 345, {"1": "HSE_IN", "3": "HSE_OUT", "2": "GND", "4": "GND"},
        "16MHz", "Crystal:Crystal_SMD_2016-4Pin_2.0x1.6mm")
s.C("C30", x0 + 40, 345, "HSE_IN", "GND", "CL (TBD)")
s.C("C31", x0 + 56, 345, "HSE_OUT", "GND", "CL (TBD)")
s.place("Device", "Crystal", "Y2", x0 + 90, 345, {"1": "LSE_IN", "2": "LSE_OUT"}, "32.768kHz", "Crystal:Crystal_SMD_3215-2Pin_3.2x1.5mm")
s.C("C32", x0 + 115, 345, "LSE_IN", "GND", "CL (TBD)")
s.C("C33", x0 + 131, 345, "LSE_OUT", "GND", "CL (TBD)")

s.text("Shared pull-ups for the three I2C buses (values default)", x0 + 170, 275)
for i, n in enumerate(["I2C_TP_SCL", "I2C_TP_SDA", "I2C_SE_SCL", "I2C_SE_SDA", "I2C_SYS_SCL", "I2C_SYS_SDA"]):
    s.R(f"R{23 + i}", x0 + 175 + i * 22, 300, "+3V3", n, "2.2k")

# ---------------------------------------------------------------- root
prj.root.text("CIRCUIT main board - schematic status\n\n"
              "Drawn (draft, from KiCad library pinouts): 2 USB-C input; 3 Haptics, buttons, debug; 4 Main MCU\n\n"
              "Not drawn yet:\n"
              "- Charger, battery, fuel gauge; 3V3 buck-boost, load switches, backlight driver;\n"
              "  secure element; NFC; BLE module - these need pinouts from datasheets (no library symbols)\n"
              "- Display and touch connectors - need the chosen panel's FPC pinout\n\n"
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
