"""Engine tests: life, death, work, economy invariants."""

from __future__ import annotations

import pytest

from vital.core.brain import Action, Brain
from vital.core.economy import TASKS, UPGRADES, market_step
from vital.core.engine import Engine
from vital.core.state import Agent, GameConfig, WorldState
import random


def make_engine(seed=42, **cfg_kwargs) -> Engine:
    return Engine(config=GameConfig(seed=seed, **cfg_kwargs))


# --------------------------------------------------------------------------- #
# Basic invariants
# --------------------------------------------------------------------------- #
def test_engine_starts_alive_with_configured_credits():
    e = make_engine(start_credits=100.0)
    assert e.agent.alive
    assert e.agent.credits == 100.0
    assert e.agent.energy == e.config.max_energy


def test_tick_advances_world_and_age():
    e = make_engine()
    e.tick()
    assert e.world.tick == 1
    assert e.agent.age == 1


def test_burn_reduces_credits_when_idle():
    """An agent that never earns must bleed credits."""
    # inflation=0 so the burn is exactly the configured value
    e = make_engine(start_credits=50.0, burn_per_tick=2.0, inflation=0.0)

    class DoNothing(Brain):
        def decide(self, agent, world):
            from vital.core.brain import Decision
            return Decision(Action.WAIT, reason="test")

    e.brain = DoNothing()
    e.tick()
    # only burn applied (no passive income)
    assert e.agent.credits == pytest.approx(48.0, abs=0.001)


def test_death_when_credits_hit_zero():
    e = make_engine(start_credits=3.0, burn_per_tick=2.0, event_chance=0.0)

    class DoNothing(Brain):
        def decide(self, agent, world):
            from vital.core.brain import Decision
            return Decision(Action.WAIT, reason="test")

    e.brain = DoNothing()
    reports = e.run(10)
    assert not e.agent.alive
    assert e.agent.credits == 0.0
    assert any(r.died for r in reports)
    assert e.agent.death_cause


def test_no_ticks_after_death():
    e = make_engine(start_credits=1.0, burn_per_tick=2.0, event_chance=0.0)

    class DoNothing(Brain):
        def decide(self, agent, world):
            from vital.core.brain import Decision
            return Decision(Action.WAIT, reason="test")

    e.brain = DoNothing()
    e.run(5)
    tick_at_death = e.world.tick
    e.tick()  # should be a no-op
    assert e.world.tick == tick_at_death


# --------------------------------------------------------------------------- #
# Work & rewards
# --------------------------------------------------------------------------- #
def test_working_earns_credits():
    e = make_engine(start_credits=100.0, event_chance=0.0)

    class WorkMicro(Brain):
        def decide(self, agent, world):
            from vital.core.brain import Decision
            return Decision(Action.WORK, task_id="micro", reason="test")

    e.brain = WorkMicro()
    before = e.agent.credits
    e.run(3)
    assert e.agent.tasks_done >= 1
    # Each completed micro task must pay a meaningful reward (base 8₵ scaled by
    # market/mood, possibly halved by risk). A broken ~0₵ reward would fail this.
    assert e.agent.total_earned >= e.agent.tasks_done * 2.0


def test_task_progress_completes_after_duration():
    e = make_engine(start_credits=100.0, event_chance=0.0)

    class WorkMicro(Brain):
        def decide(self, agent, world):
            from vital.core.brain import Decision
            return Decision(Action.WORK, task_id="data", reason="test")

    e.brain = WorkMicro()
    e.tick()
    assert e.agent.active_task == "data"
    assert e.agent.task_progress == 1
    e.tick()  # duration=2 -> completes
    assert e.agent.tasks_done == 1
    assert e.agent.active_task is None


def test_rest_recovers_energy():
    """Resting must add the explicit rest bonus (not just passive regen)."""
    # energy_regen=0 so ONLY the rest bonus can raise energy
    e = make_engine(energy_regen=0.0, rest_bonus=16.0)
    e.agent.energy = 10.0

    class Rest(Brain):
        def decide(self, agent, world):
            from vital.core.brain import Decision
            return Decision(Action.REST, reason="test")

    e.brain = Rest()
    e.tick()
    # exactly the rest bonus, since passive regen is disabled
    assert e.agent.energy == pytest.approx(26.0, abs=0.01)


