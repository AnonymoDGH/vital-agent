"""Verify rendered PNG screenshots: size, background, accent colors, content density."""
from __future__ import annotations

import os
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
SHOTS = os.path.join(HERE, "..", "assets", "screenshots")


def near(c1, c2, tol=24):
    return all(abs(a - b) <= tol for a, b in zip(c1[:3], c2[:3]))


def analyze(name):
    path = os.path.join(SHOTS, name + ".png")
    img = Image.open(path).convert("RGB")
    w, h = img.size
    px = img.load()

    # sample grid of pixels
    colors = {}
    for y in range(0, h, 4):
        for x in range(0, w, 4):
            c = px[x, y]
            key = (c[0] // 16, c[1] // 16, c[2] // 16)
            colors[key] = colors.get(key, 0) + 1

    total = sum(colors.values())
    dark_bg = sum(v for k, v in colors.items() if near((k[0]*16, k[1]*16, k[2]*16), (13, 17, 23), 40))
    panel_bg = sum(v for k, v in colors.items() if near((k[0]*16, k[1]*16, k[2]*16), (22, 27, 34), 40))
    purple = sum(v for k, v in colors.items() if k[0]*16 > 100 and k[2]*16 > 150 and k[1]*16 < 130)
    green = sum(v for k, v in colors.items() if k[1]*16 > 120 and k[0]*16 < 110 and k[2]*16 < 120)
    red = sum(v for k, v in colors.items() if k[0]*16 > 150 and k[1]*16 < 110 and k[2]*16 < 110)
    bright_text = sum(v for k, v in colors.items() if k[0]*16 > 160 and k[1]*16 > 160 and k[2]*16 > 160)

    print(f"--- {name}.png  {w}x{h} ---")
    print(f"  dark bg (#0d1117-ish): {dark_bg/total:.1%}")
    print(f"  panel bg (#161b22-ish): {panel_bg/total:.1%}")
    print(f"  purple accent: {purple/total:.2%}   green: {green/total:.2%}   red: {red/total:.2%}")
    print(f"  bright text pixels: {bright_text/total:.1%}")
    ok = (
        w >= 1000
        and h >= 600
        and (dark_bg + panel_bg) / total > 0.5
        and bright_text / total > 0.003
        and (purple + green + red) / total > 0.0005  # accent colors must exist
    )
    print(f"  VERDICT: {'OK' if ok else 'SUSPECT'}")
    return ok


def main():
    results = {}
    for name in ("panel", "jobs", "shop", "world"):
        results[name] = analyze(name)
    print()
    print("ALL OK" if all(results.values()) else "SOME SUSPECT")


if __name__ == "__main__":
    main()
