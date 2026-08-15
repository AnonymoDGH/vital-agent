"""Balance tests: the 'earn or die' promise must hold across seeds."""

from __future__ import annotations

import pytest

from vital.core.engine import Engine
from vital.core.state import GameConfig


def test_inflation_increases_burn_over_time():
    e = Engine(config=GameConfig(seed=1, inflation=100.0))
    burn_start = e.agent.burn
    e.world.tick = 100  # one doubling period
    e._refresh_burn()
    assert e.agent.burn == pytest.approx(burn_start * 2.0, rel=0.01)


def test_inflation_disabled_keeps_burn_flat():
    e = Engine(config=GameConfig(seed=1, inflation=0.0))
    burn_start = e.agent.burn
    e.world.tick = 5000
    e._refresh_burn()
    assert e.agent.burn == pytest.approx(burn_start, rel=0.01)


def test_burn_upgrade_still_reduces_burn_under_inflation():
    e = Engine(config=GameConfig(seed=1, inflation=0.0))
    e.agent.credits = 500.0  # enough to afford solar (150)
    base_burn = e.config.burn_per_tick
    from vital.core.engine import TickReport
    e._do_buy("solar", TickReport(tick=0))
    assert e.agent.burn == pytest.approx(base_burn * 0.75, rel=0.01)


def test_default_agent_survives_early_game():
    """The agent must not die in the first 50 ticks with default settings."""
    e = Engine(config=GameConfig(seed=5))
    e.run(50)
    assert e.agent.alive


def test_earn_or_die_distribution():
    """Over many seeds we expect a mix of wins and deaths — not all one.

    This is the core promise: the agent must genuinely risk death.
    """
    wins = deaths = 0
    for seed in range(25):
        e = Engine(config=GameConfig(seed=seed))
        e.run(1500)
        if e.agent.retired:
            wins += 1
        elif not e.agent.alive:
            deaths += 1
    # We want both outcomes to be possible.
    assert wins > 0, "agent never wins — too hard"
    assert deaths > 0, "agent never dies — no real risk"


def test_passive_income_can_reach_freedom():
    """Buying all passive bots + burn reducers should exceed the freedom threshold."""
    e = Engine(config=GameConfig(seed=1, inflation=0.0))
    e.agent.credits = 100_000.0
    from vital.core.engine import TickReport
    for uid in ("bot1", "bot2", "bot3", "solar", "frugal"):
        e._do_buy(uid, TickReport(tick=0))
    total_passive = e.agent.passive_income
    assert total_passive >= e.agent.burn * e.config.passive_freedom_ratio
