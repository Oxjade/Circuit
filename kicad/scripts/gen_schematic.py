#!/usr/bin/env python3
"""Generate the Circuit schematic sheets that can be drawn from vetted KiCad library pinouts.

Run: python3 scripts/gen_schematic.py   (KiCad 7 libraries must be installed)
Overwrites ../*.kicad_sch. Stop using this once sheets are edited by hand in KiCad.
Component VALUES are engineering defaults and must be checked against datasheets.
"""
import os, subprocess, sys, tempfile
import schgen as g

OUT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
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
s.text("HAPTICS: DRV2605L drives an 8 mm LRA from +3V3 (kept powered; EN low gives microamp shutdown and keeps the shared I2C bus unloaded).\n"
       "R4 holds EN low while the MCU is in reset. Pin 6 (VDD/NC) left open - CHECK datasheet.\n"
       "C2/C3 values (1 uF) are defaults - CHECK datasheet.", 20, 20)
s.place("Driver_Haptic", "DRV2605LDGS", "U3", 70, 90,
        {"REG": "HAPT_REG", "VDD": "+3V3", "VDD/NC": "NC", "SCL": "I2C_SYS_SCL", "SDA": "I2C_SYS_SDA",
         "IN/TRIG": "HAPT_TRIG", "EN": "HAPT_EN", "OUT+": "LRA_P", "OUT-": "LRA_N", "GND": "GND"})
s.place("Connector_Generic", "Conn_01x02", "J3", 135, 90, {"1": "LRA_P", "2": "LRA_N"}, "LRA pads", "")
s.C("C2", 60, 135, "+3V3", "GND", "1uF")
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

s.text("TAMPER: two case-open switch positions. Closed to GND when the case is shut; pulled up to the MCU backup rail.", 170, 215)
for i in (1, 2):
    s.place("Connector_Generic", "Conn_01x02", f"J{8 + i}", 190 + (i - 1) * 60, 240, {"1": f"TAMPER_{i}", "2": "GND"}, "case switch pads", "")
    s.R(f"R{9 + i}", 215 + (i - 1) * 60, 240, "VBAT_MCU", f"TAMPER_{i}", "1M")
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
    "PC0": "I2C_SYS_SCL", "PC1": "I2C_SYS_SDA", "PB15": "CHG_STAT_N", "PC5": "CHG_PGOOD_N", "PF5": "CHG_EN1", "PF6": "CHG_EN2", "PB1": "NFC_FD",
    # BLE module (USART1, untrusted transport)
    "PG9": "BLE_UART_TX", "PG10": "BLE_UART_RX", "PG11": "BLE_UART_CTS", "PG12": "BLE_UART_RTS",
    "PG13": "BLE_RST_N", "PG14": "EN_3V3_BLE", "PB7": "BLE_WAKE",
    # USB, CC sense, battery sense
    "PA12": "USB_DP", "PA11": "USB_DM", "PC2": "USB_CC1", "PC3": "USB_CC2", "PC4": "VBAT_SENSE",
    # buttons (wake-up pins), haptics, tamper
    "PC13": "BTN_CONFIRM_N", "PA0": "BTN_POWER_N", "PF1": "HAPT_EN", "PF2": "HAPT_TRIG",
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

s.text("I2C pull-ups (touch bus pulls to the switched LCD rail so it cannot back-power the panel)", x0 + 170, 275)
for i, n in enumerate(["I2C_TP_SCL", "I2C_TP_SDA", "I2C_SE_SCL", "I2C_SE_SDA", "I2C_SYS_SCL", "I2C_SYS_SDA"]):
    s.R(f"R{23 + i}", x0 + 175 + i * 22, 300, "+3V3_LCD" if "_TP_" in n else "+3V3", n, "2.2k")

