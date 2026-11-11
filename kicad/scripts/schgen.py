"""Minimal KiCad 7 schematic writer.

Symbols and pinouts are copied verbatim from the installed KiCad symbol libraries,
never typed by hand. Every pin gets a short wire stub ending in a global label or a
power symbol, so connectivity is explicit and checkable from the exported netlist.
"""
import copy, os, uuid

SYMDIR = "/usr/share/kicad/symbols"
NS = uuid.UUID("6f1c2a2e-0c1a-4c57-9d0e-c1c0c1c0c1c0")
POWER = {"GND": ("GND", "down"), "+3V3": ("+3V3", "up"), "VBUS": ("VBUS", "up"), "+BATT": ("+BATT", "up")}


class S(str):
    """Quoted string token."""


def parse(text):
    i, n, stack, cur = 0, len(text), [], []
    while i < n:
        c = text[i]
        if c == "(":
            stack.append(cur); cur = []; i += 1
        elif c == ")":
            done = cur; cur = stack.pop(); cur.append(done); i += 1
        elif c == '"':
            j, buf = i + 1, []
            while text[j] != '"':
                if text[j] == "\\":
                    buf.append(text[j:j + 2]); j += 2
                else:
                    buf.append(text[j]); j += 1
            cur.append(S("".join(buf))); i = j + 1
        elif c.isspace():
            i += 1
        else:
            j = i
            while j < n and not text[j].isspace() and text[j] not in "()":
                j += 1
            cur.append(text[i:j]); i = j
    return cur[0]


def dump(node, ind=0):
    if isinstance(node, S):
        return '"%s"' % node
    if not isinstance(node, list):
        return str(node)
    if all(not isinstance(c, list) for c in node):
        return "(" + " ".join(dump(c) for c in node) + ")"
    pad = "\n" + "  " * (ind + 1)
    out, first = "(", True
    for c in node:
        if isinstance(c, list):
            out += pad + dump(c, ind + 1)
        else:
            out += ("" if first else " ") + dump(c)
        first = False
    return out + "\n" + "  " * ind + ")"


_libs = {}


def _lib(lib):
    if lib not in _libs:
        _libs[lib] = parse(open(os.path.join(SYMDIR, lib + ".kicad_sym")).read())
    return _libs[lib]


def load_symbol(lib, name):
    """Return a flattened (extends resolved) copy of a library symbol."""
    def find(n):
        for c in _lib(lib):
            if isinstance(c, list) and c[0] == "symbol" and c[1] == n:
                return c
        raise KeyError(f"{lib}:{n}")
    node = copy.deepcopy(find(name))
    ext = [c for c in node if isinstance(c, list) and c[0] == "extends"]
    if ext:
        parent = load_symbol(lib, str(ext[0][1]))
        pname = str(parent[1])
        own = {str(c[1]): c for c in node if isinstance(c, list) and c[0] == "property"}
        out = []
        for c in parent:
            if isinstance(c, list) and c[0] == "property":
                out.append(own.pop(str(c[1]), c))
            elif isinstance(c, list) and c[0] == "symbol":
                c[1] = S(name + str(c[1])[len(pname):]); out.append(c)
            else:
                out.append(c)
        out[1] = S(name)
        idx = max(i for i, c in enumerate(out) if isinstance(c, list) and c[0] == "property") + 1
        out[idx:idx] = list(own.values())
        node = out
    return node


def pins_of(sym):
    pins = []
    for sub in sym:
        if isinstance(sub, list) and sub[0] == "symbol":
            for p in sub:
                if isinstance(p, list) and p[0] == "pin":
                    d = {c[0]: c for c in p if isinstance(c, list)}
                    pins.append(dict(number=str(d["number"][1]), name=str(d["name"][1]), type=p[1],
                                     x=float(d["at"][1]), y=float(d["at"][2]), a=int(float(d["at"][3]))))
    return pins


def prop(sym, key):
    for c in sym:
        if isinstance(c, list) and c[0] == "property" and str(c[1]) == key:
            return str(c[2])
    return ""


