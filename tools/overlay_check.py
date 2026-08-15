"""Capture death and victory overlay states of the TUI."""
from __future__ import annotations

import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from vital.core.engine import Engine
from vital.core.state import GameConfig
from vital.tui.app import VitalApp

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", "screenshots")
os.makedirs(OUT, exist_ok=True)


async def capture(name: str, seed: int, force: str) -> None:
    engine = Engine(config=GameConfig(seed=seed))
    app = VitalApp(engine=engine)
    async with app.run_test(size=(120, 36), headless=True) as pilot:
        await pilot.pause()
        for _ in range(10):
            app._on_tick()
        # force the terminal state
        if force == "death":
            app.engine.agent.credits = 0.0
            app.engine.agent.alive = False
            app.engine.agent.death_cause = "Se quedó sin créditos vitales"
            app._show_overlay(died=True)
        else:
            app.engine.agent.retired = True
            app.engine.agent.credits = 6200.0
            app.engine.agent.passive_income = 17.0
            app._show_overlay(died=False)
        app._refresh_all()
        await pilot.pause()
        svg = app.export_screenshot(title=f"VITAL — {name}")
        with open(os.path.join(OUT, name + ".svg"), "w", encoding="utf-8") as f:
            f.write(svg)
        print("saved", name + ".svg")


async def main() -> None:
    await capture("death", 7, "death")
    await capture("victory", 7, "victory")
    print("overlay capture OK")


if __name__ == "__main__":
    asyncio.run(main())
