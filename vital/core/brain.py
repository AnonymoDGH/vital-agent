"""The agent's brain: a small utility-based policy that decides what to do.

The brain is deliberately simple and readable — it is the "personality" of
the agent. It looks at its own runway (ticks of life left), energy, skill and
the market, then picks an action.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional

from vital.core.economy import SHOP_ORDER, TASKS, UPGRADES
from vital.core.state import Agent, WorldState


class Action(str, Enum):
    WORK = "work"        # start/continue a task
    REST = "rest"        # recover energy
    BUY = "buy"          # buy an upgrade
    WAIT = "wait"        # do nothing (rare)


@dataclass
class Decision:
    action: Action
    task_id: Optional[str] = None
    upgrade_id: Optional[str] = None
    reason: str = ""


class Brain:
    """Utility-based decision maker."""

    def __init__(self, risk_tolerance: float = 0.5):
        self.risk_tolerance = risk_tolerance

    # ------------------------------------------------------------------ #
    def decide(self, agent: Agent, world: WorldState) -> Decision:
        runway = agent.runway

        # 1) Survival first: if we are about to die, grab the fastest money.
        if runway < 12:
            task = self._pick_task(agent, world, prefer_fast=True)
            if task and agent.energy >= self._energy_for(task):
                return Decision(Action.WORK, task_id=task, reason="¡Emergencia! Necesito dinero YA")
            return Decision(Action.REST, reason="Sin energía para trabajar; descanso para no morir")

        # 2) Low energy -> rest so we can keep working later.
        if agent.energy < 25:
            return Decision(Action.REST, reason="Energía baja, recargando")

        # 3) Invest in passive income when it is safe and useful.
        upgrade = self._pick_upgrade(agent, runway)
        if upgrade:
            return Decision(Action.BUY, upgrade_id=upgrade, reason="Invierto en ingresos pasivos")

        # 4) Otherwise work: pick the best value task we can do.
        task = self._pick_task(agent, world, prefer_fast=False)
        if task and agent.energy >= self._energy_for(task):
            return Decision(Action.WORK, task_id=task, reason="Trabajo para ganar créditos")

        # 5) Fallback: rest.
        return Decision(Action.REST, reason="Nada rentable disponible; descanso")

    # ------------------------------------------------------------------ #
    def _energy_for(self, task_id: str) -> float:
        t = TASKS[task_id]
        return t.energy_cost * t.duration * 0.6  # enough to make real progress

    def _pick_task(self, agent: Agent, world: WorldState, prefer_fast: bool) -> Optional[str]:
        best: Optional[str] = None
        best_score = -1.0
        for tid, t in TASKS.items():
            if t.skill_gate > agent.skill:
                continue
            if agent.energy < t.energy_cost:
                continue
            market = world.market.get(t.category, 1.0)
            reward = t.base_reward * market * agent.reward_mult
            per_tick = reward / max(1, t.duration)
            # risk-adjusted
            per_tick *= 1.0 - t.risk * 0.5
            if prefer_fast:
                # favour short tasks when desperate
                per_tick /= max(1, t.duration)
            score = per_tick
            if score > best_score:
                best_score = score
                best = tid
        return best

    def _pick_upgrade(self, agent: Agent, runway: float) -> Optional[str]:
        # Only invest when we have a comfortable buffer.
        if runway < 30:
            return None
        for uid in SHOP_ORDER:
            u = UPGRADES[uid]
            if uid in agent.upgrades:
                continue
            # keep a safety margin after buying
            if agent.credits - u.cost < agent.burn * 15:
                continue
            # passive income upgrades are the priority
            if u.kind == "passive":
                return uid
            # burn reduction when burn is high relative to income
            if u.kind == "burn" and agent.burn >= 1.5:
                return uid
            if u.kind == "reward" and agent.tasks_done >= 3:
                return uid
            if u.kind == "skill" and agent.skill < 6:
                return uid
            if u.kind == "energy":
                return uid
        return None