def custom(name, left, right, footprint="", ref="U"):
    """Define a rectangular symbol in the project library 'circuit'. left/right: [(number, pin name), ...]."""
    rows = max(len(left), len(right))
    h = rows * 2.54 + 2.54
    w = 10.16
    top = round(h / 2 - 2.54, 2)
    def eff(): return ["effects", ["font", ["size", 1.27, 1.27]]]
    pins = []
    for side, lst in (("L", left), ("R", right)):
        for i, (num, pname) in enumerate(lst):
            y = round(top - i * 2.54, 2)
            x, a = (-w - 2.54, 0) if side == "L" else (w + 2.54, 180)
            pins.append(["pin", "passive", "line", ["at", x, y, a], ["length", 2.54],
                         ["name", S(pname), eff()], ["number", S(str(num)), eff()]])
    sym = ["symbol", S(name), ["in_bom", "yes"], ["on_board", "yes"],
           ["property", S("Reference"), S(ref), ["at", -w, h / 2 + 1.27, 0], eff()],
           ["property", S("Value"), S(name), ["at", -w, h / 2 + 3.5, 0], eff()],
           ["property", S("Footprint"), S(footprint), ["at", 0, 0, 0], eff() + ["hide"]],
           ["property", S("Datasheet"), S(""), ["at", 0, 0, 0], eff() + ["hide"]],
           ["symbol", S(name + "_0_1"), ["rectangle", ["start", -w, round(h / 2, 2)], ["end", w, round(-h / 2, 2)],
                                          ["stroke", ["width", 0.254], ["type", "default"]], ["fill", ["type", "background"]]]],
           ["symbol", S(name + "_1_1")] + pins]
    _libs.setdefault("circuit", ["kicad_symbol_lib", ["version", 20220914], ["generator", "circuit_schgen"]]).append(sym)


def write_custom_lib(outdir):
    if "circuit" in _libs:
        open(os.path.join(outdir, "circuit.kicad_sym"), "w").write(dump(_libs["circuit"]) + "\n")
        open(os.path.join(outdir, "sym-lib-table"), "w").write(
            '(sym_lib_table\n  (lib (name "circuit")(type "KiCad")(uri "${KIPRJMOD}/circuit.kicad_sym")(options "")(descr "Circuit project symbols"))\n)\n')


OUT = {0: (-1, 0, 180), 180: (1, 0, 0), 90: (0, 1, 270), 270: (0, -1, 90)}   # pin angle -> stub dx, dy, label angle
ROT = {"down": {(0, 1): 0, (1, 0): 90, (0, -1): 180, (-1, 0): 270},
       "up": {(0, -1): 0, (-1, 0): 90, (0, 1): 180, (1, 0): 270}}


def fx():
    return ["effects", ["font", ["size", 1.27, 1.27]]]


