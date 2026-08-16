"""Capture a screenshot of the real-economy TUI as SVG (Cursor-AI theme)."""

from __future__ import annotations

import asyncio
import os

from vital.real.agent import RealAgent
from vital.real.config import RealConfig
from vital.tui.real_app import RealApp

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                   "assets", "screenshots", "real.svg")


async def main() -> None:
    cfg = RealConfig(
        mode="demo",
        starting_balance_usd=1.0,
        ledger_path="data/real_shot_ledger.json",
    )
    agent = RealAgent(cfg)
    # run a few cycles so the log has content
    agent.run(8)

    app = RealApp(agent=agent)
    async with app.run_test(headless=True, size=(110, 34)) as pilot:
        await pilot.pause()
        app._refresh()
        await pilot.pause()
        svg = app.export_screenshot()
        os.makedirs(os.path.dirname(OUT), exist_ok=True)
        with open(OUT, "w", encoding="utf-8") as f:
            f.write(svg if isinstance(svg, str) else svg.data)
        print("saved", OUT)


if __name__ == "__main__":
    asyncio.run(main())