# ---------------------------------------------------------------- sheet 5: power
s = prj.sheet("power", "Battery, charger, 3V3, load switches")
s.text("POWER: USB VBUS -> BQ24075 power-path charger -> VSYS -> TPS63001 buck-boost -> +3V3 (always on).\n"
       "Load switches gate the display rail and the BLE module rail. Battery voltage is read through a 1M/1M divider.\n"
       "Defaults with the MCU unpowered: EN1 = EN2 = 0 -> 100 mA input limit (safe on any USB port). MCU raises EN1 for 500 mA,\n"
       "or EN2 for the R31 limit after reading the CC pins.\n\n"
       "VALUES FROM MEMORY OF TI DATASHEETS - CONFIRM: R30 (ISET, 890/R = 0.5 A), R31 (ILIM, 1610/R = 1.0 A), TMR left open = default\n"
       "safety timers, R32 = 10k in place of a pack NTC (use the pack's NTC if it has one), TPS63001 L2 and capacitors, CT capacitors.\n"
       "Battery connector polarity MUST be checked against the chosen cell. No VBUS over-voltage switch is fitted: BQ24075 input rating relied on.", 20, 15)
s.place("Connector_Generic", "Conn_01x02", "J4", 40, 100, {"1": "+BATT", "2": "GND"}, "Li-Po JST-PH",
        "Connector_JST:JST_PH_S2B-PH-SM4-TB_1x02-1MP_P2.00mm_Horizontal")
s.place("Battery_Management", "BQ24075RGT", "U4", 110, 100,
        {"IN": "VBUS", "OUT": "VSYS", "BAT": "+BATT", "TS": "CHG_TS", "~{CE}": "GND", "EN1": "CHG_EN1", "EN2": "CHG_EN2",
         "~{PGOOD}": "CHG_PGOOD_N", "~{CHG}": "CHG_STAT_N", "ILIM": "CHG_ILIM", "ISET": "CHG_ISET", "TMR": "NC",
         "SYSOFF": "CHG_SYSOFF", "VSS": "GND"})
y = 150
s.C("C40", 30, y, "VBUS", "GND", "1uF 25V", "Capacitor_SMD:C_0603_1608Metric")
s.C("C41", 46, y, "VSYS", "GND", "4.7uF", "Capacitor_SMD:C_0603_1608Metric")
s.C("C42", 62, y, "+BATT", "GND", "4.7uF", "Capacitor_SMD:C_0603_1608Metric")
s.R("R30", 80, y, "CHG_ISET", "GND", "1.78k 1%")
s.R("R31", 98, y, "CHG_ILIM", "GND", "1.6k 1%")
s.R("R32", 116, y, "CHG_TS", "GND", "10k 1%")
s.R("R33", 134, y, "CHG_SYSOFF", "GND", "0R")
s.R("R34", 152, y, "CHG_EN1", "GND", "100k")
s.R("R35", 170, y, "CHG_EN2", "GND", "100k")
s.R("R36", 188, y, "+3V3", "CHG_PGOOD_N", "100k")
s.R("R37", 206, y, "+3V3", "CHG_STAT_N", "100k")
s.text("3.3 V buck-boost (fixed-output TPS63001, power-save enabled)", 20, 175)
s.place("Regulator_Switching", "TPS63001", "U5", 110, 205,
        {"VIN": "VSYS", "VINA": "REG_VINA", "EN": "VSYS", "PS/SYNC": "GND", "L1": "REG_L1", "L2": "REG_L2",
         "VOUT": "+3V3", "FB": "+3V3", "GND": "GND", "PGND": "GND"})
