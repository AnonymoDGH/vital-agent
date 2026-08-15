"""Save / load the simulation state as JSON."""

from __future__ import annotations

import json
import os
from dataclasses import asdict
from typing import Optional

from vital.core.brain import Brain
from vital.core.engine import Engine
from vital.core.state import Agent, GameConfig, WorldState

SAVE_VERSION = 1


def default_save_path() -> str:
    """Where the agent's life is persisted by default."""
    base = os.environ.get("VITAL_DATA_DIR")
    if base:
        os.makedirs(base, exist_ok=True)
        return os.path.join(base, "save.json")
    here = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    data = os.path.join(here, "data")
    os.makedirs(data, exist_ok=True)
    return os.path.join(data, "save.json")


def save_engine(engine: Engine, path: Optional[str] = None) -> str:
    path = path or default_save_path()
    payload = {
        "version": SAVE_VERSION,
        "config": asdict(engine.config),
        "agent": asdict(engine.agent),
        "world": asdict(engine.world),
    }
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)
    return path


def load_engine(path: Optional[str] = None) -> Optional[Engine]:
    path = path or default_save_path()
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            payload = json.load(f)
        if payload.get("version") != SAVE_VERSION:
            return None
        config = GameConfig(**payload["config"])
        engine = Engine(config=config, brain=Brain())
        engine.agent = Agent(**payload["agent"])
        engine.world = WorldState(**payload["world"])
        return engine
    except (json.JSONDecodeError, TypeError, KeyError, ValueError):
        return None


def clear_save(path: Optional[str] = None) -> None:
    path = path or default_save_path()
    if os.path.exists(path):
        os.remove(path)
