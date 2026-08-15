"""Persistence tests: save/load round-trip."""

from __future__ import annotations

import os

from vital.core import persistence
from vital.core.engine import Engine
from vital.core.state import GameConfig


def test_save_load_roundtrip(tmp_path):
    path = str(tmp_path / "save.json")
    e = Engine(config=GameConfig(seed=1, start_credits=77.0))
    e.run(5)

    persistence.save_engine(e, path)
    assert os.path.exists(path)

    loaded = persistence.load_engine(path)
    assert loaded is not None
    assert loaded.agent.credits == e.agent.credits
    assert loaded.agent.age == e.agent.age
    assert loaded.world.tick == e.world.tick
    assert loaded.agent.upgrades == e.agent.upgrades
    assert loaded.world.history_credits == e.world.history_credits


def test_load_missing_returns_none(tmp_path):
    assert persistence.load_engine(str(tmp_path / "nope.json")) is None


def test_load_corrupt_returns_none(tmp_path):
    path = str(tmp_path / "bad.json")
    with open(path, "w", encoding="utf-8") as f:
        f.write("{not valid json")
    assert persistence.load_engine(path) is None


def test_clear_save(tmp_path):
    path = str(tmp_path / "save.json")
    e = Engine(config=GameConfig(seed=1))
    persistence.save_engine(e, path)
    assert os.path.exists(path)
    persistence.clear_save(path)
    assert not os.path.exists(path)
