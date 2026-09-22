from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageChops, ImageEnhance, ImageOps

W, H = 800, 540
FONT = "tools/fusion-pixel-12px-monospaced-zh_hans.ttf"
BG    = (8, 22, 8)
BEZEL = (24, 30, 24)
LABEL = (200, 255, 170)
VALUE = (120, 245, 120)
DIM   = (60, 130, 60)
ART   = (150, 250, 140)

LINES = [
    ("Name:",      "Zynoo"),
    ("Uptime:",    "forever, 0 reboots"),
    ("Shell:",     "zsh (47 unused plugins)"),
    ("Memory:",    "99% used, 1% for names"),
    ("Languages:", "Python, TS, Go, Bash"),
    ("Skills:",    "Approve, Accept all,\nYes, Yes, Yes"),
    ("Motto:",     "while (true) {\n  believe();\n}"),
]
PALETTE = [(180,60,60),(80,200,80),(220,200,70),(70,110,220),(190,80,190),(70,190,200),(200,200,200),(100,100,100)]

DAYS  = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
# weekly quota at the END of each day; tools are consumed in rotation, one per day
CLAUDE = [60,  60,  60,  0,  0,  0, 0]
CODEX  = [100, 60,  60, 60,  0,  0, 0]
GROK   = [100, 100, 60, 60, 60,  0, 0]
COMMANDS = ["claude --dangerously-skip-permissions",
            "codex --dangerously-bypass-approvals-and-sandbox",
            "grok --permission-mode bypassPermissions"]

FPS_MS = 120
TRANSITION, HOLD = 5, 6                    # frames per day: slide, then hold

# ---------- timelines ----------
def bar_timeline():
    """Per frame: (day, claude, codex, grok, productivity). Quota drains across the day."""
    t = []
    per_day = TRANSITION + HOLD
    for d in range(len(DAYS)):
        start = [q[d-1] if d else 100 for q in (CLAUDE, CODEX, GROK)]
        end   = [q[d] for q in (CLAUDE, CODEX, GROK)]
        for k in range(per_day):
            f = k / (per_day - 1)
            cl, cx, gk = [a + (b - a) * f for a, b in zip(start, end)]
            prod = 100 if max(cl, cx, gk) > 0 else 0
            t.append((d, cl, cx, gk, prod))
    return t