s.place("Device", "L", "L2", 40, 205, {"1": "REG_L1", "2": "REG_L2"}, "2.2uH 1.5A", "Inductor_SMD:L_1008_2520Metric")
s.R("R38", 170, 205, "VSYS", "REG_VINA", "100R")
s.C("C43", 188, 205, "REG_VINA", "GND", "100nF")
s.C("C44", 206, 205, "VSYS", "GND", "10uF", "Capacitor_SMD:C_0603_1608Metric")
s.C("C45", 224, 205, "+3V3", "GND", "10uF", "Capacitor_SMD:C_0603_1608Metric")
s.C("C46", 242, 205, "+3V3", "GND", "10uF", "Capacitor_SMD:C_0603_1608Metric")
s.text("Load switches (off by default) and battery sense", 260, 85)
for i, (rail, en) in enumerate([("+3V3_LCD", "EN_3V3_LCD"), ("+3V3_BLE", "EN_3V3_BLE")]):
    yy = 110 + i * 55
    s.place("Power_Management", "TPS22917DBV", f"U{6 + i}", 290, yy,
            {"VIN": "+3V3", "GND": "GND", "ON": en, "CT": f"SW{i + 1}_CT", "QOD": rail, "VOUT": rail})
    s.R(f"R{39 + i}", 335, yy, en, "GND", "100k")
    s.C(f"C{47 + 2 * i}", 353, yy, f"SW{i + 1}_CT", "GND", "1nF (TBD)")
    s.C(f"C{48 + 2 * i}", 371, yy, rail, "GND", "1uF")
s.R("R41", 290, 225, "+BATT", "VBAT_SENSE", "1M 1%")
s.R("R42", 310, 225, "VBAT_SENSE", "GND", "1M 1%")
s.C("C51", 330, 225, "VBAT_SENSE", "GND", "100nF")

# ---------------------------------------------------------------- sheet 6: secure element
g.custom("OPTIGA_Trust_M_SLS32AIA010MK", [(10, "VCC"), (9, "RST"), (8, "SCL"), (3, "SDA")],
         [(1, "GND"), (2, "NC2"), (4, "NC4"), (5, "NC5"), (6, "NC6"), (7, "NC7"), (11, "EP")],
         "Package_DFN_QFN:DFN-10-1EP_3x3mm_P0.5mm_EP1.55x2.48mm")
s = prj.sheet("secure", "Secure element")
s.text("SECURE ELEMENT: Infineon OPTIGA Trust M V3 (SLS32AIA010MK, PG-USON-10 3x3 mm) on its own I2C bus.\n"
       "Holds the DWalletCap authority key, gates the storage key behind the PIN, provides device attestation and counters.\n"
       "Pin-to-pad mapping and the tying of unused pads to ground follow Adafruit's published Trust M breakout (open hardware);\n"
       "CONFIRM against the Infineon datasheet, including the footprint's exposed-pad size.\n"
       "Bus pull-ups are on the MCU sheet. SE_RST_N lets the MCU reset the part.", 20, 20)
s.place("circuit", "OPTIGA_Trust_M_SLS32AIA010MK", "U8", 120, 100,
        {"VCC": "+3V3", "RST": "SE_RST_N", "SCL": "I2C_SE_SCL", "SDA": "I2C_SE_SDA", "GND": "GND", "NC2": "GND", "NC4": "GND",
         "NC5": "GND", "NC6": "GND", "NC7": "GND", "EP": "GND"}, "OPTIGA Trust M V3")
s.C("C52", 60, 150, "+3V3", "GND", "100nF")
s.C("C53", 78, 150, "+3V3", "GND", "10uF", "Capacitor_SMD:C_0603_1608Metric")
s.R("R43", 100, 150, "+3V3", "SE_RST_N", "10k")

# ---------------------------------------------------------------- sheet 7: BLE
s = prj.sheet("ble", "BLE module")
s.text("BLE: Raytac MDBT50Q-1MV2 (nRF52840, chip antenna) used only as an untrusted serial transport.\n"
       "Chosen over the nRF54L15 module of the Phase 1 proposal because its symbol and footprint are in the reviewed KiCad library.\n"
       "Rail +3V3_BLE is switched by the MCU. Firmware must drive the UART and reset lines low or high-Z while the rail is off.\n"
       "UART pins are arbitrary nRF GPIOs (set in the module firmware). VDD and VDDH tied (normal-voltage mode), USB and DC/DC pins unused.\n"
       "J5 programs the module. Keep copper and components out of the antenna keep-out in the Raytac layout guide.", 20, 20)
