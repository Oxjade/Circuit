"""Circuit - parametric 3D concept model (Phase 2 industrial design, first pass).

Run headless:  freecadcmd build_model.py
Writes circuit.FCStd, circuit-assembly.step, STL files for the printable parts,
renders/*.png and a clearance report. All dimensions in mm.

Axes: X = width, Y = height (USB-C at Y = 0), Z = thickness (rear face at Z = 0).
Component sizes come from the Phase 1 research and are estimates until each part's
mechanical drawing has been read. Change the numbers in PARAMETERS and re-run.
"""
import os, math
import FreeCAD as App, Part
from FreeCAD import Vector as V

HERE = os.path.dirname(os.path.abspath(__file__))

# ------------------------------------------------------------------ PARAMETERS
W, H = 60.0, 94.0            # outer width, height
R_OUT = 6.0                  # outer corner radius
WALL = 2.0                   # side wall
T_REAR = 1.2                 # rear cover thickness
T_COIL = 0.4                 # NFC coil + ferrite
BAT = (36.0, 63.5, 5.8)      # Li-Po 503562 class with PCM
BAT_SWELL = 0.4
PCB = (56.0, 90.0, 1.0)      # board envelope, same as kicad/circuit.kicad_pcb
PCB_TOP, PCB_BOT, PCB_STRIP = 13.0, 11.0, 17.0
T_MID = 0.6                  # mid-plate carrying the display
LCD = (54.5, 83.0, 2.3)      # 3.5" panel body (BuyDisplay ER-TFT035IPS-6 figure)
LENS = (57.0, 91.0, 1.6)     # cover lens + touch sensor
GAP = 0.2

Z_COIL = T_REAR
Z_BAT = Z_COIL + T_COIL                       # 1.6
Z_PCB = 3.0                                   # PCB underside
Z_PCB_TOP = Z_PCB + PCB[2]                    # 4.0
Z_MID = Z_BAT + BAT[2] + BAT_SWELL            # 7.8  underside of mid-plate
Z_LCD = Z_MID + T_MID                         # 8.4
Z_LENS = Z_LCD + LCD[2]                       # 10.7
T = Z_LENS + LENS[2]                          # 12.3 total thickness
BX, BY = WALL, WALL                           # board origin in device coordinates

def bxy(x, y):
    """KiCad board coordinates (y down from top edge) -> device coordinates."""
    return BX + x, BY + PCB[1] - y

# ------------------------------------------------------------------ helpers
def rbox(x, y, z, dx, dy, dz, r=0.0):
    s = Part.makeBox(dx, dy, dz, V(x, y, z))
    if r > 0:
        edges = [e for e in s.Edges if abs(e.Vertexes[0].X - e.Vertexes[1].X) < 1e-6
                 and abs(e.Vertexes[0].Y - e.Vertexes[1].Y) < 1e-6]
        s = s.makeFillet(r, edges)
    return s

def cyl(x, y, z, r, h):
    return Part.makeCylinder(r, h, V(x, y, z))

def cbox(cx, cy, z, dx, dy, dz, r=0.0):
    return rbox(cx - dx / 2, cy - dy / 2, z, dx, dy, dz, r)

HOLES = [bxy(4, 6.5), bxy(PCB[0] - 4, 17), bxy(PCB[0] - 4, 75), bxy(4, PCB[1] - 5.5)]   # as in the KiCad board
USB_X = W / 2
BTN = {"power": (70.0, 8.0), "confirm": (47.0, 14.0)}     # centre Y, length
BTN_Z, BTN_H = Z_PCB_TOP + 0.7, 2.4

parts = {}

# ------------------------------------------------------------------ rear cover
rear = rbox(0, 0, 0, W, H, T_REAR, R_OUT)
for (x, y) in HOLES:
    rear = rear.fuse(cyl(x, y, T_REAR, 2.0, Z_PCB - T_REAR))            # stand-off under the PCB
for (x, y) in HOLES:
    rear = rear.cut(cyl(x, y, 0, 1.1, Z_PCB)).cut(cyl(x, y, 0, 2.0, 0.8))  # M2 clearance + counterbore