class Sheet:
    def __init__(self, name, title, page, paper="A3"):
        self.name, self.title, self.page, self.paper = name, title, page, paper
        self.uuid = str(uuid.uuid5(NS, "sheet/" + name))
        self.libsyms, self.items, self.netpins, self.npwr, self.k = {}, [], {}, 0, 0
        self.path = None   # set by Project

    def _u(self, tag=""):
        self.k += 1
        return str(uuid.uuid5(NS, f"{self.name}/{self.k}/{tag}"))

    def _use(self, lib, name):
        key = f"{lib}:{name}"
        if key not in self.libsyms:
            sym = load_symbol(lib, name)
            emb = copy.deepcopy(sym); emb[1] = S(key)
            self.libsyms[key] = (sym, emb)
        return self.libsyms[key][0]

    def text(self, s, x, y, size=1.8):
        self.items.append(["text", S(s.replace("\n", "\\n")), ["at", x, y, 0],
                           ["effects", ["font", ["size", size, size]], ["justify", "left", "top"]], ["uuid", self._u()]])

    def _instance(self, lib, name, ref, value, footprint, x, y, rot, pins, hide_ref=False):
        e = fx() + (["hide"] if hide_ref else [])
        if len(pins) > 2:    # IC or connector: text block above the body, clear of pins
            rx = round(x + min(p["x"] for p in pins) + 2.54, 2)
            ry = round(y - max(p["y"] for p in pins) - 9, 2)
        else:
            rx, ry = x + 2.54, y - 1.2
        node = ["symbol", ["lib_id", S(f"{lib}:{name}")], ["at", x, y, rot], ["unit", 1],
                ["in_bom", "yes"], ["on_board", "yes"], ["dnp", "no"], ["uuid", self._u(ref)],
                ["property", S("Reference"), S(ref), ["at", rx, ry, 0], e + [["justify", "left"]]],
                ["property", S("Value"), S(value), ["at", rx, ry + 2.2, 0], fx() + [["justify", "left"]]],
                ["property", S("Footprint"), S(footprint), ["at", x, y, 0], fx() + ["hide"]],
                ["property", S("Datasheet"), S(""), ["at", x, y, 0], fx() + ["hide"]]]
        for num in sorted({p["number"] for p in pins}):
            node.append(["pin", S(num), ["uuid", self._u(ref + num)]])
        node.append(["instances", ["project", S("circuit"), ["path", S(self.path), ["reference", S(ref)], ["unit", 1]]]])
        self.items.append(node)

    def place(self, lib, name, ref, x, y, nets, value=None, footprint=None, stub=2.54, default=None):
        """nets: {pin number or pin name: net name | 'NC'}. Every pin must be covered."""
        sym = self._use(lib, name)
        pins = pins_of(sym)
        fp = prop(sym, "Footprint") if footprint is None else footprint
        self._instance(lib, name, ref, value or name, fp, x, y, 0, pins)
        seen = set()
        for p in pins:
            net = nets.get(p["number"], nets.get(p["name"], default))
            if net is None:
                raise ValueError(f"{ref}: pin {p['number']} ({p['name']}) has no net")
            px, py = round(x + p["x"], 2), round(y - p["y"], 2)
            if net == "NC":
                self.items.append(["no_connect", ["at", px, py], ["uuid", self._u()]]); continue
            self.netpins.setdefault(net, []).append(f"{ref}.{p['number']}")
            if (px, py) in seen:      # stacked pins share one stub
                continue
            seen.add((px, py))
            dx, dy, la = OUT[p["a"]]
            ex, ey = round(px + dx * stub, 2), round(py + dy * stub, 2)
            self.items.append(["wire", ["pts", ["xy", px, py], ["xy", ex, ey]],
                               ["stroke", ["width", 0], ["type", "default"]], ["uuid", self._u()]])
            if net in POWER:
                pname, pdir = POWER[net]
                psym = self._use("power", pname)
                self.npwr += 1
                self._instance("power", pname, f"#PWR{self.page:02d}{self.npwr:02d}", pname, "",
                               ex, ey, ROT[pdir][(dx, dy)], pins_of(psym), hide_ref=True)
            else:
                self.items.append(["global_label", S(net), ["shape", "passive"], ["at", ex, ey, la],
                                   fx() + [["justify", "right" if la in (180, 270) else "left"]], ["uuid", self._u()],
                                   ["property", S("Intersheetrefs"), S("${INTERSHEET_REFS}"), ["at", 0, 0, 0],
                                    fx() + ["hide"]]])

    def R(self, ref, x, y, a, b, value, fp="Resistor_SMD:R_0402_1005Metric"):
        self.place("Device", "R", ref, x, y, {"1": a, "2": b}, value, fp)

    def C(self, ref, x, y, a, b, value, fp="Capacitor_SMD:C_0402_1005Metric"):
        self.place("Device", "C", ref, x, y, {"1": a, "2": b}, value, fp)

    def tree(self, rev):
        return ["kicad_sch", ["version", 20230121], ["generator", "eeschema"], ["uuid", self.uuid], ["paper", S(self.paper)],
                ["title_block", ["title", S(self.title)], ["rev", S(rev)],
                 ["comment", 1, S("DRAFT - generated by kicad/scripts/gen_schematic.py - not reviewed")]],
                ["lib_symbols"] + [emb for _, emb in self.libsyms.values()]] + self.items


class Project:
    def __init__(self, outdir, rev):
        self.outdir, self.rev, self.sheets = outdir, rev, []
        self.root = Sheet("root", "Circuit main board", 1)
        self.root.path = "/" + self.root.uuid

    def sheet(self, name, title, paper="A3"):
        s = Sheet(name, title, len(self.sheets) + 2, paper)
        s.path = f"/{self.root.uuid}/{s.uuid}"
        self.sheets.append(s)
        return s

    def write(self):
        r = self.root
        for i, s in enumerate(self.sheets):
            x, y = 30 + (i % 4) * 60, 110 + (i // 4) * 40
            r.items.append(["sheet", ["at", x, y], ["size", 45, 20], ["stroke", ["width", 0.15], ["type", "solid"]],
                            ["fill", ["color", 0, 0, 0, 0.0]], ["uuid", s.uuid],
                            ["property", S("Sheetname"), S(s.title), ["at", x, y - 0.7, 0], fx() + [["justify", "left", "bottom"]]],
                            ["property", S("Sheetfile"), S(s.name + ".kicad_sch"), ["at", x, y + 20.7, 0],
                             fx() + [["justify", "left", "top"]]],
                            ["instances", ["project", S("circuit"), ["path", S(r.path), ["page", S(str(s.page))]]]]])
            t = s.tree(self.rev) + [["sheet_instances", ["path", S("/"), ["page", S(str(s.page))]]]]
            open(os.path.join(self.outdir, s.name + ".kicad_sch"), "w").write(dump(t) + "\n")
        t = r.tree(self.rev) + [["sheet_instances", ["path", S("/"), ["page", S("1")]]]]
        open(os.path.join(self.outdir, "circuit.kicad_sch"), "w").write(dump(t) + "\n")

    def expected(self):
        nets = {}
        for s in self.sheets:
            for n, pins in s.netpins.items():
                nets.setdefault(n, set()).update(pins)
        return nets