def typing_timeline():
    t = []
    for cmd in COMMANDS:
        for i in range(0, len(cmd) + 3, 3):
            t.append((cmd[:i], True))
        t += [(cmd, (k // 3) % 2 == 0) for k in range(8)]
        t.append(("", True))
    return t

# ---------- avatar -> block art ----------
def block_art(path, cols, rows):
    im = Image.open(path).convert("RGB")
    ff = im.copy()
    for pt in [(1,1),(im.width-2,1),(1,im.height-2),(im.width-2,im.height-2)]:
        ImageDraw.floodfill(ff, pt, (255,0,255), thresh=45)
    mask = Image.new("L", im.size, 0)
    px = ff.load(); mp = mask.load()
    for y in range(im.height):
        for x in range(im.width):
            if px[x,y] == (255,0,255): mp[x,y] = 255
    gray = ImageOps.autocontrast(im.convert("L"), cutoff=2)
    edges = gray.filter(ImageFilter.FIND_EDGES).filter(ImageFilter.MaxFilter(3))
    g = gray.resize((cols, rows), Image.BOX).load()
    m = mask.resize((cols, rows), Image.BOX).load()
    e = edges.resize((cols, rows), Image.BOX).load()
    grid = []
    for y in range(rows):
        row = []
        for x in range(cols):
            if m[x,y] > 128: row.append(0); continue
            L = g[x,y]
            lv = 4 if L > 200 else 3 if L > 150 else 2 if L > 90 else 1
            if e[x,y] > 110: lv = max(1, lv - 1)
            row.append(lv)
        grid.append(row)
    return grid

def draw_cell(px, x0, y0, level, cw, ch, color):
    for y in range(ch - 1):
        for x in range(cw - 1):
            on = (level == 4) or \
                 (level == 3 and not (x % 2 == 1 and y % 2 == 1)) or \
                 (level == 2 and (x + y) % 2 == 0) or \
                 (level == 1 and x % 2 == 0 and y % 2 == 0)
            if on: px[x0 + x, y0 + y] = color

# ---------- static layer (art) ----------
CW, CH, COLS, ROWS = 5, 10, 84, 42
AX, AY = 30, 36
GRID = block_art("tools/avatar.png", COLS, ROWS)

# sunglasses lenses as ellipses in grid cells: (cx, cy, rx, ry)
LENSES = [(26.5, 17.5, 3.5, 2.3), (41.0, 18.0, 6.5, 2.8)]
GLINT_START, GLINT_IN, GLINT_HOLD, GLINT_OUT = 6 * (TRANSITION + HOLD), 3, 5, 3   # fires when Sunday begins: all quota gone

def lens_cells():
    cells = []
    for cx, cy, rx, ry in LENSES:
        for y in range(int(cy - ry), int(cy + ry) + 2):
            for x in range(int(cx - rx), int(cx + rx) + 2):
                if ((x - cx) / rx) ** 2 + ((y - cy) / ry) ** 2 <= 1:
                    cells.append((x, y))
    return cells
LENS = lens_cells()
_d = [x + y for x, y in LENS]; D0, D1 = min(_d), max(_d)

def glint_levels(frame):
    """Conan-style flash: diagonal sweep in, hold bright, sweep out. Returns {cell: level} or {}."""
    t = frame - GLINT_START
    if not (0 <= t < GLINT_IN + GLINT_HOLD + GLINT_OUT): return {}
    out = {}
    for x, y in LENS:
        pos = (x + y - D0) / max(1, D1 - D0)
        if t < GLINT_IN:                 lit = pos <= (t + 1) / GLINT_IN
        elif t < GLINT_IN + GLINT_HOLD:  lit = True
        else:                            lit = pos >= (t - GLINT_IN - GLINT_HOLD + 1) / GLINT_OUT
        if lit:
            # one thin unlit diagonal line keeps it reading as a reflection, not a blank patch
            out[(x, y)] = 2 if abs(pos - 0.62) < 0.05 else 4
    return out

def draw_art(im, frame=0):
    px = im.load()
    g = glint_levels(frame)
    for y, row in enumerate(GRID):
        for x, lv in enumerate(row):
            lv = g.get((x, y), lv)
            if lv: draw_cell(px, AX + x*CW, AY + y*CH, lv, CW, CH, ART)

# ---------- right column ----------
RX, LH = 470, 22

def draw_bar(d, x, y, pct, note=""):
    seg, gap, n = 8, 1, 10
    filled = round(pct / 10)
    for i in range(n):
        c = VALUE if i < filled else (30, 60, 30)
        d.rectangle([x + i*(seg+gap), y + 4, x + i*(seg+gap) + seg - 1, y + 16], fill=c)
    tx = x + n*(seg+gap) + 8
    d.text((tx, y), f"{int(round(pct)):3d}%", font=F18, fill=VALUE)
    if note: d.text((tx + 40, y), note, font=F18, fill=DIM)

def draw_right(d, day, claude, codex, grok, prod):
    # measure total height to center against art
    n_lines = sum(v.count("\n") + 1 for _, v in LINES)
    total = n_lines*LH + 10 + LH + 5*LH + 10 + 14
    art_h = ROWS * CH
    y = AY + (art_h - total) // 2
    for label, value in LINES:
        d.text((RX, y), label, font=F18, fill=LABEL)
        for i, part in enumerate(value.split("\n")):
            d.text((RX + 99, y + i*LH), part, font=F18, fill=VALUE)
        y += LH * (value.count("\n") + 1)
    y += 10
    # week strip
    x = RX
    for i, name in enumerate(DAYS):
        cur = i == day
        d.text((x, y), name, font=F18, fill=LABEL if cur else DIM)
        if cur: d.line([x, y + 20, x + 27, y + 20], fill=LABEL, width=2)
        x += 40
    y += LH
    # bars
    bx = RX + 135
    d.text((RX, y), "Claude weekly:", font=F18, fill=LABEL); draw_bar(d, bx, y, claude); y += LH
    d.text((RX, y), "Codex weekly:", font=F18, fill=LABEL);  draw_bar(d, bx, y, codex);  y += LH
    d.text((RX, y), "Grok weekly:", font=F18, fill=LABEL);   draw_bar(d, bx, y, grok);   y += LH
    d.text((RX, y), "Productivity:", font=F18, fill=LABEL);  draw_bar(d, bx, y, prod);   y += LH
    d.text((RX, y), "= any(quota) ? 100 : 0", font=F18, fill=DIM); y += LH
    y += 10
    for i, c in enumerate(PALETTE):
        d.rectangle([RX + i*26, y, RX + i*26 + 24, y + 12], fill=c)

def draw_prompt(d, typed, cursor_on):
    prompt = "zynoo@mbp$ " + typed
    d.text((40, H - 62), prompt, font=F18, fill=VALUE)
    if cursor_on:
        cx = 40 + d.textlength(prompt, font=F18)
        d.rectangle([cx, H - 62, cx + 9, H - 62 + 18], fill=VALUE)

# ---------- CRT post (deterministic, so frames diff cleanly) ----------
def make_layer(kind):
    if kind == "scan":
        sl = Image.new("L", (W, H), 255); sp = sl.load()
        for y in range(H):
            v = 255 if y % 4 in (1, 2) else (140 if y % 4 == 0 else 200)
            for x in range(W): sp[x, y] = v
        return Image.merge("RGB", (sl, sl, sl))
    vg = Image.new("L", (W, H), 0)
    ImageDraw.Draw(vg).ellipse([-W*0.15, -H*0.25, W*1.15, H*1.25], fill=255)
    vg = vg.filter(ImageFilter.GaussianBlur(90))
    vg = ImageChops.add(vg, Image.new("L", (W, H), 70))
    return Image.merge("RGB", (vg, vg, vg))

SCAN, VIG = make_layer("scan"), make_layer("vig")
MASK = Image.new("L", (W, H), 0)
ImageDraw.Draw(MASK).rounded_rectangle([14, 14, W-15, H-15], radius=28, fill=255)

def crt(im):
    glow = ImageEnhance.Brightness(im.filter(ImageFilter.GaussianBlur(5))).enhance(0.8)
    im = ImageChops.add(im, glow)
    im = ImageChops.multiply(im, SCAN)
    im = ImageChops.multiply(im, VIG)
    out = Image.new("RGB", (W, H), BEZEL)
    out.paste(im, (0, 0), MASK)
    return out

# ---------- render ----------
F18 = ImageFont.truetype(FONT, 18)
bars, typing = bar_timeline(), typing_timeline()
N = len(bars)                       # one loop = one week; prompt idles if it finishes early
assert len(typing) <= N, f"typing timeline {len(typing)} > week {N}"
typing += [("", (k // 3) % 2 == 0) for k in range(N - len(typing))]
frames = []
for i in range(N):
    day, claude, codex, grok, prod = bars[i % len(bars)]
    typed, cur = typing[i]
    im = Image.new("RGB", (W, H), BG)
    draw_art(im, i)
    d = ImageDraw.Draw(im)
    draw_right(d, day, claude, codex, grok, prod)
    draw_prompt(d, typed, cur)
    frames.append(crt(im))

# weight the palette toward the colour swatches, which are tiny and would otherwise be merged into greens
pal_src = frames[0].copy()
sw = frames[0].crop((RX - 4, H - 110, RX + 8*26 + 4, H - 60)).resize((400, 300), Image.NEAREST)
pal_src.paste(sw, (AX, AY))
pal = pal_src.quantize(colors=255, method=Image.Quantize.MEDIANCUT)
q = [f.quantize(palette=pal, dither=Image.Dither.NONE) for f in frames]
out = [q[0]]
for prev, cur in zip(q, q[1:]):
    diff = ImageChops.difference(prev.convert("RGB"), cur.convert("RGB")).convert("L").point(lambda v: 255 if v else 0)
    fr = cur.copy()
    fr.paste(255, mask=ImageChops.invert(diff))   # unchanged -> transparent index
    out.append(fr)
out[0].save("assets/neofetch.gif", save_all=True, append_images=out[1:],
            duration=FPS_MS, loop=0, transparency=255, disposal=1, optimize=False)
frames[16].save("/tmp/neofetch-preview.png"); frames[GLINT_START + GLINT_IN + 2].save("/tmp/neofetch-glint.png")
import os; print("frames", N, "bytes", os.path.getsize("assets/neofetch.gif"))
