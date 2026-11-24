#!/usr/bin/env python3
"""verify.py — independent checks for the news-image-20261124 entry.

Run from the entry dir:  python3 verify.py
Checks:
  1. determinism: two renders are byte-identical (SHA-256)
  2. gate: PNG, 1024x1024, <= 1 MiB
  3. signal: grayscale stats sane; 300px downscale still has masthead ink
  4. geometry: logged text boxes stay inside the canvas and pin labels
     never overlap each other
  5. data: 43 stories numbered 1..43, Top 10 ranks 1..10, region counts
     match the region bar, heroes 3 / cards 12 / briefs 28 / claims 5 /
     timeline 7 / pins 16, every hero + card tag unique
Exits non-zero on the first failure.
"""
import hashlib
import json
import os
import subprocess
import sys

from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = json.load(open(os.path.join(HERE, "stories.json")))


def fail(msg):
    print(f"VERIFY FAIL: {msg}")
    sys.exit(1)


def ok(msg):
    print(f"  ok: {msg}")


def sha(path):
    return hashlib.sha256(open(path, "rb").read()).hexdigest()


def main():
    print("== 1. determinism (two renders, byte-identical) ==")
    env = dict(os.environ, DRAW_LOG="1")
    outs = []
    for name in ("v1.png", "v2.png"):
        p = os.path.join(HERE, name)
        r = subprocess.run(
            [sys.executable, os.path.join(HERE, "draw.py"), p],
            cwd=HERE, env=env, capture_output=True, text=True,
        )
        if r.returncode != 0:
            fail(f"draw.py {name} failed:\n{r.stdout}\n{r.stderr}")
        outs.append(p)
    h1, h2 = sha(outs[0]), sha(outs[1])
    if h1 != h2:
        fail(f"renders differ: {h1[:12]} vs {h2[:12]}")
    ok(f"byte-identical SHA-256 {h1[:16]}...")

    print("== 2. gate ==")
    img = Image.open(outs[0])
    if img.size != (1024, 1024):
        fail(f"size {img.size}, want (1024, 1024)")
    size_b = os.path.getsize(outs[0])
    if size_b > 1_048_576:
        fail(f"{size_b} bytes > 1 MiB")
    ok(f"PNG 1024x1024, {size_b} bytes ({size_b / 1024:.0f} KiB)")

    print("== 3. signal ==")
    g = img.convert("L")
    px = list(g.getdata())
    mean = sum(px) / len(px)
    dark = sum(1 for v in px if v < 80) / len(px)
    if not (150 < mean < 245):
        fail(f"grayscale mean {mean:.1f} outside sane range")
    if not (0.02 < dark < 0.40):
        fail(f"dark fraction {dark:.3f} outside sane range")
    ok(f"grayscale mean {mean:.1f}, dark frac {dark:.3f}")
    small = g.resize((300, 300))
    mast = small.crop((90, 8, 210, 30))  # masthead title area at 300px
    ink = sum(1 for v in mast.getdata() if v < 120) / (120 * 22)
    if ink < 0.05:
        fail(f"300px masthead ink {ink:.3f} too faint")
    ok(f"300px masthead ink {ink:.3f}")

    print("== 4. geometry (boxes.json) ==")
    boxes = json.load(open(os.path.join(HERE, "boxes.json")))
    for x0, y0, x1, y1, name in boxes:
        if not (0 <= x0 < x1 <= 1024 and 0 <= y0 < y1 <= 1024):
            fail(f"box out of canvas: {name} {(x0, y0, x1, y1)}")
    pins = [b for b in boxes if b[4].startswith("pin ")]
    for i, a in enumerate(pins):
        for b in pins[i + 1:]:
            if a[0] < b[2] and a[2] > b[0] and a[1] < b[3] and a[3] > b[1]:
                fail(f"pin labels overlap: {a[4]} vs {b[4]}")
    ok(f"{len(boxes)} boxes inside canvas, {len(pins)} pin labels disjoint")

    print("== 5. data completeness ==")
    stories = DATA["stories"]
    nums = sorted(s["n"] for s in stories)
    if nums != list(range(1, 44)):
        fail(f"story numbers not 1..43: {nums}")
    ranks = sorted(s["top10"] for s in stories if s.get("top10"))
    if ranks != [1, 2, 3, 4, 5, 6, 7, 8, 9, 9, 10]:
        fail(f"Top 10 ranks not 1..10 (9 shared): {ranks}")
    counts = {}
    for s in stories:
        counts[s["region"]] = counts.get(s["region"], 0) + 1
    names = {"EU": "EUROPE", "AS": "ASIA-PACIFIC", "AM": "AMERICAS",
             "ME": "MIDDLE EAST", "OC": "OCEANIA", "WD": "GLOBAL"}
    bar = {name: n for name, n in DATA["region_bar"]}
    for code, n in counts.items():
        if bar.get(names[code]) != n:
            fail(f"region {names[code]}: {n} stories but bar says {bar.get(names[code])}")
    if bar.get("AFRICA") != 0:
        fail(f"AFRICA bar is {bar.get('AFRICA')}, must be 0 (no verified story)")
    if len(DATA["heroes"]) != 3:
        fail(f"{len(DATA['heroes'])} heroes, want 3")
    if len(DATA["cards"]) != 12:
        fail(f"{len(DATA['cards'])} cards, want 12")
    featured = {h["n"] for h in DATA["heroes"]} | {c["n"] for c in DATA["cards"]}
    briefs = [s for s in stories if s["n"] not in featured]
    if len(briefs) != 28:
        fail(f"{len(briefs)} briefs (stories not hero/card), want 28")
    if len(DATA["claims"]) != 5:
        fail(f"{len(DATA['claims'])} claims, want 5")
    if len(DATA["timeline"]) != 7:
        fail(f"{len(DATA['timeline'])} timeline items, want 7")
    if len(DATA["map_pins"]) != 16:
        fail(f"{len(DATA['map_pins'])} pins, want 16")
    tags = [c["tag"] for c in DATA["cards"]] + [h["tag"] for h in DATA["heroes"]]
    if len(set(tags)) != len(tags):
        fail(f"duplicate hero/card tags: {tags}")
    if DATA["date_line"] != "TUESDAY, 24 NOVEMBER 2026":
        fail(f"date_line {DATA['date_line']!r}")
    # Cikande framing: never "26 tewas"/"26 killed" anywhere
    blob = json.dumps(DATA, ensure_ascii=False)
    for bad in ("26 tewas", "26 killed", "26 dead", "kills 26"):
        if bad in blob:
            fail(f"forbidden Cikande framing found: {bad!r}")
    ok("43 stories 1..43, ranks 1..10, regions match, 3/12/28/5/7/16, tags unique")
    ok("Cikande framing clean (body bags, not deaths)")

    for p in outs:
        os.remove(p)
    print("VERIFY: ALL PASS")


if __name__ == "__main__":
    main()
