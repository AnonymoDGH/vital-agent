"""Save / load the simulation state as JSON."""

from __future__ import annotations

import dataclasses
import json
import os
from dataclasses import asdict, fields
from typing import Optional

from vital.core.brain import Brain
from vital.core.economy import TASKS
from vital.core.engine import Engine
from vital.core.state import Agent, GameConfig, WorldState

SAVE_VERSION = 1


def _filter_fields(dc_cls, data: dict) -> dict:
    """Keep only keys that are real fields of the dataclass.

    This makes loading tolerant of schema drift: extra keys are dropped and
    missing keys fall back to the dataclass defaults instead of raising.
    """
    valid = {f.name for f in fields(dc_cls)}
    return {k: v for k, v in data.items() if k in valid}


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
        config = GameConfig(**_filter_fields(GameConfig, payload["config"]))
        engine = Engine(config=config, brain=Brain())
        engine.agent = Agent(**_filter_fields(Agent, payload["agent"]))
        engine.world = WorldState(**_filter_fields(WorldState, payload["world"]))
        # Recompute derived economics from owned upgrades. The saved values may
        # be stale (e.g. if the economy was retuned since the save was written),
        # so never trust them blindly.
        engine._apply_upgrades()
        # A saved active_task may reference a task id that no longer exists.
        if engine.agent.active_task not in TASKS:
            engine.agent.active_task = None
            engine.agent.task_progress = 0
        return engine
    except (json.JSONDecodeError, TypeError, KeyError, ValueError) as exc:
        # Surface the problem instead of silently discarding the save.
        import sys

        print(f"[vital] no se pudo cargar la partida '{path}': {exc}", file=sys.stderr)
        return None


def clear_save(path: Optional[str] = None) -> None:
    path = path or default_save_path()
    if os.path.exists(path):
        os.remove(path)
