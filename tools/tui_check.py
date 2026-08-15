"""Manual verification script: run the TUI headless and capture screenshots.

Usage:
    python tools/tui_check.py
"""
from __future__ import annotations

import asyncio
import os
import sys

# ensure repo root on path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from vital.core.engine import Engine
from vital.core.state import GameConfig
from vital.tui.app import VitalApp

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", "screenshots")
os.makedirs(OUT, exist_ok=True)


async def main() -> None:
    engine = Engine(config=GameConfig(seed=7))
    app = VitalApp(engine=engine)

    async with app.run_test(size=(120, 36), headless=True) as pilot:
        await pilot.pause()
        # run a bunch of ticks manually so there is history
        for _ in range(40):
            app._on_tick()
        app._refresh_all()
        await pilot.pause()

        svg = app.export_screenshot(title="VITAL — Panel")
        with open(os.path.join(OUT, "panel.svg"), "w", encoding="utf-8") as f:
            f.write(svg)
        print("saved panel.svg")

        # switch to jobs tab
        app.action_tab_jobs()
        await pilot.pause()
        svg = app.export_screenshot(title="VITAL — Trabajos")
        with open(os.path.join(OUT, "jobs.svg"), "w", encoding="utf-8") as f:
            f.write(svg)
        print("saved jobs.svg")

        # shop tab
        app.action_tab_shop()
        await pilot.pause()
        svg = app.export_screenshot(title="VITAL — Tienda")
        with open(os.path.join(OUT, "shop.svg"), "w", encoding="utf-8") as f:
            f.write(svg)
        print("saved shop.svg")

        # world tab
        app.action_tab_world()
        await pilot.pause()
        svg = app.export_screenshot(title="VITAL — Mundo")
        with open(os.path.join(OUT, "world.svg"), "w", encoding="utf-8") as f:
            f.write(svg)
        print("saved world.svg")

    print("TUI smoke test OK")


if __name__ == "__main__":
    asyncio.run(main())
