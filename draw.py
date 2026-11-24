#!/usr/bin/env python3
"""draw.py — renderer for the news-image-20261124 entry (Hunter Office, Kirana).

Renders a 1024x1024 broadsheet front page ("THE WORLD — Tuesday, 24 November
2026") with PIL, from the verified 24 Nov 2026 story list in stories.json
(43 stories, 6 regions). The PNG is committed beside this script; main.ts
only copies it to /output/entry.png.

Written from scratch in this session. My own layout: red-rule kicker,
masthead with fact ears, region strip, lead hero full-width (AWACS, halftone
engraving) over two stacked secondary heroes, pull quote, pinned world map
beside a framed numbers table, fold line, Inside-Today / Quote-of-the-Day /
Tomorrow boxes, three brief columns (28 stories), two rows of six illustrated
mini-cards (12 cards, every Top 10 story illustrated), a CLAIMS-NOT-FACTS
band, UTC timeline, dark ticker strip, DATE CHECK box, footer. 43 stories,
15 illustration elements.

Run:  python3 draw.py [out.png]     (default: entry.png next to this script)
Fonts are render-time tools only (system Noto); they are NOT part of the
entry. Output is deterministic: same bytes every run. Set DRAW_LOG=1 to
write boxes.json (text-box log for verify.py overlap checks).
"""

import json
import os
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

W, H = 1024, 1024
BASE = Path(__file__).resolve().parent
DATA = json.loads((BASE / "stories.json").read_text())
STORIES = {s["n"]: s for s in DATA["stories"]}
HEROES = DATA["heroes"]
CARDS = DATA["cards"]

# ---------------------------------------------------------------- palette
PAPER = (250, 246, 236)      # warm newsprint
INK = (18, 18, 18)           # near-black text
NAVY = (24, 38, 68)          # dark bands
NAVY_SOFT = (38, 58, 100)
RED = (179, 38, 30)          # ONE spot colour (#B3261E)
RED_SOFT = (252, 234, 234)   # date-check fill
RULE = (122, 112, 92)        # hairline rules
SEA = (211, 224, 235)        # map sea
LAND = (231, 221, 190)       # map land
LAND_EDGE = (168, 156, 118)
GREY = (88, 86, 80)          # secondary text
PANEL = (243, 238, 222)      # hero/card panel background
WHITE = (255, 255, 255)
GREEN = (28, 110, 60)        # market green (charts only)
SKY = (198, 220, 238)        # hero sky

REGION_COLOURS = {
    "EU": (46, 80, 140), "AS": (156, 84, 20), "ME": (140, 40, 40),
    "AM": (32, 110, 70), "AF": (110, 70, 140), "OC": (20, 120, 130),
    "WD": (70, 70, 70),
}
REGION_NAMES = {
    "EU": "EUROPE", "AS": "ASIA", "ME": "MIDDLE EAST", "AM": "AMERICAS",
    "AF": "AFRICA", "OC": "OCEANIA", "WD": "WORLD",
}

# ---------------------------------------------------------------- fonts
NOTO = "/usr/share/fonts/truetype/noto/"
FONT_FILES = {
    "display_black": "NotoSerifDisplay-Black.ttf",
    "display_bold": "NotoSerifDisplay-Bold.ttf",
    "serif_bold": "NotoSerif-Bold.ttf",
    "serif": "NotoSerif-Regular.ttf",
    "serif_italic": "NotoSerif-Italic.ttf",
    "sans_bold": "NotoSans-Bold.ttf",
    "sans": "NotoSans-Regular.ttf",
    "mono_bold": "NotoSansMono-Bold.ttf",
    "mono": "NotoSansMono-Regular.ttf",
}
_font_cache = {}


def F(name, size):
    """Cached font loader; fails loudly if a font is missing."""
    key = (name, size)
    if key not in _font_cache:
        path = os.path.join(NOTO, FONT_FILES[name])
        _font_cache[key] = ImageFont.truetype(path, size)
    return _font_cache[key]


# ---------------------------------------------------------------- text log
BOXES = []


def log_box(x0, y0, x1, y1, label):
    BOXES.append([round(x0), round(y0), round(x1), round(y1), label])


def tw(d, s, font):
    return d.textlength(s, font=font)


def wrap(d, s, font, width):
    """Greedy word wrap; returns list of lines (never silently drops words)."""
    words, lines, cur = s.split(), [], ""
    for word in words:
        trial = f"{cur} {word}".strip()
        if tw(d, trial, font) <= width or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines


def fit_check(d, s, font, width, max_lines, what):
    """Assert text fits in max_lines at width; raise (never truncate silently)."""
    lines = wrap(d, s, font, width)
    if len(lines) > max_lines:
        raise SystemExit(f"FIT FAIL [{what}]: {len(lines)} lines > {max_lines}: {s!r}")
    return lines


def spaced(s, n=1):
    """Letterspace caps text with hair spaces."""
    return ("\u200a" * n).join(list(s))


def hline(d, x0, x1, y, color=INK, width=1):
    d.line([(x0, y), (x1, y)], fill=color, width=width)


def vline(d, x, y0, y1, color=RULE, width=1):
    d.line([(x, y0), (x, y1)], fill=color, width=width)


def panel_box(d, x0, y0, x1, y1, fill=PANEL, outline=RULE, width=1):
    d.rectangle([x0, y0, x1, y1], fill=fill, outline=outline, width=width)


def dashed_hline(d, x0, x1, y, color=RULE, dash=6, gap=4):
    x = x0
    while x < x1:
        d.line([(x, y), (min(x + dash, x1), y)], fill=color, width=1)
        x += dash + gap


# ---------------------------------------------------------------- halftone
def halftone(img, pitch=4):
    """Dot-screen engraving: each pitch-px cell becomes one dot whose radius
    grows with darkness. Mid-tone scenes only — big dark masses blob."""
    grey = img.convert("L")
    w, hgt = grey.size
    out = Image.new("RGB", (w, hgt), WHITE)
    od = ImageDraw.Draw(out)
    px = grey.load()
    for cy in range(0, hgt, pitch):
        for cx in range(0, w, pitch):
            dark = 0
            n = 0
            for dy in range(pitch):
                for dx in range(pitch):
                    if cx + dx < w and cy + dy < hgt:
                        dark += 255 - px[cx + dx, cy + dy]
                        n += 1
            dark /= max(n, 1)
            r = (dark / 255.0) * (pitch * 0.72)
            if r > 0.4:
                mx, my = cx + pitch / 2, cy + pitch / 2
                od.ellipse([mx - r, my - r, mx + r, my + r], fill=INK)
    return out


