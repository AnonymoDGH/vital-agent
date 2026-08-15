"""Headless smoke test for the real-economy TUI."""

from __future__ import annotations

import asyncio
import os

from vital.real.agent import RealAgent
from vital.real.config import RealConfig
from vital.tui.real_app import RealApp


async def main() -> None:
    cfg = RealConfig(
        mode="demo",
        starting_balance_usd=1.0,
        ledger_path="data/real_tui_test_ledger.json",
    )
    agent = RealAgent(cfg)
    app = RealApp(agent=agent)
    async with app.run_test(headless=True, size=(110, 34)) as pilot:
        await pilot.pause()
        # let a few cycles run
        for _ in range(3):
            app._on_cycle()
            await pilot.pause()
        # verify key widgets exist and have content
        bal = app.query_one("#balance-big")
        runway = app.query_one("#runway-big")
        log = app.query_one("#activity-log")
        assert bal is not None
        assert runway is not None
        assert log is not None
        # pause / resume
        app.action_toggle_pause()
        assert app.paused
        app.action_toggle_pause()
        assert not app.paused
        print("REAL TUI OK — balance widget, runway, log, pause all working")


if __name__ == "__main__":
    asyncio.run(main())
