from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageChops, ImageEnhance, ImageOps
import random, math

W, H = 800, 540
FONT = "tools/fusion-pixel-12px-monospaced-zh_hans.ttf"
BG      = (8, 22, 8)
BEZEL   = (24, 30, 24)
LABEL   = (200, 255, 170)
VALUE   = (120, 245, 120)
ART     = (150, 250, 140)

LINES = [
    ("Name:",      "Zynoo"),
    ("Uptime:",    "forever, 0 reboots"),
    ("Shell:",     "zsh (47 unused plugins)"),
    ("Editor:",    "Claude Code\n(I press Enter)"),
    ("Memory:",    "99% used, 1% for names"),
    ("Languages:", "Python, TypeScript, Go,\nBash"),
    ("Skills:",    "Approve, Accept all,\nYes, Yes, Yes,\n\"it works on my agent\""),
    ("Motto:",     "念念不忘 必有回响"),
]
PALETTE = [(180,60,60),(80,200,80),(220,200,70),(70,110,220),(190,80,190),(70,190,200),(200,200,200),(100,100,100)]

# ---------- avatar -> block art ----------
def block_art(path, cols, rows):
    im = Image.open(path).convert("RGB")
    # flood-fill background from corners
    ff = im.copy(); d = ImageDraw.Draw(ff)
    for pt in [(1,1),(im.width-2,1),(1,im.height-2),(im.width-2,im.height-2)]:
        ImageDraw.floodfill(ff, pt, (255,0,255), thresh=45)
    mask = Image.new("L", im.size, 0)
    px = ff.load(); mp = mask.load()
    for y in range(im.height):
        for x in range(im.width):
            if px[x,y] == (255,0,255): mp[x,y] = 255
    gray = ImageOps.autocontrast(im.convert("L"), cutoff=2)
    edges = gray.filter(ImageFilter.FIND_EDGES).filter(ImageFilter.MaxFilter(3))
    small_gray = gray.resize((cols, rows), Image.BOX)
    small_mask = mask.resize((cols, rows), Image.BOX)
    small_edge = edges.resize((cols, rows), Image.BOX)
    g = small_gray.load(); m = small_mask.load(); e = small_edge.load()
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
    # leave 1px column gap and 2px row gap, like terminal glyphs
    for y in range(ch - 1):
        for x in range(cw - 1):
            on = (level == 4) or \
                 (level == 3 and not (x % 2 == 1 and y % 2 == 1)) or \
                 (level == 2 and (x + y) % 2 == 0) or \
                 (level == 1 and x % 2 == 0 and y % 2 == 0)
            if on: px[x0 + x, y0 + y] = color

# ---------- base frame ----------
def base(cursor_on):
    im = Image.new("RGB", (W, H), BG)
    px = im.load()
    d = ImageDraw.Draw(im)
    f18 = ImageFont.truetype(FONT, 18)

    # left: art
    CW, CH = 7, 14
    cols, rows = 60, 30
    grid = block_art("tools/avatar.png", cols, rows)
    ax, ay = 30, 36
    for y, row in enumerate(grid):
        for x, lv in enumerate(row):
            if lv: draw_cell(px, ax + x*CW, ay + y*CH, lv, CW, CH, ART)

    # right: info
    rx, ry, lh = 470, 44, 24
    for label, value in LINES:
        d.text((rx, ry), label, font=f18, fill=LABEL)
        vx = rx + 9 * 11
        for i, part in enumerate(value.split("\n")):
            d.text((vx, ry + i*lh), part, font=f18, fill=VALUE)
        ry += lh * (value.count("\n") + 1)

    # palette
    py = ry + 18
    for i, c in enumerate(PALETTE):
        d.rectangle([rx + i*26, py, rx + i*26 + 24, py + 20], fill=c)
        c2 = tuple(min(255, v + 60) for v in c)
        d.rectangle([rx + i*26, py + 22, rx + i*26 + 24, py + 30], fill=c2)

    # prompt
    prompt = "zynoo@mbp$ "
    d.text((40, H - 62), prompt, font=f18, fill=VALUE)
    if cursor_on:
        cx = 40 + d.textlength(prompt, font=f18)
        d.rectangle([cx, H - 62, cx + 9, H - 62 + 18], fill=VALUE)
    return im

# ---------- CRT post ----------
def crt(im, seed):
    rnd = random.Random(seed)
    # glow
    glow = im.filter(ImageFilter.GaussianBlur(5))
    glow = ImageEnhance.Brightness(glow).enhance(0.8)
    im = ImageChops.add(im, glow)
    # scanlines
    sl = Image.new("L", (W, H), 255); sp = sl.load()
    for y in range(H):
        v = 255 if y % 4 in (1, 2) else (140 if y % 4 == 0 else 200)
        for x in range(W): sp[x, y] = v
    im = ImageChops.multiply(im, Image.merge("RGB", (sl, sl, sl)))
    # vignette
    vg = Image.new("L", (W, H), 0)
    ImageDraw.Draw(vg).ellipse([-W*0.15, -H*0.25, W*1.15, H*1.25], fill=255)
    vg = vg.filter(ImageFilter.GaussianBlur(90))
    vg = ImageChops.add(vg, Image.new("L", (W, H), 70))
    im = ImageChops.multiply(im, Image.merge("RGB", (vg, vg, vg)))
    # flicker
    im = ImageEnhance.Brightness(im).enhance(1 + rnd.uniform(-0.03, 0.03))
    # bezel with rounded screen
    out = Image.new("RGB", (W, H), BEZEL)
    m = Image.new("L", (W, H), 0)
    ImageDraw.Draw(m).rounded_rectangle([14, 14, W-15, H-15], radius=28, fill=255)
    out.paste(im, (0, 0), m)
    return out

frames = []
for i in range(6):
    frames.append(crt(base(cursor_on=(i % 6) < 3), seed=i))
frames[0].save("assets/neofetch.gif", save_all=True, append_images=frames[1:],
               duration=180, loop=0, optimize=True)
frames[0].save("/tmp/neofetch-preview.png")
import os; print("bytes", os.path.getsize("assets/neofetch.gif"))