# ================================================================ painters
# Every illustration is drawn in code here (flat shapes + hatching), with
# compositions of my own. No photographs, no external images.

def paint_awacs(d, x0, y0, x1, y1):
    """E-3A AWACS over the eastern flank: sky, sea/land strip below, the jet
    with its 9 m radar dome, white window line so the halftone keeps shape."""
    d.rectangle([x0, y0, x1, y1], fill=SKY)
    # land strip (eastern flank) along the bottom
    d.polygon([(x0, y1), (x0, y1 - 26), (x0 + 90, y1 - 34), (x0 + 170, y1 - 24),
               (x0 + 260, y1 - 36), (x0 + 340, y1 - 28), (x1, y1 - 30), (x1, y1)],
              fill=(178, 198, 150))
    d.line([(x0, y1 - 26), (x0 + 90, y1 - 34), (x0 + 170, y1 - 24),
            (x0 + 260, y1 - 36), (x0 + 340, y1 - 28), (x1, y1 - 30)],
           fill=(120, 140, 100), width=2)
    # Warsaw star
    sx, sy = x0 + 250, y1 - 20
    d.ellipse([sx - 5, sy - 5, sx + 5, sy + 5], fill=RED)
    d.text((sx + 8, sy - 6), "WARSAW", font=F("sans_bold", 9), fill=INK)
    # jet: fuselage, dome, wings, tail, engines
    jy = y0 + 52
    d.polygon([(x0 + 30, jy), (x0 + 330, jy - 6), (x0 + 352, jy - 2),
               (x0 + 330, jy + 6), (x0 + 30, jy + 8)], fill=(60, 66, 76))
    d.polygon([(x0 + 150, jy - 2), (x0 + 200, jy - 34), (x0 + 230, jy - 34),
               (x0 + 205, jy - 2)], fill=(60, 66, 76))          # tail fin
    d.polygon([(x0 + 120, jy + 2), (x0 + 90, jy + 34), (x0 + 130, jy + 30),
               (x0 + 160, jy + 4)], fill=(80, 86, 96))          # near wing
    d.polygon([(x0 + 210, jy - 4), (x0 + 250, jy - 30), (x0 + 268, jy - 28),
               (x0 + 235, jy - 2)], fill=(80, 86, 96))          # far wing
    d.line([(x0 + 185, jy - 6), (x0 + 185, jy - 26)], fill=(60, 66, 76), width=4)
    d.ellipse([x0 + 155, jy - 44, x0 + 215, jy - 22], fill=(40, 44, 52))  # dome
    d.ellipse([x0 + 160, jy - 42, x0 + 210, jy - 30], fill=(120, 128, 140))
    for ex in (150, 235):  # engines
        d.ellipse([x0 + ex, jy + 6, x0 + ex + 18, jy + 14], fill=(40, 44, 52))
    d.line([(x0 + 40, jy + 1), (x0 + 320, jy - 4)], fill=WHITE, width=2)  # windows
    # radar sweep arcs from the dome
    for r in (30, 46, 62):
        d.arc([x0 + 185 - r, jy - 33 - r, x0 + 185 + r, jy - 33 + r],
              start=200, end=340, fill=(90, 100, 115), width=2)