parts["rear_cover"] = (rear, "#3a3f47")

# ------------------------------------------------------------------ front housing (frame + mid-plate + bosses)
body = rbox(0, 0, T_REAR, W, H, T - T_REAR, R_OUT)
body = body.cut(rbox(WALL - GAP, WALL - GAP, T_REAR, PCB[0] + 2 * GAP, PCB[1] + 2 * GAP, Z_MID - T_REAR, 3.5))   # electronics bay
lx, ly = (W - LCD[0]) / 2, (H - LCD[1]) / 2
body = body.cut(rbox(lx - 0.25, ly - 0.25, Z_LCD, LCD[0] + 0.5, LCD[1] + 0.5, LCD[2], 0.5))                       # LCD pocket
body = body.cut(rbox((W - LENS[0]) / 2 - 0.1, (H - LENS[1]) / 2 - 0.1, Z_LENS, LENS[0] + 0.2, LENS[1] + 0.2, LENS[2], 4.6))  # lens ledge
body = body.cut(rbox(15, ly + LCD[1] - 4.0, Z_MID, 30, 3.0, T_MID, 0.5))                                         # display FPC slot
for (x, y) in HOLES:
    body = body.fuse(cyl(x, y, Z_PCB_TOP, 2.0, Z_MID - Z_PCB_TOP)).cut(cyl(x, y, Z_PCB_TOP, 0.8, Z_MID - Z_PCB_TOP - 0.6))
body = body.cut(rbox(USB_X - 4.7, -1, Z_PCB_TOP - 0.15, 9.4, WALL + 2, 3.6, 0))                                   # USB-C opening
for cy, ln in BTN.values():
    body = body.cut(Part.makeBox(WALL + 2, ln, BTN_H, V(W - WALL - 1, cy - ln / 2, BTN_Z - BTN_H / 2)))
parts["front_housing"] = (body, "#5b616b")

# ------------------------------------------------------------------ display stack
parts["lcd_panel"] = (rbox(lx, ly, Z_LCD, *LCD), "#1b1d21")
parts["cover_lens"] = (rbox((W - LENS[0]) / 2, (H - LENS[1]) / 2, Z_LENS, LENS[0], LENS[1], LENS[2], 4.5), "#0c1a2b")

# ------------------------------------------------------------------ PCB (C shape, as in KiCad) and components
pcb = rbox(BX, BY, Z_PCB, PCB[0], PCB[1], PCB[2], 3.0)
pcb = pcb.cut(rbox(BX - 1, BY + PCB_BOT, Z_PCB, PCB[0] - PCB_STRIP + 1, PCB[1] - PCB_TOP - PCB_BOT, PCB[2], 0))   # battery cut-out
for (x, y) in HOLES:
    pcb = pcb.cut(cyl(x, y, Z_PCB, 1.1, PCB[2]))
parts["pcb"] = (pcb, "#2f7d4f")

bat_x = BX + (PCB[0] - PCB_STRIP - BAT[0]) / 2
bat_y = BY + PCB_BOT + (PCB[1] - PCB_TOP - PCB_BOT - BAT[1]) / 2
parts["battery"] = (rbox(bat_x, bat_y, Z_BAT, *BAT, 1.0), "#c9ced6")
parts["nfc_coil_ferrite"] = (cbox(bat_x + BAT[0] / 2, bat_y + BAT[1] / 2, Z_COIL, 34, 50, T_COIL, 3.0), "#b3541e")