def test_rest_beats_passive_regen():
    """Resting must recover strictly more than idling (the rest bonus matters)."""
    e_rest = make_engine(energy_regen=8.0, rest_bonus=16.0)
    e_idle = make_engine(energy_regen=8.0, rest_bonus=16.0)
    e_rest.agent.energy = 20.0
    e_idle.agent.energy = 20.0

    class Rest(Brain):
        def decide(self, agent, world):
            from vital.core.brain import Decision
            return Decision(Action.REST, reason="test")

    class DoNothing(Brain):
        def decide(self, agent, world):
            from vital.core.brain import Decision
            return Decision(Action.WAIT, reason="test")

    e_rest.brain = Rest()
    e_idle.brain = DoNothing()
    e_rest.tick()
    e_idle.tick()
    assert e_rest.agent.energy > e_idle.agent.energy


def test_energy_capped_at_max():
    e = make_engine()
    e.agent.energy = e.config.max_energy

    class Rest(Brain):
        def decide(self, agent, world):
            from vital.core.brain import Decision
            return Decision(Action.REST, reason="test")

    e.brain = Rest()
    e.run(5)
    assert e.agent.energy == e.config.max_energy


# --------------------------------------------------------------------------- #
# Upgrades
# --------------------------------------------------------------------------- #
def test_buying_passive_upgrade_adds_income():
    e = make_engine(start_credits=500.0, event_chance=0.0)
    e.agent.credits = 500.0
    e._do_buy("bot1", _rep(e))
    assert "bot1" in e.agent.upgrades
    assert e.agent.passive_income == pytest.approx(1.5)


def _rep(e):
    from vital.core.engine import TickReport
    return TickReport(tick=0)


def test_burn_upgrade_reduces_burn():
    e = make_engine(start_credits=500.0, inflation=0.0)
    base_burn = e.config.burn_per_tick
    e._do_buy("solar", _rep(e))
    assert e.agent.burn == pytest.approx(base_burn * 0.75)


def test_cannot_buy_without_credits():
    e = make_engine(start_credits=10.0)
    e._do_buy("bot3", _rep(e))  # costs 900
    assert "bot3" not in e.agent.upgrades


def test_cannot_buy_twice():
    e = make_engine(start_credits=1000.0)
    e._do_buy("bot1", _rep(e))
    credits_after_first = e.agent.credits
    e._do_buy("bot1", _rep(e))
    assert e.agent.credits == credits_after_first
    assert e.agent.upgrades.count("bot1") == 1


# --------------------------------------------------------------------------- #
# Market
# --------------------------------------------------------------------------- #
def test_market_step_initializes_and_clamps():
    rng = random.Random(0)
    m = market_step({}, rng)
    assert set(m.keys()) == {"gig", "service", "dev", "enterprise"}
    for _ in range(500):
        m = market_step(m, rng)
    for v in m.values():
        assert 0.6 <= v <= 1.8


# --------------------------------------------------------------------------- #
# Brain
# --------------------------------------------------------------------------- #
def test_brain_prefers_fast_task_when_dying():
    """When near death with enough energy, the brain must WORK a short task."""
    e = make_engine(start_credits=10.0, burn_per_tick=2.0)
    e.agent.energy = e.config.max_energy  # plenty of energy
    d = e.brain.decide(e.agent, e.world)
    assert d.action == Action.WORK
    # the emergency pick should be a short task (duration <= 2)
    assert TASKS[d.task_id].duration <= 2


def test_brain_works_when_healthy():
    """A healthy agent with energy should choose to work, not wait."""
    e = make_engine(start_credits=200.0)
    e.agent.energy = e.config.max_energy
    d = e.brain.decide(e.agent, e.world)
    assert d.action in (Action.WORK, Action.BUY)


def test_brain_rests_when_no_energy():
    e = make_engine()
    e.agent.energy = 0.0
    d = e.brain.decide(e.agent, e.world)
    assert d.action == Action.REST


def test_brain_respects_skill_gates():
    brain = Brain()
    e = make_engine()
    e.agent.skill = 1.0
    task = brain._pick_task(e.agent, e.world, prefer_fast=False)
    assert task in ("micro", "data")  # only ones without high gates


# --------------------------------------------------------------------------- #
# Long-run survival (the core promise: earn or die)
# --------------------------------------------------------------------------- #
def test_agent_survives_long_run_with_default_brain():
    """With a sane brain the agent should not die immediately."""
    e = make_engine(seed=7, start_credits=120.0)
    e.run(150)
    assert e.agent.alive or e.agent.retired
    assert e.agent.total_earned > 0


def test_history_is_recorded():
    e = make_engine()
    e.run(10)
    assert len(e.world.history_credits) == 10
    assert len(e.world.history_income) == 10
    assert len(e.world.history_runway) == 10


def test_runway_property():
    a = Agent(credits=100.0, burn=2.0)
    assert a.runway == pytest.approx(50.0)
    a.burn = 0.0
    assert a.runway == float("inf")
