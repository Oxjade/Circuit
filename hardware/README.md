# Circuit hardware (KiCad 7)

Open `circuit/circuit.kicad_pro` in KiCad 7.0 or later.

## What exists

| File | Content | State |
|---|---|---|
| `circuit/circuit.kicad_sch` + 8 sub-sheets | Complete draft schematic, 127 parts, 105 nets | Draft, not reviewed |
| `schematic-draft.pdf` | PDF of all nine sheets | — |
| `bom-draft.csv` | Parts list grouped by value and footprint | Draft |
| `circuit/circuit.kicad_sym` | Project symbol library (OPTIGA Trust M) | — |
| `circuit/circuit.kicad_pcb` | Board definition only: outline, layers, holes, USB-C, debug pads, MCU fit check | Provisional. Not yet synchronised with the schematic. No routing |
| `scripts/` | `gen_schematic.py` + `schgen.py` build the sheets from library symbols and check them against KiCad's netlist export; `gen_board.py` builds the board definition | Stop using a generator once its output is hand-edited |

## Sheets and parts as drawn

| Sheet | Main parts | Source of pin data |
|---|---|---|
| USB-C input | 16-pin USB-C receptacle, 2 x 5.1k CC resistors, USBLC6-2SC6 | KiCad library |
| Power | BQ24075 power-path charger, TPS63001 3.3 V buck-boost, 2 x TPS22917 load switches (display, BLE), battery divider | KiCad library |
| Main MCU | STM32U5G9NJH6Q, decoupling, core SMPS, crystals, I2C pull-ups | KiCad library, pin functions checked against its alternate-function data |
| Secure element | Infineon OPTIGA Trust M V3 | Adafruit's open-hardware Trust M breakout (pin-to-pad map) |
| BLE | Raytac MDBT50Q-1MV2 (nRF52840), programming pads | KiCad library |
| NFC | ST25DV04K dynamic tag, coil pads, tuning position | KiCad library |
| Display, touch, backlight | 40-pin and 6-pin FPC connectors, TPS61165 LED boost driver | Connector pin ORDER is a placeholder; driver from KiCad library |
| Haptics, buttons, debug | DRV2605L, LRA pads, 2 buttons, 2 tamper switch positions, SWD pads | KiCad library |

Parts that differ from the Phase 1 proposal, chosen because verified pin data was reachable: BQ24075 (was BQ25180), TPS63001 (was TPS631000), MDBT50Q-1MV2 (was the nRF54L15 module), ST25DV04K (was NTAG I2C plus), no fuel-gauge IC (ADC divider, as Keystone 3 does). The haptic driver and NFC tag are powered from the always-on rail so they cannot load the shared I2C bus when off.

## What must be fixed or confirmed before any board is ordered

1. **Display connector pin order is a placeholder.** It must be re-mapped to the purchased panel's FPC pinout, including pin count and contact side.
2. **Backlight circuit assumes series LEDs.** Panel-dependent.
3. **MCU power pins:** SMPS inductor and capacitors, VDD11USB, unused DSI supplies, VBAT. Listed on the MCU sheet.
4. **Charger and regulator values** (charge-current, input-limit and timer settings, inductor, capacitors) are from memory of the TI datasheets.
5. **OPTIGA pin mapping** comes from a third-party board, not the Infineon datasheet.
6. **Battery connector polarity** against the chosen cell; NTC handling.
7. **No VBUS over-voltage switch and no dedicated CC protection** are fitted.
8. **Eight parts have no footprint yet:** buttons, button ESD diodes, LRA pads, NFC coil pads, tamper switch pads.
9. **No electrical rules check has been run** (KiCad 7's command line has none). Only connectivity was verified: each net contains exactly the pins intended, there are no duplicate references and no single-ended signals.
10. **No human has reviewed any sheet.**

## Findings from the first board definition

- A 13 x 13 mm BGA leaves 2 mm each side in the 17 mm right strip. Fan-out of 216 balls will probably need a wider strip or a different PCB shape, which competes with the 36 mm wide battery inside a 56 mm board. Resolve in Phase 2.
- The USB-C footprint needs about 8.4 mm of depth from the board edge, so the bottom band is 11 mm and the top band 13 mm.
- Outline dimensions come from the Phase 1 estimate, not from enclosure CAD.
