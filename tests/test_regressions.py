"""Regression tests for bugs found in code review (M1–M6)."""

from __future__ import annotations

import json

import pytest

from vital.core import persistence
from vital.core.brain import Action, Brain
from vital.core.economy import TASKS
from vital.core.engine import Engine
from vital.core.state import GameConfig


# --------------------------------------------------------------------------- #
# M1: stale derived economics after load must be recomputed
# --------------------------------------------------------------------------- #
def test_load_recomputes_economics_from_upgrades(tmp_path):
    path = str(tmp_path / "save.json")
    e = Engine(config=GameConfig(seed=1))
    e.agent.upgrades = ["bot1"]
    e.agent.passive_income = 17.0  # deliberately stale
    e.agent.burn = 0.5             # deliberately stale
    persistence.save_engine(e, path)

    loaded = persistence.load_engine(path)
    assert loaded is not None
    assert loaded.agent.passive_income == pytest.approx(1.5)
    assert loaded.agent.burn == pytest.approx(e.config.burn_per_tick)


# --------------------------------------------------------------------------- #
# M2: log must not freeze once the in-memory cap is hit
# --------------------------------------------------------------------------- #
def test_log_total_is_monotonic_past_cap():
    e = Engine(config=GameConfig(seed=7))
    for _ in range(450):
        if not e.agent.alive or e.agent.retired:
            break
        e.tick()
    assert e.world.log_total >= len(e.world.log)
    assert len(e.world.log) <= e.world.LOG_CAP
    # every line is still reachable via the monotonic counter
    assert e.world.log_total > e.world.LOG_CAP


def test_incremental_display_never_loses_lines():
    e = Engine(config=GameConfig(seed=7))
    last_total = 0
    displayed = 0
    for _ in range(450):
        if not e.agent.alive or e.agent.retired:
            break
        e.tick()
        new_lines = e.world.log_total - last_total
        displayed += new_lines
        last_total = e.world.log_total
    assert displayed == e.world.log_total


# --------------------------------------------------------------------------- #
# M3: brain energy gate must be consistent with _energy_for
# --------------------------------------------------------------------------- #
def test_brain_energy_gate_consistent():
    b = Brain()
    e = Engine(config=GameConfig(seed=1))
    threshold = b._energy_for("micro")
    e.agent.energy = threshold + 0.1
    e.agent.credits = 5.0  # desperate -> emergency branch
    d = b.decide(e.agent, e.world)
    assert d.action == Action.WORK
    assert d.task_id == "micro"


# --------------------------------------------------------------------------- #
# M4: schema drift must not silently discard the save
# --------------------------------------------------------------------------- #
def test_load_tolerates_schema_drift(tmp_path):
    path = str(tmp_path / "save.json")
    e = Engine(config=GameConfig(seed=1))
    e.run(3)
    persistence.save_engine(e, path)

    with open(path, "r", encoding="utf-8") as f:
        payload = json.load(f)
    payload["agent"]["some_future_field"] = 999  # extra key
    del payload["agent"]["mood"]                 # missing key
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f)

    loaded = persistence.load_engine(path)
    assert loaded is not None
    assert loaded.agent.mood == 0.7  # dataclass default


# --------------------------------------------------------------------------- #
# M5: stale active_task id must not KeyError
# --------------------------------------------------------------------------- #
def test_stale_active_task_cleared_on_load(tmp_path):
    path = str(tmp_path / "save.json")
    e = Engine(config=GameConfig(seed=1))
    e.agent.active_task = "nonexistent_task"
    e.agent.task_progress = 3
    persistence.save_engine(e, path)

    loaded = persistence.load_engine(path)
    assert loaded.agent.active_task is None
    assert loaded.agent.task_progress == 0
    loaded.tick()  # must not raise


# --------------------------------------------------------------------------- #
# M6: event income must reach rep.income / history
# --------------------------------------------------------------------------- #
def test_event_income_tracked():
    e = Engine(config=GameConfig(seed=7, event_chance=1.0))
    saw = False
    for _ in range(80):
        if not e.agent.alive or e.agent.retired:
            break
        rep = e.tick()
        if rep.event_name in ("Propina", "Bono", "Créditos encontrados") and rep.income > 0:
            saw = True
            break
    assert saw, "event income never reached rep.income"