blemap = {"VDD": "+3V3_BLE", "VDDH": "+3V3_BLE", "GND": "GND", "P0.08": "BLE_UART_TX", "P0.06": "BLE_UART_RX",
          "P0.05": "BLE_UART_CTS", "P0.07": "BLE_UART_RTS", "P0.18": "BLE_RST_N", "P0.13": "BLE_WAKE",
          "SWDIO": "BLE_SWDIO", "SWDCLK": "BLE_SWDCLK"}
s.place("RF_Module", "MDBT50Q-1MV2", "U9", 150, 150, blemap, default="NC")
s.C("C54", 40, 250, "+3V3_BLE", "GND", "100nF")
s.C("C55", 58, 250, "+3V3_BLE", "GND", "4.7uF", "Capacitor_SMD:C_0603_1608Metric")
s.R("R44", 80, 250, "+3V3_BLE", "BLE_RST_N", "10k")
s.place("Connector", "Conn_ARM_SWD_TagConnect_TC2030-NL", "J5", 300, 120,
        {"VCC": "+3V3_BLE", "SWDIO": "BLE_SWDIO", "~{RESET}": "BLE_RST_N", "SWCLK": "BLE_SWDCLK", "GND": "GND", "SWO": "NC"},
        "BLE SWD TC2030-NL")
s.text("Signal direction (names are from the MCU's point of view):\nBLE_UART_TX  MCU -> module P0.08\nBLE_UART_RX  module P0.06 -> MCU\n"
       "BLE_UART_RTS MCU -> module P0.07\nBLE_UART_CTS module P0.05 -> MCU\nBLE_WAKE     module P0.13 -> MCU wake-up pin", 280, 170)

# ---------------------------------------------------------------- sheet 8: NFC
s = prj.sheet("nfc", "NFC tag and antenna")
s.text("NFC: ST25DV04K dynamic tag (ISO 15693 / NFC Type 5), I2C on the system bus. The phone is the reader.\n"
       "Chosen over NTAG I2C plus because its symbol is in the reviewed KiCad library; ST25DV04KC is the current revision - confirm pin compatibility.\n"
       "Powered from +3V3 (not switched) so it never loads the shared I2C bus. GPO is open-drain -> NFC_FD wakes the MCU on RF field.\n"
       "Antenna: FPC coil on the rear cover with ferrite, connected at J6. C56 is a tuning position, fitted only after measuring in the enclosure.\n"
       "No secrets are ever written to this tag: it carries a signed pairing payload only.", 20, 20)
s.place("RF_NFC", "ST25DV04K-IER8C3", "U10", 130, 110,
        {"VCC": "+3V3", "VSS": "GND", "SDA": "I2C_SYS_SDA", "SCL": "I2C_SYS_SCL", "GPO": "NFC_FD", "V_EH": "NC",
         "AC0": "NFC_ANT_A", "AC1": "NFC_ANT_B", "NC": "NC"})
s.place("Connector_Generic", "Conn_01x02", "J6", 220, 110, {"1": "NFC_ANT_A", "2": "NFC_ANT_B"}, "NFC coil pads", "")
s.C("C56", 60, 160, "NFC_ANT_A", "NFC_ANT_B", "DNP (tune)")
s.C("C57", 80, 160, "+3V3", "GND", "100nF")
s.R("R45", 100, 160, "+3V3", "NFC_FD", "100k")

# ---------------------------------------------------------------- sheet 9: display, touch, backlight
s = prj.sheet("display", "Display, touch, backlight")
s.text("DISPLAY: 3.5 in IPS 320x480 driven as RGB565 from the MCU's LTDC, with SPI for controller set-up.\n"
       "!! J7 and J8 PIN ORDER IS A PLACEHOLDER. No panel datasheet could be opened. The signal SET is complete; the ORDER must be\n"
       "   re-mapped to the purchased panel's FPC pinout (and connector pin count / top-bottom contact) before layout.\n"
       "   Unused low-order colour bits and interface-select (IM) straps are panel-specific and not shown.\n"
       "BACKLIGHT: TPS61165 boost assumes the panel's LEDs are one SERIES string (R46 = 200 mV / I_LED -> 20 mA). If the panel's LEDs\n"
       "   are in parallel this circuit is wrong and is replaced by a low-side PWM switch. Values from memory - confirm.", 20, 15)
