# Circuit hardware (KiCad 7)

Open `circuit/circuit.kicad_pro` in KiCad 7.0 or later.

## What exists

| File | Content | State |
|---|---|---|
| `circuit/circuit.kicad_pcb` | Board definition: C-shaped 56 x 90 mm outline with battery cut-out, 4 copper layers at 1.0 mm, four M2 holes, USB-C receptacle at bottom centre, SWD pads, BLE antenna keep-out, and the working-assumption MCU package placed as a fit check | Provisional, not for fabrication |
| `circuit/circuit.kicad_sch` | Root sheet listing the planned sheet structure | Capture not started |
| `scripts/gen_board.py` | Regenerates the board definition. Do not run once routing has started; it overwrites the board | — |
| `board-definition-preview.png` | Render of the board definition | — |

## What is deliberately not here yet

- **No schematic sheets and no routing.** Project rule: no PCB layout before the electrical schematic is reviewed.
- **MCU sheet is blocked on gate G1** (Ika user-side crypto benchmark). The TFBGA-216 footprint on the board is a size check only.
- **Parts with no symbol in the KiCad 7 library** need symbols drawn from their datasheets, which have not been opened yet: BQ25180, TPS631000, MAX17260, TPS22916, TPS61169, NT3H2111, OPTIGA Trust M, Raytac AN54LQ-15.
- **Parts with library symbols** (pinouts vetted by the KiCad library): STM32U5G9NJHxQ, USB-C 16P receptacle, USBLC6-2SC6, TPD6S300A, DRV2605LDGS, ST25DV04K, MDBT50Q-1MV2, W25Q128JVS, TPS63900.

## Findings from the first board definition

- A 13 x 13 mm BGA leaves 2 mm each side in the 17 mm right strip. Fan-out of 216 balls will probably need a wider strip or a different PCB shape, which competes with the 36 mm wide battery inside a 56 mm board. Resolve in Phase 2.
- The USB-C footprint needs about 8.4 mm of depth from the board edge, so the bottom band is 11 mm and the top band 13 mm.
- Outline dimensions come from the Phase 1 estimate, not from enclosure CAD.
