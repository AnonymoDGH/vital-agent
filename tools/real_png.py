"""Convert real.svg -> real.png via Edge headless (no cairosvg on Windows)."""
from __future__ import annotations

import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SHOTS = os.path.join(HERE, "..", "assets", "screenshots")
SVG = os.path.join(SHOTS, "real.svg")
PNG = os.path.join(SHOTS, "real.png")


def main() -> int:
    svg = open(SVG, encoding="utf-8").read()
    m = re.search(r'viewBox="([^"]+)"', svg)
    if not m:
        print("no viewBox found")
        return 1
    parts = m.group(1).split()
    w, h = float(parts[2]), float(parts[3])
    print("viewBox:", m.group(1), "-> w,h:", w, h)

    # Inject explicit width/height so the browser renders at full size.
    first_tag_end = svg.find(">")
    if "width=" not in svg[:first_tag_end]:
        svg = svg.replace("<svg ", f'<svg width="{int(w)}" height="{int(h)}" ', 1)

    sized = os.path.join(SHOTS, "real_sized.svg")
    open(sized, "w", encoding="utf-8").write(svg)

    html = (
        "<html><head><style>body{margin:0;background:#0d1117}</style></head>"
        "<body>" + svg + "</body></html>"
    )
    html_path = os.path.join(SHOTS, "real.html")
    open(html_path, "w", encoding="utf-8").write(html)

    # Locate Edge.
    edge_candidates = [
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    ]
    edge = next((p for p in edge_candidates if os.path.exists(p)), None)
    if not edge:
        print("Edge not found")
        return 1

    cmd = [
        edge,
        "--headless=new",
        "--disable-gpu",
        "--no-sandbox",
        f"--screenshot={PNG}",
        f"--window-size={int(w)},{int(h)}",
        "--hide-scrollbars",
        "--default-background-color=FF0D1117",
        "file:///" + html_path.replace("\\", "/"),
    ]
    print("running Edge headless...")
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    if os.path.exists(PNG):
        print("PNG written:", PNG, os.path.getsize(PNG), "bytes")
        return 0
    print("PNG not produced. stderr:", r.stderr[-500:])
    return 1


if __name__ == "__main__":
    sys.exit(main())
