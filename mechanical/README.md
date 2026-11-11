# Circuit mechanical model (FreeCAD)

Phase 2 industrial design, first pass. Open `circuit.FCStd` in FreeCAD 1.0 or later.

## Envelope

**60.0 x 94.0 x 12.3 mm**, 6 mm corner radius. USB-C on the bottom edge, both buttons on the right edge, NFC tap area on the rear.

| Layer (from rear face) | Z range, mm |
|---|---|
| Rear cover | 0.0 – 1.2 |
| NFC coil + ferrite | 1.2 – 1.6 |
| Battery (plus 0.4 swell gap) | 1.6 – 7.4 |
| PCB, beside the battery | 3.0 – 4.0 (3.8 clear above, 1.4 below) |
| Mid-plate carrying the display | 7.8 – 8.4 |
| LCD panel | 8.4 – 10.7 |
| Cover lens + touch sensor | 10.7 – 12.3 |

## Files

| File | Content |
|---|---|
| `build_model.py` | Parametric source. Edit the PARAMETERS block and run `freecadcmd build_model.py` to regenerate everything below |
| `circuit.FCStd` | FreeCAD document, 19 named solids |
| `circuit-assembly.step` | Whole assembly for other CAD tools |
| `front_housing.stl`, `rear_cover.stl`, `button_power.stl`, `button_confirm.stl` | Printable parts |
| `clearance-report.txt` | Z stack and the automatic interference check (currently: none) |
| `renders/` | Front, rear, edge, internal and exploded views |

## Parts in the model

- **Front housing:** one piece with 2 mm walls, a 0.6 mm mid-plate, an LCD pocket, a lens ledge, a slot for the display flex, USB-C and button openings, and four screw bosses.
- **Rear cover:** 1.2 mm plate with four stand-offs. Four M2 screws from the rear pass through the cover and the PCB into the bosses, so one set of screws clamps everything and the unit can be reopened.
- **PCB:** the same C-shaped 56 x 90 mm outline and hole positions as `kicad/circuit.kicad_pcb`.
- **Placeholders for:** battery, NFC coil, LCD, cover lens, processor, BLE module, USB-C receptacle, LRA, display connector, secure element, charger area, two side switches and their button caps.

## What this pass found

- The processor had to move 8 mm up the board to clear the confirm switch; the KiCad board file was updated to match.
- The LRA cannot sit in the bottom-left corner because of the screw boss; it moved to x = 17 mm.
- The 17 mm PCB strip beside the battery is the tightest area: a 13 mm processor package plus a 2.9 mm side switch leaves little room for routing.

## Limits of this model

- Component sizes are the Phase 1 research figures, not dimensions read from mechanical drawings. The LCD and cover-lens sizes in particular depend on the panel that is actually bought.
- Button caps have no retention flange, the lens has no adhesive gap, and there are no snap fits, ribs, draft angles, light pipes or gaskets. It is a fit-and-layout model, not a tooling design.
- The file carries no colours (they cannot be saved without the FreeCAD GUI); the renders are produced by the script.
- The interference check covers the solids in the model only. Small parts and the underside of the PCB are not modelled.