mx, my = bxy(PCB[0] - PCB_STRIP / 2, 32)      # clear of both side switches
parts["mcu_bga216"] = (cbox(mx, my, Z_PCB_TOP, 13, 13, 1.2), "#111111")
parts["ble_module"] = (cbox(BX + PCB[0] - 9.0, BY + PCB[1] - 6.5, Z_PCB_TOP, 15.5, 10.5, 2.05), "#bde0fe")
parts["usb_c"] = (rbox(USB_X - 4.47, 0.5, Z_PCB_TOP, 8.94, 7.35, 3.26, 0), "#adb5bd")
parts["lra"] = (cyl(17.0, 7.5, Z_PCB_TOP, 4.0, 3.2), "#cdb4db")
parts["lcd_fpc_conn"] = (cbox(20, BY + PCB[1] - 6.0, Z_PCB_TOP, 23, 5, 2.0), "#f4d35e")
parts["secure_element"] = (cbox(mx, my - 12, Z_PCB_TOP, 3, 3, 0.6), "#ffadad")
parts["charger_regulator"] = (cbox(47, 7.5, Z_PCB_TOP, 14, 7, 1.3), "#dfe7fd")
for name, (cy, ln) in BTN.items():
    parts[f"switch_{name}"] = (cbox(W - WALL - 1.45, cy, Z_PCB_TOP, 2.9, 3.5, 1.35), "#888888")
    parts[f"button_{name}"] = (Part.makeBox(2.5, ln - 0.3, BTN_H - 0.3, V(W - WALL + 0.1, cy - ln / 2 + 0.15, BTN_Z - BTN_H / 2 + 0.15)),
                               "#c1121f" if name == "confirm" else "#444444")

# ------------------------------------------------------------------ document, exports
doc = App.newDocument("Circuit")
for name, (shape, _) in parts.items():
    doc.addObject("Part::Feature", name).Shape = shape
doc.recompute()
doc.saveAs(os.path.join(HERE, "circuit.FCStd"))
Part.export(list(doc.Objects), os.path.join(HERE, "circuit-assembly.step"))
for n in ("front_housing", "rear_cover", "button_power", "button_confirm"):
    parts[n][0].exportStl(os.path.join(HERE, f"{n}.stl"))

# ------------------------------------------------------------------ clearance / interference report
names = list(parts)
lines = [f"Envelope: {W:.1f} x {H:.1f} x {T:.1f} mm", "",
         "Z stack (mm from rear face):",
         f"  rear cover        0.0 - {T_REAR:.1f}", f"  NFC coil+ferrite  {Z_COIL:.1f} - {Z_BAT:.1f}",
         f"  battery           {Z_BAT:.1f} - {Z_BAT + BAT[2]:.1f}  (+{BAT_SWELL} swell gap)",
         f"  PCB               {Z_PCB:.1f} - {Z_PCB_TOP:.1f}  (top-side clearance {Z_MID - Z_PCB_TOP:.1f}, bottom-side {Z_PCB - Z_BAT:.1f})",
         f"  mid-plate         {Z_MID:.1f} - {Z_LCD:.1f}", f"  LCD               {Z_LCD:.1f} - {Z_LENS:.1f}",
         f"  cover lens        {Z_LENS:.1f} - {T:.1f}", "", "Interference check (common volume > 0.01 mm3):"]
hits = 0
for i in range(len(names)):
    for j in range(i + 1, len(names)):
        a, b = parts[names[i]][0], parts[names[j]][0]
        if not a.BoundBox.intersect(b.BoundBox):
            continue
        v = a.common(b).Volume
        if v > 0.01:
            hits += 1
            lines.append(f"  CLASH {names[i]} / {names[j]}: {v:.2f} mm3")
if not hits:
    lines.append("  none")
lines += ["", "Volumes (cm3): " + ", ".join(f"{n} {parts[n][0].Volume / 1000:.2f}" for n in ("front_housing", "rear_cover"))]
open(os.path.join(HERE, "clearance-report.txt"), "w").write("\n".join(lines) + "\n")
print("\n".join(lines))

# ------------------------------------------------------------------ renders (own z-buffer rasteriser, no GUI needed)
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import to_rgb

