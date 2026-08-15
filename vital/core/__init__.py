"""Core simulation engine for VITAL (pure logic, no I/O)."""

from vital.core.state import Agent, GameConfig, TaskDef, Upgrade, WorldState
from vital.core.engine import Engine, TickReport
from vital.core.economy import TASKS, UPGRADES, market_step
from vital.core.brain import Brain, Action
from vital.core import events, persistence, formatting

__all__ = [
    "Agent",
    "GameConfig",
    "TaskDef",
    "Upgrade",
    "WorldState",
    "Engine",
    "TickReport",
    "TASKS",
    "UPGRADES",
    "market_step",
    "Brain",
    "Action",
    "events",
    "persistence",
    "formatting",
]