order = (["GND", "LCD_LED_K", "LCD_LED_A", "+3V3_LCD", "+3V3_LCD", "LCD_RST", "LCD_SPI_CS", "LCD_SPI_SCK", "LCD_DC",
          "LCD_SPI_MOSI", "LCD_TE", "LCD_CLK", "LCD_DE", "LCD_HSYNC", "LCD_VSYNC", "GND"]
         + [f"LCD_R{i}" for i in range(3, 8)] + [f"LCD_G{i}" for i in range(2, 8)] + [f"LCD_B{i}" for i in range(3, 8)]
         + ["GND"] + ["NC"] * 6 + ["GND"])
assert len(order) == 40
s.place("Connector_Generic", "Conn_01x40", "J7", 330, 140, {str(i + 1): n for i, n in enumerate(order)},
        "LCD FPC 40P 0.5mm (PINOUT TBD)", "Connector_FFC-FPC:Hirose_FH12-40S-0.5SH_1x40-1MP_P0.50mm_Horizontal")
s.place("Connector_Generic", "Conn_01x06", "J8", 330, 230,
        {"1": "+3V3_LCD", "2": "GND", "3": "I2C_TP_SCL", "4": "I2C_TP_SDA", "5": "TP_INT_N", "6": "TP_RST_N"},
        "Touch FPC 6P 0.5mm (PINOUT TBD)", "Connector_FFC-FPC:Hirose_FH12-6S-0.5SH_1x06-1MP_P0.50mm_Horizontal")
s.place("Driver_LED", "TPS61165DBV", "U11", 110, 110,
        {"VIN": "VSYS", "CTRL": "LCD_BL_PWM", "SW": "BL_SW", "GND": "GND", "COMP": "BL_COMP", "FB": "LCD_LED_K"})
s.place("Device", "L", "L3", 40, 110, {"1": "VSYS", "2": "BL_SW"}, "10uH 0.5A", "Inductor_SMD:L_1008_2520Metric")
s.place("Device", "D_Schottky", "D3", 175, 110, {"A": "BL_SW", "K": "LCD_LED_A"}, "40V 0.5A", "Diode_SMD:D_SOD-123")
s.C("C58", 40, 160, "VSYS", "GND", "1uF")
s.C("C59", 58, 160, "LCD_LED_A", "GND", "1uF 50V", "Capacitor_SMD:C_0603_1608Metric")
s.C("C60", 76, 160, "BL_COMP", "GND", "220nF")
s.R("R46", 96, 160, "LCD_LED_K", "GND", "10R 1%")
s.R("R47", 116, 160, "LCD_BL_PWM", "GND", "100k")
s.C("C61", 136, 160, "+3V3_LCD", "GND", "1uF")
s.R("R48", 156, 160, "+3V3_LCD", "TP_INT_N", "10k")
s.R("R49", 176, 160, "+3V3_LCD", "TP_RST_N", "10k")

# ---------------------------------------------------------------- root
prj.root.text("CIRCUIT main board - schematic status\n\n"
              "All nine sheets are drawn as DRAFTS. Each sheet lists, in its header note, what is from memory and must be confirmed.\n\n"
              "Biggest open items: display FPC pin order (placeholder), MCU power-pin network, charger and regulator values,\n"
              "backlight LED topology. Nothing here has been through an electrical rules check or a human review.\n\n"
              "Signals between sheets use global labels. No routing before this schematic is complete and reviewed.", 30, 30, 2.2)
prj.write()
g.write_custom_lib(OUT)

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