def render(fname, names, elev, azim, dz=None, title="", px=9.0, size=(1000, 1250)):
    e, a = math.radians(elev), math.radians(azim)
    fwd = np.array([math.cos(e) * math.cos(a), math.cos(e) * math.sin(a), math.sin(e)])       # from scene towards camera
    right = np.cross([0, 0, 1], fwd); right = right / np.linalg.norm(right) if np.linalg.norm(right) > 1e-6 else np.array([1.0, 0, 0])
    up = np.cross(fwd, right)
    light = (0.5 * right + 0.6 * up + 0.9 * fwd); light /= np.linalg.norm(light)
    Wd, Hd = size
    img = np.ones((Hd, Wd, 3)); zb = np.full((Hd, Wd), -1e9)
    centre = np.array([W / 2, H / 2, T / 2])
    for n in names:
        shape, col = parts[n]
        vs, fs = shape.tessellate(0.15)
        P = np.array([(v.x, v.y, v.z) for v in vs]) + np.array([0, 0, (dz or {}).get(n, 0.0)]) - centre
        sx = P @ right * px + Wd / 2; sy = Hd / 2 - P @ up * px; sz = P @ fwd
        base = np.array(to_rgb(col))
        for f in fs:
            x, y, z = sx[list(f)], sy[list(f)], sz[list(f)]
            x0, x1 = max(int(x.min()), 0), min(int(x.max()) + 1, Wd - 1)
            y0, y1 = max(int(y.min()), 0), min(int(y.max()) + 1, Hd - 1)
            if x1 < x0 or y1 < y0:
                continue
            den = (y[1] - y[2]) * (x[0] - x[2]) + (x[2] - x[1]) * (y[0] - y[2])
            if abs(den) < 1e-9:
                continue
            gx, gy = np.meshgrid(np.arange(x0, x1 + 1) + 0.5, np.arange(y0, y1 + 1) + 0.5)
            l0 = ((y[1] - y[2]) * (gx - x[2]) + (x[2] - x[1]) * (gy - y[2])) / den
            l1 = ((y[2] - y[0]) * (gx - x[2]) + (x[0] - x[2]) * (gy - y[2])) / den
            l2 = 1 - l0 - l1
            zz = l0 * z[0] + l1 * z[1] + l2 * z[2]
            sub = zb[y0:y1 + 1, x0:x1 + 1]
            m = (l0 >= -1e-4) & (l1 >= -1e-4) & (l2 >= -1e-4) & (zz > sub)
            if not m.any():
                continue
            nrm = np.cross(P[f[1]] - P[f[0]], P[f[2]] - P[f[0]]); ln = np.linalg.norm(nrm)
            s = 0.35 + 0.65 * abs(float(nrm @ light) / ln) if ln else 1.0
            sub[m] = zz[m]
            img[y0:y1 + 1, x0:x1 + 1][m] = base * s
    fig = plt.figure(figsize=(Wd / 130, Hd / 130), dpi=130)
    ax = fig.add_axes([0, 0, 1, 0.95]); ax.imshow(img); ax.set_axis_off(); fig.suptitle(title, fontsize=11)
    fig.savefig(os.path.join(HERE, "renders", fname), facecolor="white"); plt.close(fig)

os.makedirs(os.path.join(HERE, "renders"), exist_ok=True)
outer = ["rear_cover", "front_housing", "cover_lens", "lcd_panel", "button_power", "button_confirm", "usb_c"]
render("front-iso.png", outer, 32, -62, title=f"Circuit concept, front. {W:.0f} x {H:.0f} x {T:.1f} mm")
render("rear-iso.png", outer, -32, -118, title="Rear")
render("front.png", outer, 90, -90, title="Front view")
render("bottom-usb.png", outer, 0, -90, title="Bottom edge (USB-C)", px=13)
render("right-buttons.png", outer, 0, 0, title="Right edge (power and confirm buttons)", px=11)
inner = [n for n in names if n not in ("front_housing", "cover_lens", "lcd_panel")]
render("internal-from-front.png", inner, 90, -90, title="Internal layout, display and front housing removed")
ex = {"cover_lens": 46, "lcd_panel": 34, "front_housing": 20, "button_power": 20, "button_confirm": 20,
      "rear_cover": -24, "nfc_coil_ferrite": -12}
render("exploded.png", names, 24, -62, dz=ex, title="Exploded view", px=6.5, size=(1000, 1500))
