# Circuit hardware (KiCad 7)

Open `circuit/circuit.kicad_pro` in KiCad 7.0 or later.

## What exists

| File | Content | State |
|---|---|---|
| `circuit/circuit.kicad_pcb` | Board definition: C-shaped 56 x 90 mm outline with battery cut-out, 4 copper layers at 1.0 mm, four M2 holes, USB-C receptacle at bottom centre, SWD pads, BLE antenna keep-out, and the working-assumption MCU package placed as a fit check | Provisional, not for fabrication |
| `circuit/circuit.kicad_sch` | Root sheet with status notes and the two sub-sheets | Draft |
| `circuit/usb.kicad_sch` | USB-C receptacle, 5.1k CC resistors, D+/D-/VBUS ESD array | Draft, not reviewed |
| `circuit/hmi.kicad_sch` | DRV2605L haptic driver and LRA pads, confirm and power buttons with debounce and ESD, SWD debug pads | Draft, not reviewed |
| `circuit/mcu.kicad_sch` | STM32U5G9NJH6Q with the full pin map (display, touch, secure element, system bus, BLE, USB, buttons, tamper, debug), decoupling, core SMPS, analog supply, reset/boot, crystals, I2C pull-ups | Draft, not reviewed; six power-pin items flagged on the sheet for datasheet confirmation |
| `schematic-draft.pdf` | PDF export of all sheets | — |
| `scripts/schgen.py`, `scripts/gen_schematic.py` | Generate the sheets from KiCad library symbols and compare the result with KiCad's exported netlist (85 nets, all match) | Stop using once sheets are hand-edited |
| `scripts/gen_board.py` | Regenerates the board definition. Do not run once routing has started; it overwrites the board | — |
| `board-definition-preview.png` | Render of the board definition | — |

## What is deliberately not here yet

- **No routing, and six of nine schematic sheets are missing.** Project rule: no PCB layout before the electrical schematic is reviewed.
- **Drawn sheets are drafts.** Pinouts come from the KiCad library; passive values are defaults that have not been checked against datasheets. No electrical rules check has been run (KiCad 7's command line has none); only connectivity was verified. Signals use global labels rather than drawn wires.
- **MCU pin functions were checked against the KiCad library's alternate-function data** (every assigned pin offers the function used; display pins match ST's STM32U5G9J-DK2). Its power-pin network (SMPS inductor and capacitors, VDD11USB, unused DSI supplies) is from memory and is flagged on the sheet.
- **Parts with no symbol in the KiCad 7 library** need symbols drawn from their datasheets, which have not been opened yet: BQ25180, TPS631000, MAX17260, TPS22916, TPS61169, NT3H2111, OPTIGA Trust M, Raytac AN54LQ-15.
- **Parts with library symbols** (pinouts vetted by the KiCad library): STM32U5G9NJHxQ, USB-C 16P receptacle, USBLC6-2SC6, TPD6S300A, DRV2605LDGS, ST25DV04K, MDBT50Q-1MV2, W25Q128JVS, TPS63900.

## Findings from the first board definition

- A 13 x 13 mm BGA leaves 2 mm each side in the 17 mm right strip. Fan-out of 216 balls will probably need a wider strip or a different PCB shape, which competes with the 36 mm wide battery inside a 56 mm board. Resolve in Phase 2.
- The USB-C footprint needs about 8.4 mm of depth from the board edge, so the bottom band is 11 mm and the top band 13 mm.
- Outline dimensions come from the Phase 1 estimate, not from enclosure CAD.
