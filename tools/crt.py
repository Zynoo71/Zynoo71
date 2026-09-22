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
QUOTA = [100, 70, 35, 0, 0, 0, 0]          # Claude weekly limit by day
COMMANDS = ["git push --force", "rm -rf node_modules", "claude --dangerously-skip-permissions"]

FPS_MS = 120
TRANSITION, HOLD = 5, 6                    # frames per day: slide, then hold

# ---------- timelines ----------
def bar_timeline():
    t = []
    for d in range(len(DAYS)):
        prev = QUOTA[d - 1] if d else QUOTA[0]
        for i in range(TRANSITION):
            t.append((d, prev + (QUOTA[d] - prev) * (i + 1) / TRANSITION))
        t += [(d, QUOTA[d])] * HOLD
    return t

def typing_timeline():
    t = []
    for cmd in COMMANDS:
        for i in range(0, len(cmd) + 1, 2):
            t.append((cmd[:i], True))
        t += [(cmd, (k // 3) % 2 == 0) for k in range(12)]
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
CW, CH, COLS, ROWS = 7, 14, 60, 30
AX, AY = 30, 36
GRID = block_art("tools/avatar.png", COLS, ROWS)

def draw_art(im):
    px = im.load()
    for y, row in enumerate(GRID):
        for x, lv in enumerate(row):
            if lv: draw_cell(px, AX + x*CW, AY + y*CH, lv, CW, CH, ART)

# ---------- right column ----------
RX, LH = 470, 24

def draw_bar(d, x, y, pct, note=""):
    seg, gap, n = 8, 1, 10
    filled = round(pct / 10)
    for i in range(n):
        c = VALUE if i < filled else (30, 60, 30)
        d.rectangle([x + i*(seg+gap), y + 4, x + i*(seg+gap) + seg - 1, y + 16], fill=c)
    tx = x + n*(seg+gap) + 8
    d.text((tx, y), f"{int(round(pct)):3d}%", font=F18, fill=VALUE)
    if note: d.text((tx + 40, y), note, font=F18, fill=DIM)

def draw_right(d, day, quota):
    # measure total height to center against art
    n_lines = sum(v.count("\n") + 1 for _, v in LINES)
    total = n_lines*LH + 12 + LH + 4*LH + 12 + 32
    art_h = ROWS * CH
    y = AY + (art_h - total) // 2
    for label, value in LINES:
        d.text((RX, y), label, font=F18, fill=LABEL)
        for i, part in enumerate(value.split("\n")):
            d.text((RX + 99, y + i*LH), part, font=F18, fill=VALUE)
        y += LH * (value.count("\n") + 1)
    y += 12
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
    d.text((RX, y), "Coffee:", font=F18, fill=LABEL);        draw_bar(d, bx, y, 100); y += LH
    d.text((RX, y), "Claude weekly:", font=F18, fill=LABEL); draw_bar(d, bx, y, quota); y += LH
    d.text((RX, y), "Productivity:", font=F18, fill=LABEL);  draw_bar(d, bx, y, min(100, quota)); y += LH
    d.text((RX + 99, y), "= min(Coffee, Claude)", font=F18, fill=DIM); y += LH
    y += 12
    for i, c in enumerate(PALETTE):
        d.rectangle([RX + i*26, y, RX + i*26 + 24, y + 20], fill=c)
        d.rectangle([RX + i*26, y + 22, RX + i*26 + 24, y + 30], fill=tuple(min(255, v + 60) for v in c))

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
N = max(len(bars), len(typing))
frames = []
for i in range(N):
    day, quota = bars[i % len(bars)]
    typed, cur = typing[i % len(typing)]
    im = Image.new("RGB", (W, H), BG)
    draw_art(im)
    d = ImageDraw.Draw(im)
    draw_right(d, day, quota)
    draw_prompt(d, typed, cur)
    frames.append(crt(im))

# weight the palette toward the colour swatches, which are tiny and would otherwise be merged into greens
pal_src = frames[0].copy()
sw = frames[0].crop((RX - 4, H - 140, RX + 8*26 + 4, H - 60)).resize((400, 300), Image.NEAREST)
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
frames[20].save("/tmp/neofetch-preview.png")
import os; print("frames", N, "bytes", os.path.getsize("assets/neofetch.gif"))
