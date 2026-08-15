"""Data model for the VITAL simulation.

Everything here is a plain dataclass so the engine stays deterministic,
serializable and trivially testable.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


# --------------------------------------------------------------------------- #
# Configuration
# --------------------------------------------------------------------------- #
@dataclass
class GameConfig:
    """Tuning knobs for a VITAL run."""

    start_credits: float = 80.0       # life-credit the agent is born with
    burn_per_tick: float = 2.0        # cost of staying alive each tick
    max_energy: float = 100.0
    energy_regen: float = 8.0         # passive energy recovery per tick
    rest_bonus: float = 16.0          # extra recovery when actively resting
    target_credits: float = 6_000.0   # "financial freedom" => win
    passive_freedom_ratio: float = 8.0  # passive income >= burn * ratio => win
    event_chance: float = 0.20        # probability of a world event per tick
    inflation: float = 300.0          # burn doubles every this many ticks
    seed: Optional[int] = None        # None => random run


# --------------------------------------------------------------------------- #
# Economy definitions
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class TaskDef:
    """A kind of job the agent can perform."""

    id: str
    name: str
    icon: str
    duration: int          # ticks needed to complete
    base_reward: float     # credits before market multiplier
    energy_cost: float     # energy spent per tick while working
    risk: float            # 0..1 chance the payout is halved
    skill_gate: float = 0.0  # minimum skill level required
    category: str = "general"


@dataclass(frozen=True)
class Upgrade:
    """A permanent purchase that changes the agent's economics."""

    id: str
    name: str
    icon: str
    cost: float
    blurb: str
    kind: str  # "passive" | "burn" | "reward" | "energy" | "skill"
    power: float  # meaning depends on kind


# --------------------------------------------------------------------------- #
# Agent
# --------------------------------------------------------------------------- #
@dataclass
class Agent:
    """The living agent. `credits` is literally its remaining life."""

    name: str = "VITAL-01"
    credits: float = 120.0
    energy: float = 100.0
    skill: float = 1.0
    mood: float = 0.7          # 0..1, cosmetic but affects rewards a bit
    age: int = 0               # ticks lived
    alive: bool = True
    retired: bool = False      # won the game
    death_cause: str = ""

    # current job
    active_task: Optional[str] = None
    task_progress: int = 0

    # owned upgrade ids
    upgrades: list[str] = field(default_factory=list)

    # lifetime stats
    total_earned: float = 0.0
    total_spent: float = 0.0
    tasks_done: int = 0
    tasks_failed: int = 0

    # derived economics (recomputed each tick)
    burn: float = 2.0
    burn_mult: float = 1.0        # from upgrades; inflation applied on top
    passive_income: float = 0.0
    reward_mult: float = 1.0
    energy_cost_mult: float = 1.0

    @property
    def runway(self) -> float:
        """Ticks left to live if income stopped right now."""
        if self.burn <= 0:
            return float("inf")
        return self.credits / self.burn

    @property
    def net_per_tick(self) -> float:
        return self.passive_income - self.burn


# --------------------------------------------------------------------------- #
# World
# --------------------------------------------------------------------------- #
@dataclass
class WorldState:
    """Market conditions and history that outlive a single task."""

    tick: int = 0
    market: dict[str, float] = field(default_factory=dict)  # category -> multiplier
    history_credits: list[float] = field(default_factory=list)
    history_income: list[float] = field(default_factory=list)
    history_runway: list[float] = field(default_factory=list)
    log: list[str] = field(default_factory=list)

    def push_history(self, agent: Agent, income: float) -> None:
        self.history_credits.append(round(agent.credits, 2))
        self.history_income.append(round(income, 2))
        self.history_runway.append(round(agent.runway, 2))
        # keep bounded
        cap = 512
        if len(self.history_credits) > cap:
            self.history_credits = self.history_credits[-cap:]
            self.history_income = self.history_income[-cap:]
            self.history_runway = self.history_runway[-cap:]
