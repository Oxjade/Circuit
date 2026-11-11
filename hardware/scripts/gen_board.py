#!/usr/bin/env python3
"""Generate the provisional Circuit board definition (outline, layers, holes, keep-outs).

Run: python3 scripts/gen_board.py   (needs KiCad 7 'pcbnew' Python module)
Re-running overwrites circuit/circuit.kicad_pcb. Do NOT run once routing has started.
All dimensions come from docs/phase1 estimates and are provisional until Phase 2 CAD.
"""
import math, os, pcbnew
from pcbnew import FromMM, VECTOR2I

OX, OY = 100.0, 50.0            # page offset of board top-left corner, mm
W, H = 56.0, 90.0               # board envelope, mm
TOP, BOT, STRIP = 13.0, 11.0, 17.0   # top band, bottom band, right strip, mm
FP = "/usr/share/kicad/footprints"

def P(x, y): return VECTOR2I(FromMM(OX + x), FromMM(OY + y))

board = pcbnew.BOARD()
board.SetCopperLayerCount(4)
ds = board.GetDesignSettings()
ds.SetBoardThickness(FromMM(1.0))
board.SetLayerName(pcbnew.In1_Cu, "In1.GND")
board.SetLayerName(pcbnew.In2_Cu, "In2.PWR")
tb = board.GetTitleBlock()
tb.SetTitle("Circuit main board - PROVISIONAL board definition")
tb.SetRevision("A0-draft")
tb.SetComment(0, "Outline from Phase 1 placement concept. Not for fabrication.")

def line(a, b, layer=pcbnew.Edge_Cuts, w=0.1):
    s = pcbnew.PCB_SHAPE(board); s.SetShape(pcbnew.SHAPE_T_SEGMENT)
    s.SetStart(P(*a)); s.SetEnd(P(*b)); s.SetLayer(layer); s.SetWidth(FromMM(w)); board.Add(s)

def arc(a, m, b, layer=pcbnew.Edge_Cuts, w=0.1):
    s = pcbnew.PCB_SHAPE(board); s.SetShape(pcbnew.SHAPE_T_ARC)
    s.SetArcGeometry(P(*a), P(*m), P(*b)); s.SetLayer(layer); s.SetWidth(FromMM(w)); board.Add(s)

def outline(verts):
    """Closed polygon with a fillet radius per vertex: [(x, y, r), ...]."""
    n = len(verts); pts = []
    for i, (x, y, r) in enumerate(verts):
        ax, ay, _ = verts[i - 1]; cx, cy, _ = verts[(i + 1) % n]
        u1 = ((ax - x) / math.hypot(ax - x, ay - y), (ay - y) / math.hypot(ax - x, ay - y))
        u2 = ((cx - x) / math.hypot(cx - x, cy - y), (cy - y) / math.hypot(cx - x, cy - y))
        p1 = (x + r * u1[0], y + r * u1[1]); p2 = (x + r * u2[0], y + r * u2[1])
        c = (x + r * (u1[0] + u2[0]), y + r * (u1[1] + u2[1]))
        k = r / math.sqrt(2)
        mid = (c[0] - k * (u1[0] + u2[0]), c[1] - k * (u1[1] + u2[1]))
        pts.append((p1, mid, p2))
    for i, (p1, mid, p2) in enumerate(pts):
        arc(p1, mid, p2)
        line(p2, pts[(i + 1) % n][0])

xs = W - STRIP   # left edge of right strip
outline([(0, 0, 3), (W, 0, 3), (W, H, 3), (0, H, 3),
         (0, H - BOT, 1), (xs, H - BOT, 1), (xs, TOP, 1), (0, TOP, 1)])

def place(lib, name, ref, x, y, rot=0, value=""):
    fp = pcbnew.FootprintLoad(f"{FP}/{lib}.pretty", name)
    fp.SetReference(ref); fp.SetValue(value or name)
    fp.SetPosition(P(x, y)); fp.SetOrientationDegrees(rot); board.Add(fp); return fp

# Mechanical anchors (positions provisional)
for i, (x, y) in enumerate([(4, 6.5), (W - 4, 17), (W - 4, 75), (4, H - 5.5)], 1):
    place("MountingHole", "MountingHole_2.2mm_M2", f"H{i}", x, y)
# USB-C: footprint's "PCB Edge" line is 3.67 mm below its origin
place("Connector_USB", "USB_C_Receptacle_GCT_USB4105-xx-A_16P_TopMnt_Horizontal", "J1", W / 2, H - 3.67,
      value="USB4105-GF-A (candidate)")
place("Connector", "Tag-Connect_TC2030-IDC-NL_2x03_P1.27mm_Vertical", "J2", xs + STRIP / 2, 66, value="SWD TC2030-NL")
# Fit check only: working-assumption MCU package (not selected; see gate G1)
place("Package_BGA", "TFBGA-216_13x13mm_Layout15x15_P0.8mm", "U1", xs + STRIP / 2, 40,
      value="STM32U5G9NJHxQ (fit check, not selected)")

def rule_area(name, x0, y0, x1, y1):
    z = pcbnew.ZONE(board); z.SetIsRuleArea(True); z.SetZoneName(name)
    ls = pcbnew.LSET.AllCuMask(4); z.SetLayerSet(ls)
    for f in (z.SetDoNotAllowCopperPour, z.SetDoNotAllowTracks, z.SetDoNotAllowVias): f(True)
    z.SetDoNotAllowPads(False); z.SetDoNotAllowFootprints(False)
    o = z.Outline(); o.NewOutline()
    for x, y in [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]: o.Append(FromMM(OX + x), FromMM(OY + y))
    board.Add(z)

rule_area("BLE antenna keep-out (size TBD from module drawing)", xs, 0.3, W - 0.3, 6)

def note(txt, x, y, size=1.0, layer=pcbnew.Cmts_User):
    t = pcbnew.PCB_TEXT(board); t.SetText(txt); t.SetPosition(P(x, y)); t.SetLayer(layer)
    t.SetTextSize(VECTOR2I(FromMM(size), FromMM(size))); t.SetTextThickness(FromMM(size * 0.15))
    t.SetHorizJustify(pcbnew.GR_TEXT_H_ALIGN_LEFT); board.Add(t)

note("BATTERY CUT-OUT 39 x 66 mm\n(cell ~36 x 63.5 x 5.8, provisional)", 3, 44, 1.5)
line((1.5, TOP + 1.25), (37.5, TOP + 1.25), pcbnew.Cmts_User); line((37.5, TOP + 1.25), (37.5, H - BOT - 1.25), pcbnew.Cmts_User)
line((37.5, H - BOT - 1.25), (1.5, H - BOT - 1.25), pcbnew.Cmts_User); line((1.5, H - BOT - 1.25), (1.5, TOP + 1.25), pcbnew.Cmts_User)
note("CIRCUIT main board - PROVISIONAL DEFINITION, NOT FOR FABRICATION\n"
     "4 layers, 1.0 mm: F.Cu sig / In1 GND / In2 PWR / B.Cu sig\n"
     "Outline 56 x 90 mm from Phase 1 concept; redo from Phase 2 CAD.\n"
     "No routing before schematic review (project rule 4).", 0, -9, 1.2)
note("Buttons on this edge\n(side-push, TBD)", W + 2, 30, 1.0)

out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "circuit", "circuit.kicad_pcb")
pcbnew.SaveBoard(os.path.normpath(out), board)
print("wrote", os.path.normpath(out))