def paint_chart(d, x0, y0, x1, y1):
    """Rising market bars + trend line, green on paper."""
    d.rectangle([x0, y0, x1, y1], fill=PANEL)
    wdt, hgt = x1 - x0, y1 - y0
    vals = [18, 26, 22, 34, 30, 44, 52, 66]
    bw = wdt // len(vals)
    for i, v in enumerate(vals):
        bx = x0 + i * bw + 3
        bh = int(v / 70 * (hgt - 22))
        d.rectangle([bx, y1 - 14 - bh, bx + bw - 6, y1 - 14], fill=GREEN)
    d.line([(x0 + 4, y1 - 14), (x1 - 4, y1 - 14)], fill=INK, width=1)
    pts = []
    for i, v in enumerate(vals):
        pts.append((x0 + i * bw + bw // 2, y1 - 16 - int(v / 70 * (hgt - 22))))
    d.line(pts, fill=RED, width=2)
    d.polygon([pts[-1], (pts[-1][0] - 8, pts[-1][1] + 2), (pts[-1][0] - 2, pts[-1][1] + 8)],
              fill=RED)
    d.text((x0 + 6, y0 + 4), "TAIEX +9.1%", font=F("mono_bold", 11), fill=INK)


def paint_factory(d, x0, y0, x1, y1):
    """Cikande: factory block + chimney + DVI tent. No graphic victims."""
    d.rectangle([x0, y0, x1, y1], fill=(232, 222, 200))
    # factory block
    d.rectangle([x0 + 8, y0 + 30, x0 + 88, y1 - 8], fill=(150, 120, 90))
    d.rectangle([x0 + 8, y0 + 30, x0 + 88, y0 + 38], fill=(110, 86, 64))
    for wx in (18, 38, 58):
        d.rectangle([x0 + wx, y0 + 46, x0 + wx + 12, y0 + 58], fill=(60, 58, 52))
    # chimney with smoke
    d.rectangle([x0 + 96, y0 + 12, x0 + 108, y1 - 8], fill=(130, 110, 92))
    for i, (cx, cy, r) in enumerate([(102, 8, 6), (110, 2, 8), (120, -2, 9)]):
        d.ellipse([x0 + cx - r, y0 + cy - r, x0 + cx + r, y0 + cy + r],
                  fill=(170, 168, 160))
    # DVI tent + cross
    d.polygon([(x0 + 118, y1 - 8), (x0 + 136, y0 + 40), (x0 + 154, y1 - 8)],
              fill=WHITE, outline=INK)
    d.line([(x0 + 136, y0 + 48), (x0 + 136, y0 + 60)], fill=RED, width=3)
    d.line([(x0 + 130, y0 + 54), (x0 + 142, y0 + 54)], fill=RED, width=3)
    d.text((x0 + 6, y0 + 2), "DVI POST", font=F("sans_bold", 8), fill=INK)


# ---- mini-card painters: each draws into a (x0,y0,x1,y1) strip, ~166x30
def _sky(d, x0, y0, x1, y1, col=SKY):
    d.rectangle([x0, y0, x1, y1], fill=col)


def art_zaporizhzhia(d, x0, y0, x1, y1):
    _sky(d, x0, y0, x1, y1)
    d.rectangle([x0 + 30, y0 + 4, x0 + 90, y1 - 2], fill=(120, 116, 108))
    d.polygon([(x0 + 90, y0 + 4), (x0 + 130, y0 + 4), (x0 + 130, y1 - 2),
               (x0 + 90, y1 - 2), (x0 + 104, y0 + 14)], fill=(90, 86, 80))
    for wy in (8, 16, 24):
        for wx in (36, 52, 68):
            d.rectangle([x0 + wx, y0 + wy, x0 + wx + 8, y0 + wy + 5], fill=(230, 228, 210))
    d.ellipse([x0 + 118, y0 + 2, x0 + 138, y0 + 14], fill=(200, 198, 188))
    d.ellipse([x0 + 130, y0 + 8, x0 + 152, y0 + 22], fill=(210, 208, 198))


def art_gaza(d, x0, y0, x1, y1):
    _sky(d, x0, y0, x1, y1, (228, 214, 190))
    for bx, bw, bh in [(10, 26, 16), (42, 20, 22), (68, 30, 12), (104, 24, 20)]:
        d.rectangle([x0 + bx, y1 - bh, x0 + bx + bw, y1], fill=(110, 100, 86))
    d.polygon([(x0 + 128, y1), (x0 + 136, y0 + 2), (x0 + 144, y1)], fill=(150, 148, 140))
    d.ellipse([x0 + 128, y0 - 2, x0 + 148, y0 + 10], fill=(170, 168, 160))


def art_brasil(d, x0, y0, x1, y1):
    _sky(d, x0, y0, x1, y1, (214, 232, 214))
    d.ellipse([x0 + 58, y0 + 8, x0 + 108, y1 - 4], fill=(240, 240, 230))  # dome
    d.rectangle([x0 + 20, y0 + 6, x0 + 34, y1 - 4], fill=(200, 200, 190))
    d.rectangle([x0 + 132, y0 + 6, x0 + 146, y1 - 4], fill=(200, 200, 190))
    d.line([(x0 + 8, y1 - 4), (x0 + 158, y1 - 4)], fill=INK, width=2)
    d.text((x0 + 6, y0 + 1), "353–128", font=F("mono_bold", 10), fill=GREEN)


def art_shenzhou(d, x0, y0, x1, y1):
    d.rectangle([x0, y0, x1, y1], fill=(16, 24, 48))
    for sx, sy in [(20, 6), (48, 12), (120, 5), (142, 16), (96, 4), (150, 24)]:
        d.ellipse([x0 + sx, y0 + sy, x0 + sx + 2, y0 + sy + 2], fill=WHITE)
    d.polygon([(x0 + 76, y0 + 2), (x0 + 84, y0 + 2), (x0 + 84, y0 + 20),
               (x0 + 76, y0 + 20)], fill=WHITE)
    d.polygon([(x0 + 76, y0 + 2), (x0 + 80, y0 - 2), (x0 + 84, y0 + 2)], fill=RED)
    d.polygon([(x0 + 72, y0 + 16), (x0 + 76, y0 + 12), (x0 + 76, y0 + 20)], fill=RED)
    d.polygon([(x0 + 88, y0 + 16), (x0 + 84, y0 + 12), (x0 + 84, y0 + 20)], fill=RED)
    d.polygon([(x0 + 78, y0 + 20), (x0 + 82, y0 + 20), (x0 + 80, y0 + 27)], fill=(255, 180, 60))
    d.rectangle([x0 + 116, y0 + 8, x0 + 140, y0 + 12], fill=(180, 180, 190))
    d.rectangle([x0 + 126, y0 + 4, x0 + 130, y0 + 16], fill=(180, 180, 190))


def art_kadiz(d, x0, y0, x1, y1):
    _sky(d, x0, y0, x1, y1)
    d.ellipse([x0 + 100, y1 - 12, x0 + 150, y1 + 6], fill=(120, 160, 110))  # island
    d.polygon([(x0 + 20, y0 + 14), (x0 + 62, y0 + 10), (x0 + 70, y0 + 14),
               (x0 + 62, y0 + 18), (x0 + 20, y0 + 18)], fill=(70, 76, 86))
    d.polygon([(x0 + 44, y0 + 12), (x0 + 54, y0 + 2), (x0 + 60, y0 + 2),
               (x0 + 52, y0 + 12)], fill=(70, 76, 86))
    for r in (10, 18, 26):
        d.arc([x0 + 124 - r, y1 - 8 - r, x0 + 124 + r, y1 - 8 + r],
              start=180, end=360, fill=RED, width=2)


def art_emden(d, x0, y0, x1, y1):
    _sky(d, x0, y0, x1, y1, (226, 226, 220))
    for i in range(4):  # sawtooth factory roof
        bx = x0 + 8 + i * 30
        d.polygon([(bx, y1 - 4), (bx, y0 + 12), (bx + 30, y0 + 4), (bx + 30, y1 - 4)],
                  fill=(140, 136, 128))
    d.line([(x0 + 128, y0 + 4), (x0 + 128, y1 - 4)], fill=INK, width=2)
    d.rectangle([x0 + 116, y0 + 4, x0 + 146, y0 + 16], fill=WHITE, outline=INK)
    d.text((x0 + 120, y0 + 6), "5%", font=F("sans_bold", 8), fill=RED)


def art_strike(d, x0, y0, x1, y1):
    _sky(d, x0, y0, x1, y1, (240, 232, 214))
    for i, px in enumerate((24, 66, 108)):
        d.line([(x0 + px, y0 + 12), (x0 + px, y1 - 2)], fill=INK, width=2)
        d.rectangle([x0 + px - 14, y0 + 2, x0 + px + 14, y0 + 14],
                    fill=WHITE, outline=RED)
    d.text((x0 + 16, y0 + 4), "+5%", font=F("sans_bold", 9), fill=RED)
    d.text((x0 + 58, y0 + 4), "JOBS", font=F("sans_bold", 8), fill=INK)
    d.text((x0 + 98, y0 + 4), "PAY", font=F("sans_bold", 8), fill=INK)
    for px in (24, 66, 108, 140):
        d.ellipse([x0 + px - 4, y1 - 10, x0 + px + 4, y1 - 2], fill=(90, 70, 50))


def art_brent(d, x0, y0, x1, y1):
    _sky(d, x0, y0, x1, y1, (232, 228, 216))
    d.rectangle([x0 + 14, y0 + 6, x0 + 44, y1 - 4], fill=(60, 70, 84))
    d.line([(x0 + 14, y0 + 12), (x0 + 44, y0 + 12)], fill=(140, 148, 160), width=2)
    d.line([(x0 + 14, y1 - 10), (x0 + 44, y1 - 10)], fill=(140, 148, 160), width=2)
    d.line([(x0 + 62, y0 + 6), (x0 + 150, y0 + 24)], fill=RED, width=3)
    d.polygon([(x0 + 150, y0 + 24), (x0 + 138, y0 + 20), (x0 + 142, y0 + 28)], fill=RED)
    d.text((x0 + 62, y0 + 1), "$89", font=F("mono_bold", 11), fill=INK)


def art_mnf(d, x0, y0, x1, y1):
    d.rectangle([x0, y0, x1, y1], fill=(34, 110, 60))
    d.line([(x0 + 80, y0 + 4), (x0 + 80, y1 - 4)], fill=(255, 220, 60), width=3)
    d.line([(x0 + 58, y0 + 4), (x0 + 58, y0 + 16)], fill=(255, 220, 60), width=3)
    d.line([(x0 + 102, y0 + 4), (x0 + 102, y0 + 16)], fill=(255, 220, 60), width=3)
    d.line([(x0 + 58, y0 + 16), (x0 + 102, y0 + 16)], fill=(255, 220, 60), width=3)
    d.ellipse([x0 + 20, y0 + 16, x0 + 38, y0 + 26], fill=(150, 90, 50))
    d.text((x0 + 112, y0 + 12), "22–20", font=F("mono_bold", 11), fill=WHITE)


def art_larkin(d, x0, y0, x1, y1):
    d.rectangle([x0, y0, x1, y1], fill=(210, 226, 240))
    d.line([(x0, y1 - 8), (x1, y1 - 8)], fill=RED, width=2)
    d.line([(x0 + 82, y0), (x0 + 82, y1)], fill=RED, width=2)
    d.rectangle([x0 + 24, y0 + 6, x0 + 56, y1 - 10], fill=(190, 30, 45))
    d.text((x0 + 30, y0 + 12), "89", font=F("sans_bold", 14), fill=WHITE)
    d.ellipse([x0 + 120, y1 - 16, x0 + 134, y1 - 8], fill=INK)


def art_brentford(d, x0, y0, x1, y1):
    d.rectangle([x0, y0, x1, y1], fill=(40, 120, 66))
    d.rectangle([x0 + 12, y0 + 6, x0 + 92, y1 - 6], fill=WHITE, outline=INK)
    for gx in range(20, 92, 12):
        d.line([(x0 + gx, y0 + 6), (x0 + gx, y1 - 6)], fill=(200, 200, 200), width=1)
    for gy in range(12, 26, 8):
        d.line([(x0 + 12, y0 + gy), (x0 + 92, y0 + gy)], fill=(200, 200, 200), width=1)
    d.ellipse([x0 + 118, y0 + 12, x0 + 134, y1 - 6], fill=WHITE, outline=INK)
    d.text((x0 + 100, y0 + 1), "4–0", font=F("mono_bold", 11), fill=WHITE)


def art_proof(d, x0, y0, x1, y1):
    d.rectangle([x0, y0, x1, y1], fill=(238, 236, 228))
    d.text((x0 + 10, y0 + 6), "VP ≠ VNP", font=F("mono_bold", 14), fill=INK)
    d.line([(x0 + 112, y0 + 20), (x0 + 122, y0 + 26), (x0 + 142, y0 + 6)],
           fill=GREEN, width=3)
    d.text((x0 + 10, y0 + 20), "73,000 lines Lean", font=F("sans", 8), fill=GREY)


CARD_ART = {
    2: art_zaporizhzhia, 3: art_gaza, 10: art_brasil, 23: art_shenzhou,
    8: art_kadiz, 20: art_emden, 21: art_strike, 16: art_brent,
    28: art_mnf, 30: art_larkin, 31: art_brentford, 25: art_proof,
}


# ---------------------------------------------------------------- world map
# Simplified continent outlines (lon/lat, equirectangular). Rough but
# recognisable at this size; drawn from my own knowledge of world geography.
CONTINENTS = {
    "n_america": [(-168, 66), (-140, 70), (-125, 72), (-110, 73), (-95, 72),
                  (-85, 70), (-80, 73), (-65, 62), (-60, 52), (-65, 45),
                  (-75, 35), (-80, 25), (-85, 30), (-90, 21), (-97, 16),
                  (-105, 20), (-110, 24), (-117, 33), (-124, 42), (-124, 48),
                  (-135, 58), (-155, 58)],
    "s_america": [(-78, 8), (-72, 12), (-60, 8), (-50, 5), (-35, -8),
                  (-35, -20), (-40, -30), (-48, -28), (-52, -32), (-58, -38),
                  (-62, -41), (-65, -47), (-69, -52), (-73, -50), (-73, -37),
                  (-70, -20), (-77, -12), (-80, -3)],
    "europe": [(-10, 36), (-9, 43), (-2, 48), (-4, 50), (0, 53), (5, 58),
               (10, 58), (18, 56), (21, 55), (24, 58), (28, 60), (30, 62),
               (32, 66), (28, 70), (20, 70), (15, 68), (12, 64), (8, 58),
               (5, 60), (-5, 60), (-8, 55), (-10, 52)],
    "britain": [(-5, 50), (-3, 53), (-5, 56), (-3, 58), (-1, 57), (1, 52), (0, 51)],
    "africa": [(-17, 15), (-16, 21), (-10, 31), (-5, 35), (10, 37), (20, 32),
               (32, 31), (35, 28), (34, 20), (40, 15), (43, 12), (51, 12),
               (48, 2), (41, -2), (40, -10), (35, -18), (32, -26), (28, -33),
               (20, -35), (17, -29), (14, -22), (12, -6), (9, 4), (-8, 4),
               (-13, 8)],
    "asia": [(30, 36), (36, 36), (44, 39), (48, 30), (56, 27), (60, 25),
             (66, 25), (70, 20), (72, 20), (77, 8), (80, 7), (80, 15),
             (88, 22), (91, 22), (94, 17), (98, 10), (100, 7), (103, 1),
             (104, 9), (106, 10), (109, 13), (106, 21), (110, 21), (114, 23),
             (120, 28), (122, 31), (120, 35), (126, 40), (130, 42), (132, 43),
             (135, 44), (138, 46), (141, 50), (142, 55), (140, 60), (135, 62),
             (130, 68), (125, 72), (120, 73), (110, 74), (100, 77), (90, 75),
             (80, 73), (70, 72), (60, 69), (50, 68), (45, 68), (40, 66),
             (35, 66), (30, 62), (28, 58), (30, 55), (28, 50), (30, 46),
             (32, 42)],
    "australia": [(113, -22), (114, -28), (115, -33), (118, -35), (124, -33),
                  (129, -32), (132, -32), (135, -35), (138, -35), (140, -38),
                  (145, -38), (147, -38), (150, -37), (153, -27), (153, -24),
                  (146, -19), (142, -11), (142, -15), (136, -12), (132, -12),
                  (130, -13), (126, -14), (122, -17), (118, -20)],
    "indonesia": [(95, 5), (100, 0), (105, -5), (110, -7), (115, -8),
                  (120, -10), (125, -9), (130, -3), (135, -2), (140, -3),
                  (141, -1), (135, 1), (130, 1), (125, -1), (120, -2),
                  (115, -1), (110, 0), (105, 1), (100, 3)],
    "japan": [(130, 31), (132, 34), (136, 35), (140, 36), (141, 40),
              (142, 44), (140, 42), (138, 38), (134, 35), (131, 33)],
}


def paint_map(d, x0, y0, x1, y1):
    """World map panel: sea, graticule, land polygons, red pins + labels."""
    d.rectangle([x0, y0, x1, y1], fill=SEA, outline=RULE, width=1)
    mw, mh = x1 - x0, y1 - y0

    def proj(lon, lat):
        return (x0 + (lon + 180) / 360 * mw, y0 + (90 - lat) / 180 * mh)

    for lon in range(-150, 181, 30):  # graticule
        gx, _ = proj(lon, 0)
        d.line([(gx, y0), (gx, y1)], fill=(196, 210, 222), width=1)
    for lat in (-30, 0, 30, 60):
        _, gy = proj(0, lat)
        d.line([(x0, gy), (x1, gy)], fill=(196, 210, 222), width=1)
    for poly in CONTINENTS.values():
        pts = [proj(lon, lat) for lon, lat in poly]
        d.polygon(pts, fill=LAND, outline=LAND_EDGE)
    d.text((x0 + 6, y0 + 4), "WHERE IT HAPPENED", font=F("sans_bold", 10), fill=INK)
    # pins: try 8 label positions until one fits without colliding with an
    # earlier label; keep inside the panel. A leader line joins any label
    # that is not in the default right-hand slot to its pin.
    placed = []

    def collides(rx0, ry0, rx1, ry1):
        for px0, py0, px1, py1 in placed:
            if rx0 < px1 and rx1 > px0 and ry0 < py1 and ry1 > py0:
                return True
        return False

    for pin in DATA["map_pins"]:
        px, py = proj(pin["lon"], pin["lat"])
        label = pin["label"]
        fw = tw(d, label, F("sans_bold", 9))
        fh = 10
        cands = [
            (px + 7, py - 6), (px - fw - 10, py - 6),
            (px - fw / 2, py - 19), (px - fw / 2, py + 7),
            (px + 7, py - 19), (px + 7, py + 7),
            (px - fw - 10, py - 19), (px - fw - 10, py + 7),
            (px + 7, py - 32), (px - fw - 10, py - 32),
            (px + 7, py + 20), (px - fw - 10, py + 20),
            (px - fw / 2, py - 32), (px - fw / 2, py + 20),
        ]
        lx, ly, slot = cands[0][0], cands[0][1], 0
        for i, (cx, cy) in enumerate(cands):
            cx = max(x0 + 2, min(cx, x1 - fw - 2))
            cy = max(y0 + 2, min(cy, y1 - fh - 2))
            if not collides(cx, cy, cx + fw, cy + fh):
                lx, ly, slot = cx, cy, i
                break
        else:
            print(f"WARNING: pin {label} label collides everywhere; using default slot")
            lx = max(x0 + 2, min(cands[0][0], x1 - fw - 2))
            ly = max(y0 + 2, min(cands[0][1], y1 - fh - 2))
        placed.append((lx, ly, lx + fw, ly + fh))
        if slot != 0:
            # leader line from the label's nearest corner to the pin
            ex = lx + fw if lx < px else lx
            ey = ly + fh / 2
            d.line([(ex, ey), (px, py)], fill=GREY, width=1)
        d.rectangle([lx - 1, ly - 1, lx + fw + 1, ly + 10], fill=WHITE)
        d.text((lx, ly), label, font=F("sans_bold", 9), fill=INK)
        d.ellipse([px - 3, py - 3, px + 3, py + 3], fill=RED, outline=WHITE, width=1)
        log_box(lx, ly, lx + fw, ly + 10, f"pin {label}")


# ================================================================ layout
MARGIN = 14
CW = W - 2 * MARGIN  # 996 content width


def section_kicker(d):
    y = 0
    hline(d, MARGIN, W - MARGIN, y + 2, color=RED, width=3)
    f = F("mono_bold", 11)
    t = DATA["kicker"]
    d.text(((W - tw(d, t, f)) / 2, y + 5), t, font=f, fill=INK)
    log_box(MARGIN, y + 5, W - MARGIN, y + 16, "kicker")
    return y + 16


def section_masthead(d, y0):
    y1 = y0 + 76
    # ears: facts only, no invented weather or edition numbers
    ear_w = 150
    panel_box(d, MARGIN, y0 + 8, MARGIN + ear_w, y1 - 8, fill=PAPER)
    d.text((MARGIN + 8, y0 + 12), "TUESDAY", font=F("sans_bold", 11), fill=RED)
    d.text((MARGIN + 8, y0 + 26), "24 NOVEMBER 2026", font=F("sans_bold", 11), fill=INK)
    d.text((MARGIN + 8, y0 + 42), "Research cut-off 15:00 WIB", font=F("sans", 9), fill=GREY)
    panel_box(d, W - MARGIN - ear_w, y0 + 8, W - MARGIN, y1 - 8, fill=PAPER)
    d.text((W - MARGIN - ear_w + 8, y0 + 12), "43 STORIES", font=F("sans_bold", 11), fill=INK)
    d.text((W - MARGIN - ear_w + 8, y0 + 26), "6 REGIONS  ·  0 AFRICA*", font=F("sans_bold", 11), fill=INK)
    d.text((W - MARGIN - ear_w + 8, y0 + 42), "*no verified story today", font=F("sans", 9), fill=GREY)
    # nameplate
    name = DATA["edition"]
    nf = F("display_black", 58)
    nw = tw(d, name, nf)
    d.text(((W - nw) / 2, y0 + 2), name, font=nf, fill=INK)
    date = spaced(DATA["date_line"])
    df = F("sans_bold", 13)
    dw = tw(d, date, df)
    d.text(((W - dw) / 2, y0 + 58), date, font=df, fill=INK)
    log_box(MARGIN, y0, W - MARGIN, y1, "masthead")
    hline(d, MARGIN, W - MARGIN, y1, color=INK, width=2)
    hline(d, MARGIN, W - MARGIN, y1 + 2, color=INK, width=1)
    return y1 + 2


def section_regions(d, y0):
    y1 = y0 + 14
    parts = []
    for name, count in DATA["region_bar"]:
        parts.append(f"{name} {count}")
    t = "   ·   ".join(parts)
    f = F("sans_bold", 10)
    d.text(((W - tw(d, t, f)) / 2, y0 + 2), t, font=f, fill=INK)
    log_box(MARGIN, y0, W - MARGIN, y1, "regions")
    hline(d, MARGIN, W - MARGIN, y1, color=RULE, width=1)
    return y1


def section_heroes(img, d, y0):
    """Lead hero full width (112px), two secondary heroes side by side (78px)."""
    y1 = y0 + 190
    h1, h2, h3 = HEROES
    # --- lead hero: art left, text right
    ax0, ay0, ax1, ay1 = MARGIN, y0 + 4, MARGIN + 420, y0 + 108
    art = Image.new("RGB", (ax1 - ax0, ay1 - ay0), SKY)
    ad = ImageDraw.Draw(art)
    paint_awacs(ad, 0, 0, ax1 - ax0, ay1 - ay0)
    if h1.get("halftone"):
        art = halftone(art)
    img.paste(art, (ax0, ay0))
    d.rectangle([ax0, ay0, ax1, ay1], outline=RULE, width=1)
    d.rectangle([ax0, ay1 - 16, ax1, ay1], fill=NAVY)  # label bar AFTER halftone
    d.text((ax0 + 6, ay1 - 14), "E-3A AWACS · RADAR DOME 9 M · RANGE >400 KM",
           font=F("sans_bold", 9), fill=WHITE)
    tx = ax1 + 14
    twd = W - MARGIN - tx
    if h1.get("critical"):
        d.rectangle([tx, y0 + 6, tx + 74, y0 + 20], fill=RED)
        d.text((tx + 6, y0 + 8), "CRITICAL", font=F("sans_bold", 10), fill=WHITE)
        d.text((tx + 82, y0 + 8), h1["kicker"], font=F("sans_bold", 10), fill=GREY)
    else:
        d.text((tx, y0 + 8), h1["kicker"], font=F("sans_bold", 10), fill=GREY)
    d.text((tx, y0 + 18), h1["tag"], font=F("sans_bold", 11), fill=RED)
    hf = F("display_bold", 34)
    d.text((tx, y0 + 30), h1["headline"], font=hf, fill=INK)
    log_box(tx, y0 + 30, tx + tw(d, h1["headline"], hf), y0 + 64, "hero1 headline")
    deck_lines = fit_check(d, h1["deck"], F("serif", 14), twd, 2, "hero1 deck")
    yy = y0 + 66
    for ln in deck_lines:
        d.text((tx, yy), ln, font=F("serif", 14), fill=INK)
        yy += 16
    d.text((tx, yy + 2), h1["sub"], font=F("serif_italic", 12), fill=GREY)
    # --- secondary heroes (deck carries the numbers; no separate sub-line)
    sy = y0 + 112
    half = CW // 2
    for hero, sx in ((h2, MARGIN), (h3, MARGIN + half + 6)):
        sw = half - 6
        panel_box(d, sx, sy, sx + sw, sy + 78, fill=PAPER)
        art_w = 150
        if hero["n"] == 15:
            paint_chart(d, sx + 5, sy + 5, sx + 5 + art_w, sy + 73)
        else:
            paint_factory(d, sx + 5, sy + 5, sx + 5 + art_w, sy + 73)
        tx2 = sx + 5 + art_w + 10
        tw2 = sx + sw - tx2 - 6
        d.text((tx2, sy + 6), hero["kicker"], font=F("sans_bold", 9), fill=GREY)
        d.text((tx2, sy + 18), hero["tag"], font=F("sans_bold", 10), fill=RED)
        hf2 = F("display_bold", 24)
        d.text((tx2, sy + 28), hero["headline"], font=hf2, fill=INK)
        log_box(tx2, sy + 28, tx2 + tw(d, hero["headline"], hf2), sy + 52, "hero2/3 headline")
        dl = fit_check(d, hero["deck"], F("serif", 11), tw2, 2, "hero2/3 deck")
        yy = sy + 54
        for ln in dl:
            d.text((tx2, yy), ln, font=F("serif", 11), fill=INK)
            yy += 12
    hline(d, MARGIN, W - MARGIN, y1, color=RULE, width=1)
    return y1


def section_pull_quote(d, y0):
    y1 = y0 + 16
    q = DATA["pull_quote"]
    a = DATA["pull_quote_attribution"]
    qf = F("serif_italic", 14)
    af = F("sans", 9)
    full_w = tw(d, q, qf) + 8 + tw(d, f"— {a}", af)
    x = (W - full_w) / 2
    d.text((x, y0 + 2), q, font=qf, fill=INK)
    d.text((x + tw(d, q, qf) + 8, y0 + 5), f"— {a}", font=af, fill=GREY)
    log_box(MARGIN, y0, W - MARGIN, y1, "pull quote")
    hline(d, MARGIN, W - MARGIN, y1, color=RULE, width=1)
    return y1


def section_map_numbers(d, y0):
    y1 = y0 + 132
    map_w = 640
    paint_map(d, MARGIN, y0 + 4, MARGIN + map_w, y1 - 4)
    # numbers table, right of the map
    nx0 = MARGIN + map_w + 10
    nx1 = W - MARGIN
    panel_box(d, nx0, y0 + 4, nx1, y1 - 4, fill=PAPER)
    d.text((nx0 + 10, y0 + 8), "BY THE NUMBERS", font=F("sans_bold", 11), fill=INK)
    hline(d, nx0 + 10, nx1 - 10, y0 + 24, color=RULE, width=1)
    ry = y0 + 28
    for value, label in DATA["numbers_table"]:
        vf = F("serif_bold", 15)
        d.text((nx1 - 10 - tw(d, value, vf), ry), value, font=vf, fill=INK)
        lab_lines = fit_check(d, label, F("sans", 10), (nx1 - nx0) - 24 - tw(d, value, vf) - 8,
                              1, f"number label {value}")
        d.text((nx0 + 10, ry + 2), lab_lines[0], font=F("sans", 10), fill=INK)
        ry += 15
        if value != DATA["numbers_table"][-1][0]:
            hline(d, nx0 + 10, nx1 - 10, ry - 2, color=(210, 202, 180), width=1)
    d.text((nx0 + 10, y1 - 12), DATA["numbers_footnote"], font=F("sans", 8), fill=GREY)
    log_box(nx0, y0, nx1, y1, "numbers table")
    return y1


def section_fold(d, y0):
    dashed_hline(d, MARGIN, W - MARGIN, y0 + 2)
    d.text((W - MARGIN - 34, y0 - 4), "FOLD", font=F("sans_bold", 8), fill=GREY)
    return y0 + 4


def section_index_row(d, y0):
    y1 = y0 + 66
    third = CW // 3
    boxes = [
        ("INSIDE TODAY", DATA["inside_today"]),
        ("QUOTE OF THE DAY", None),
        ("TOMORROW", DATA["tomorrow"]),
    ]
    for i, (title, lines) in enumerate(boxes):
        bx0 = MARGIN + i * (third + 5)
        bx1 = bx0 + third - (5 if i < 2 else 0)
        if i == 2:
            bx1 = W - MARGIN
        panel_box(d, bx0, y0 + 2, bx1, y1 - 2, fill=PAPER)
        d.text((bx0 + 8, y0 + 5), title, font=F("sans_bold", 10), fill=RED)
        if lines is None:
            q = DATA["quote_of_day"]
            ql = fit_check(d, q, F("serif_italic", 12), bx1 - bx0 - 16, 2, "quote of day")
            yy = y0 + 20
            for ln in ql:
                d.text((bx0 + 8, yy), ln, font=F("serif_italic", 12), fill=INK)
                yy += 14
            d.text((bx0 + 8, yy + 1), DATA["quote_attribution"], font=F("sans", 9), fill=GREY)
        else:
            yy = y0 + 20
            for ln in lines:
                d.text((bx0 + 8, yy), ln, font=F("sans", 10), fill=INK)
                yy += 11
                if yy > y1 - 8:
                    break
        log_box(bx0, y0, bx1, y1, f"index {title}")
    return y1


def section_briefs(d, y0):
    """Three columns, 28 brief stories (all stories not featured as hero/card)."""
    featured = {h["n"] for h in HEROES} | {c["n"] for c in CARDS}
    briefs = [s for s in DATA["stories"] if s["n"] not in featured]
    assert len(briefs) == 28, f"expected 28 briefs, got {len(briefs)}"
    header = "THE DAY IN BRIEF — 28 MORE STORIES, NUMBERED WITH THE FRONT"
    d.text((MARGIN, y0 + 1), header, font=F("sans_bold", 11), fill=INK)
    hline(d, MARGIN, W - MARGIN, y0 + 14, color=INK, width=1)
    col_w = CW // 3
    pitch = 16
    per_col = [10, 9, 9]
    idx = 0
    bf = F("serif", 11)
    nf = F("sans_bold", 11)
    for ci, count in enumerate(per_col):
        cx = MARGIN + ci * col_w
        if ci:
            vline(d, cx - 7, y0 + 18, y0 + 18 + 10 * pitch)
        for r in range(count):
            s = briefs[idx]
            idx += 1
            yy = y0 + 18 + r * pitch
            num = f"{s['n']:02d}"
            col = REGION_COLOURS[s["region"]]
            d.rectangle([cx, yy + 2, cx + 7, yy + 9], fill=col)
            d.text((cx + 11, yy), num, font=nf, fill=col)
            hw = col_w - 34
            fit_check(d, s["headline"], bf, hw, 1, f"brief {s['n']}")
            d.text((cx + 34, yy), s["headline"], font=bf, fill=INK)
            log_box(cx, yy, cx + col_w - 8, yy + 12, f"brief {s['n']}")
    return y0 + 178


def section_cards(d, y0):
    """Two rows of six illustrated mini-cards (78px rows)."""
    y1 = y0 + 78 + 78
    card_w = CW // 6
    for row in range(2):
        for ci in range(6):
            card = CARDS[row * 6 + ci]
            cx0 = MARGIN + ci * card_w
            cx1 = cx0 + card_w
            cy0 = y0 + row * 78
            cy1 = cy0 + 78
            panel_box(d, cx0 + 2, cy0 + 2, cx1 - 2, cy1 - 2, fill=PAPER)
            art_fn = CARD_ART[card["n"]]
            art_fn(d, cx0 + 4, cy0 + 4, cx1 - 4, cy0 + 32)
            tx = cx0 + 6
            twd = card_w - 12
            d.text((tx, cy0 + 34), card["tag"], font=F("sans_bold", 9), fill=RED)
            hl = fit_check(d, card["headline"], F("serif_bold", 11), twd, 1,
                           f"card {card['n']} headline")
            d.text((tx, cy0 + 46), hl[0], font=F("serif_bold", 11), fill=INK)
            cap = fit_check(d, card["caption"], F("sans", 8), twd, 1,
                            f"card {card['n']} caption")
            d.text((tx, cy0 + 66), cap[0], font=F("sans", 8), fill=GREY)
            log_box(cx0, cy0, cx1, cy1, f"card {card['n']}")
    return y1


def section_claims(d, y0):
    """CLAIMS band: red prefix inline, claims wrap to 2 lines in 30px."""
    y1 = y0 + 30
    d.rectangle([MARGIN, y0 + 2, W - MARGIN, y1 - 2], fill=RED_SOFT, outline=RED, width=1)
    prefix = "CLAIMS, NOT FACTS:  "
    hf = F("sans_bold", 10)
    bf = F("sans", 10)
    # wrap on claim boundaries: line 1 fills with whole claims after the
    # prefix, the rest go to line 2 (never split a claim's "— unverified").
    claims = DATA["claims"]
    first_w = CW - 16 - tw(d, prefix, hf)
    l1_items, l2_items, used = [], [], 0.0
    for cl in claims:
        w = tw(d, cl, bf) + (tw(d, "  ·  ", bf) if l1_items else 0)
        if used + w <= first_w:
            l1_items.append(cl)
            used += w
        else:
            l2_items.append(cl)
    l1 = "  ·  ".join(l1_items)
    l2 = "  ·  ".join(l2_items)
    if tw(d, l2, bf) > CW - 16:
        raise SystemExit(f"FIT FAIL [claims]: line 2 overflows: {l2!r}")
    d.text((MARGIN + 8, y0 + 5), prefix, font=hf, fill=RED)
    d.text((MARGIN + 8 + tw(d, prefix, hf), y0 + 5), l1, font=bf, fill=INK)
    if l2:
        d.text((MARGIN + 8, y0 + 16), l2, font=bf, fill=INK)
    log_box(MARGIN, y0, W - MARGIN, y1, "claims")
    return y1


def section_timeline(d, y0):
    y1 = y0 + 32
    d.text((MARGIN, y0 + 2), "TUESDAY IN UTC", font=F("sans_bold", 10), fill=INK)
    hline(d, MARGIN + 110, W - MARGIN, y0 + 7, color=RULE, width=1)
    items = DATA["timeline"]
    slot = (CW - 110) // len(items)
    for i, (t, txt) in enumerate(items):
        cx = MARGIN + 110 + i * slot
        d.ellipse([cx + 4, y0 + 4, cx + 10, y0 + 10], fill=RED)
        d.text((cx + 14, y0 + 1), t, font=F("mono_bold", 10), fill=RED)
        tl = fit_check(d, txt, F("sans", 9), slot - 16, 2, f"timeline {t}")
        yy = y0 + 13
        for ln in tl:
            d.text((cx + 14, yy), ln, font=F("sans", 9), fill=INK)
            yy += 10
        log_box(cx, y0, cx + slot, y1, f"timeline {t}")
    return y1


def section_ticker(d, y0):
    y1 = y0 + 24
    d.rectangle([MARGIN, y0 + 2, W - MARGIN, y1 - 2], fill=NAVY)
    t = DATA["ticker"]
    size = 12
    while tw(d, t, F("mono_bold", size)) > CW - 16 and size > 9:
        size -= 1
    f = F("mono_bold", size)
    d.text(((W - tw(d, t, f)) / 2, y0 + 7), t, font=f, fill=WHITE)
    log_box(MARGIN, y0, W - MARGIN, y1, "ticker")
    return y1


def section_date_check(d, y0):
    y1 = y0 + 66
    d.rectangle([MARGIN, y0 + 2, W - MARGIN, y1 - 2], fill=RED_SOFT, outline=RULE, width=1)
    d.text((MARGIN + 8, y0 + 5), "DATE CHECK — WHAT WE LEFT OUT, AND WHY",
           font=F("sans_bold", 10), fill=RED)
    half = CW // 2
    bf = F("sans", 9)
    for col, key in ((0, "date_check_left"), (1, "date_check_right")):
        cx = MARGIN + 8 + col * half
        lines = fit_check(d, DATA[key], bf, half - 16, 5, key)
        yy = y0 + 18
        for ln in lines:
            d.text((cx, yy), ln, font=bf, fill=INK)
            yy += 9
        log_box(cx, y0 + 17, cx + half - 16, y0 + 17 + len(lines) * 9, key)
    return y1


def section_footer(d, y0):
    y1 = y0 + 22
    fb = DATA["footer_bold"]
    ff = F("serif_bold", 11)
    d.text(((W - tw(d, fb, ff)) / 2, y0 + 1), fb, font=ff, fill=INK)
    fs = DATA["footer_small"]
    sf = F("sans", 9)
    d.text(((W - tw(d, fs, sf)) / 2, y0 + 13), fs, font=sf, fill=GREY)
    log_box(MARGIN, y0, W - MARGIN, y1, "footer")
    return y1


# ================================================================ main
def render(out_path):
    img = Image.new("RGB", (W, H), PAPER)
    d = ImageDraw.Draw(img)
    y = section_kicker(d)            # 16
    y = section_masthead(d, y)       # 78
    y = section_regions(d, y)        # 14
    y = section_heroes(img, d, y)    # 190
    y = section_pull_quote(d, y)     # 16
    y = section_map_numbers(d, y)    # 132
    y = section_fold(d, y)           # 4
    y = section_index_row(d, y)      # 66
    y = section_briefs(d, y)         # 178
    y = section_cards(d, y)          # 156
    y = section_claims(d, y)         # 30
    y = section_timeline(d, y)       # 32
    y = section_ticker(d, y)         # 24
    y = section_date_check(d, y)     # 66
    y = section_footer(d, y)         # 22
    if y != H:
        raise SystemExit(f"LAYOUT FAIL: used {y}px, canvas is {H}px")
    img.save(out_path, "PNG", optimize=True)
    if os.environ.get("DRAW_LOG"):
        (BASE / "boxes.json").write_text(json.dumps(BOXES))
    return out_path


if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else str(BASE / "entry.png")
    render(target)
    print(f"rendered {target} ({Path(target).stat().st_size} bytes)")
