"""The simulation engine: advances the world one tick at a time.

The engine is pure: it mutates only the Agent/WorldState it is given and
reports what happened. No I/O, no timers — the caller (TUI or CLI) decides
when a tick happens.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import List, Optional

from vital.core import events as events_mod
from vital.core.brain import Action, Brain, Decision
from vital.core.economy import TASKS, UPGRADES, market_step
from vital.core.state import Agent, GameConfig, WorldState


@dataclass
class TickReport:
    """Everything that happened during one tick (for UI / logging)."""

    tick: int
    income: float = 0.0
    spent: float = 0.0
    decision: Optional[Decision] = None
    task_completed: Optional[str] = None
    task_reward: float = 0.0
    upgrade_bought: Optional[str] = None
    event_name: Optional[str] = None
    messages: List[str] = field(default_factory=list)
    died: bool = False
    won: bool = False


class Engine:
    """Runs the VITAL simulation."""

    def __init__(self, config: Optional[GameConfig] = None, brain: Optional[Brain] = None):
        self.config = config or GameConfig()
        self.brain = brain or Brain()
        self.rng = random.Random(self.config.seed)
        self.agent = Agent(
            credits=self.config.start_credits,
            energy=self.config.max_energy,
            burn=self.config.burn_per_tick,
        )
        self.world = WorldState()
        self.world.market = market_step({}, self.rng)
        self._apply_upgrades()  # normalize derived stats

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #
    def tick(self) -> TickReport:
        """Advance the simulation by one tick."""
        rep = TickReport(tick=self.world.tick + 1)
        agent, cfg = self.agent, self.config

        if not agent.alive or agent.retired:
            return rep

        agent.age += 1
        self.world.tick += 1

        # 1) market moves + cost-of-living inflation
        self.world.market = market_step(self.world.market, self.rng)
        self._refresh_burn()

        # 2) brain decides
        decision = self.brain.decide(agent, self.world)
        rep.decision = decision

        # 3) execute decision
        if decision.action is Action.WORK and decision.task_id:
            self._do_work(decision.task_id, rep)
        elif decision.action is Action.REST:
            self._do_rest(rep)
        elif decision.action is Action.BUY and decision.upgrade_id:
            self._do_buy(decision.upgrade_id, rep)
        # WAIT: nothing

        # 4) passive income
        if agent.passive_income > 0:
            agent.credits += agent.passive_income
            agent.total_earned += agent.passive_income
            rep.income += agent.passive_income

        # 5) cost of living
        agent.credits -= agent.burn
        rep.spent += agent.burn

        # 6) energy regen (passive)
        agent.energy = min(cfg.max_energy, agent.energy + cfg.energy_regen)

        # 7) mood drifts toward neutral
        agent.mood += (0.7 - agent.mood) * 0.05

        # 8) world event (track any credit delta so history stays accurate)
        credits_before_event = agent.credits
        ev = events_mod.maybe_fire_event(agent, self.world, self.rng, cfg.event_chance)
        if ev:
            rep.event_name = ev.name
            delta = agent.credits - credits_before_event
            if delta > 0:
                rep.income += delta
            elif delta < 0:
                rep.spent += -delta

        # 9) bookkeeping
        self.world.push_history(agent, rep.income)
        self.world.append_log(
            f"[t{self.world.tick}] {decision.reason} "
            f"(+{rep.income:.1f} / -{rep.spent:.1f} ₵)"
        )

        # 10) death / victory checks
        if agent.credits <= 0:
            agent.alive = False
            agent.credits = 0.0
            agent.death_cause = "Se quedó sin créditos vitales"
            rep.died = True
            rep.messages.append("💀 VITAL ha muerto: sin créditos para seguir vivo.")
        elif agent.credits >= cfg.target_credits:
            agent.retired = True
            rep.won = True
            rep.messages.append("🏆 VITAL alcanzó la libertad financiera.")
        elif agent.burn > 0 and agent.passive_income >= agent.burn * cfg.passive_freedom_ratio:
            agent.retired = True
            rep.won = True
            rep.messages.append("🏆 Los ingresos pasivos de VITAL superan su coste de vida. ¡Libre!")

        return rep

    def run(self, ticks: int, on_report=None) -> List[TickReport]:
        """Run many ticks (used by headless mode and tests)."""
        reports = []
        for _ in range(ticks):
            if not self.agent.alive or self.agent.retired:
                break
            rep = self.tick()
            reports.append(rep)
            if on_report:
                on_report(rep)
        return reports

    # ------------------------------------------------------------------ #
    # Internals
    # ------------------------------------------------------------------ #
    def _do_work(self, task_id: str, rep: TickReport) -> None:
        agent, cfg = self.agent, self.config
        task = TASKS[task_id]

        # start or switch task
        if agent.active_task != task_id:
            agent.active_task = task_id
            agent.task_progress = 0

        # spend energy
        cost = task.energy_cost * agent.energy_cost_mult
        agent.energy = max(0.0, agent.energy - cost)

        agent.task_progress += 1
        if agent.task_progress >= task.duration:
            # complete!
            market = self.world.market.get(task.category, 1.0)
            reward = task.base_reward * market * agent.reward_mult
            reward *= 0.9 + agent.mood * 0.2  # mood bonus/penalty
            if self.rng.random() < task.risk:
                reward *= 0.5
                rep.messages.append(f"⚠️ La tarea '{task.name}' salió mal: pago reducido.")
                agent.tasks_failed += 1
            else:
                agent.tasks_done += 1
            reward = round(reward, 2)
            agent.credits += reward
            agent.total_earned += reward
            rep.income += reward
            rep.task_completed = task_id
            rep.task_reward = reward
            # skill grows with harder tasks
            agent.skill += 0.08 + 0.02 * task.duration
            agent.mood = min(1.0, agent.mood + 0.05)
            rep.messages.append(f"✅ '{task.name}' completada: +{reward}₵")
            agent.active_task = None
            agent.task_progress = 0

    def _do_rest(self, rep: TickReport) -> None:
        agent, cfg = self.agent, self.config
        agent.energy = min(cfg.max_energy, agent.energy + cfg.rest_bonus)
        agent.mood = min(1.0, agent.mood + 0.02)
        agent.active_task = None
        agent.task_progress = 0

    def _do_buy(self, upgrade_id: str, rep: TickReport) -> None:
        agent = self.agent
        u = UPGRADES[upgrade_id]
        if upgrade_id in agent.upgrades or agent.credits < u.cost:
            return
        agent.credits -= u.cost
        agent.total_spent += u.cost
        agent.upgrades.append(upgrade_id)
        rep.upgrade_bought = upgrade_id
        rep.spent += u.cost
        if u.kind == "skill":
            agent.skill += u.power
        rep.messages.append(f"🛒 Comprado '{u.name}' ({u.blurb}) por {u.cost}₵")
        self._apply_upgrades()

    def _apply_upgrades(self) -> None:
        """Recompute derived stats from owned upgrades."""
        agent, cfg = self.agent, self.config
        passive = 0.0
        burn_mult = 1.0
        reward_mult = 1.0
        energy_mult = 1.0
        for uid in agent.upgrades:
            u = UPGRADES[uid]
            if u.kind == "passive":
                passive += u.power
            elif u.kind == "burn":
                burn_mult *= 1.0 - u.power
            elif u.kind == "reward":
                reward_mult += u.power
            elif u.kind == "energy":
                energy_mult *= 1.0 - u.power
            elif u.kind == "skill":
                pass  # applied at purchase time
        agent.passive_income = passive
        agent.burn_mult = burn_mult
        self._refresh_burn()
        agent.reward_mult = reward_mult
        agent.energy_cost_mult = energy_mult

    def _refresh_burn(self) -> None:
        """Burn = base * upgrade_mult * inflation. Inflation doubles cost of
        living every `config.inflation` ticks, so standing still means death."""
        agent, cfg = self.agent, self.config
        inflation = 2.0 ** (self.world.tick / cfg.inflation) if cfg.inflation > 0 else 1.0
        agent.burn = max(0.25, cfg.burn_per_tick * agent.burn_mult * inflation)
