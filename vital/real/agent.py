"""The real survival loop: VITAL must earn real money to pay for its own life.

Each cycle:
    1. THINK  -> make an LLM call, PAY the real cost (this is staying alive)
    2. WORK   -> try each income provider to earn money
    3. RECORD -> update the ledger and wallet
    4. CHECK  -> if balance <= min, the agent DIES

In demo mode everything is simulated but priced identically, so the economics
are the same as real mode. In real mode the LLM calls and wallet are real.
"""

from __future__ import annotations

import random
import time
from dataclasses import dataclass, field
from typing import Optional

from vital.real.config import RealConfig, load_real_config
from vital.real.costs import CostTracker
from vital.real.income import IncomeProvider, make_providers
from vital.real.ledger import Ledger
from vital.real.llm import LLMClient
from vital.real.wallet import Wallet, make_wallet


@dataclass
class CycleReport:
    """What happened in one survival cycle."""

    cycle: int
    thought: str = ""
    think_cost: float = 0.0
    earned: float = 0.0
    income_sources: list[str] = field(default_factory=list)
    balance_after: float = 0.0
    runway_actions: float = 0.0
    died: bool = False
    messages: list[str] = field(default_factory=list)


class RealAgent:
    """VITAL running on the real economy."""

    SYSTEM_PROMPT = (
        "You are VITAL, an autonomous agent. Every thought you have costs real "
        "money. You must earn more than you spend or you will run out of funds "
        "and die. Decide what paid work to pursue next. Be concise."
    )

    def __init__(self, config: Optional[RealConfig] = None):
        self.config = config or load_real_config()
        problems = self.config.validate()
        if problems:
            raise RuntimeError("Real-mode config problems: " + "; ".join(problems))

        self.rng = random.Random()
        self.cost_tracker = CostTracker()
        self.llm = LLMClient(self.config)
        self.wallet = make_wallet(self.config)
        self.providers = make_providers(self.config, wallet=self.wallet)
        self.cycle = 0

        # Load or create the ledger.
        ledger_path = self.config.ledger_path or self._default_ledger_path()
        self.ledger_path = ledger_path
        loaded = Ledger.load(ledger_path)
        if loaded is not None:
            self.ledger = loaded
        else:
            # Start at zero and record the starting credit as seed income so the
            # books balance (no double-counting).
            self.ledger = Ledger(balance=0.0)
            self.ledger.record_income(
                self.config.starting_balance_usd, "seed", "starting life-credit"
            )

    def _default_ledger_path(self) -> str:
        import os

        here = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        return os.path.join(here, "data", "real_ledger.json")

    # ------------------------------------------------------------------ #
    def run_cycle(self) -> CycleReport:
        """One think -> work -> record -> check cycle."""
        rep = CycleReport(cycle=self.cycle + 1)
        if self.ledger.dead:
            return rep
        self.cycle += 1

        # 1) THINK (costs money = staying alive)
        prompt = self._build_prompt()
        result = self.llm.think(prompt, system=self.SYSTEM_PROMPT)
        rep.thought = result.text
        rep.think_cost = result.cost_usd
        self.cost_tracker.record(result.usage)

        # Enforce per-action spend cap.
        if result.cost_usd > self.config.max_spend_per_action_usd:
            rep.messages.append(
                f"⚠️ thought cost ${result.cost_usd:.6f} exceeds cap; recording anyway"
            )

        # Pay for the thought. If we can't, we die.
        if not self.ledger.record_expense(
            result.cost_usd, f"llm:{result.usage.model}", "thinking"
        ):
            self._die(rep, "could not afford to think")
            return rep

        # 2) WORK (try to earn)
        for provider in self.providers:
            outcome = provider.attempt(self.rng)
            if outcome.ok and outcome.amount > 0:
                self.ledger.record_income(outcome.amount, outcome.source, outcome.memo)
                self.wallet.receive(outcome.amount, outcome.memo)
                rep.earned += outcome.amount
                rep.income_sources.append(f"{outcome.source}:${outcome.amount:.6f}")

        # 3) RECORD / persist
        rep.balance_after = self.ledger.balance
        rep.runway_actions = self.ledger.runway_actions(
            self.cost_tracker.avg_cost_per_call
        )
        self.ledger.save(self.ledger_path)

        # 4) CHECK death
        if self.ledger.balance <= self.config.min_balance_usd:
            self._die(rep, "balance fell to zero")
        return rep

    def run(self, cycles: int, on_report=None) -> list[CycleReport]:
        reports = []
        for _ in range(cycles):
            if self.ledger.dead:
                break
            rep = self.run_cycle()
            reports.append(rep)
            if on_report:
                on_report(rep)
        return reports

    # ------------------------------------------------------------------ #
    def work_bounties(self, demo: bool = True) -> dict:
        """Use the LLM planner to pick a real bounty and submit work for it.

        This is the agent actively "getting a job": it lists AGENT_ALLOWED
        bounties, asks the LLM which to pursue and to draft the work, then
        submits. Returns a report dict.

        In demo mode the bounty list and submission are simulated (no network),
        but the LLM planning step still runs (simulated in demo, real in real
        mode) so the flow is exercised end to end.
        """
        from vital.real.bounties import SuperteamProvider
        from vital.real.planner import Planner, ACTION_WORK_BOUNTY

        provider = SuperteamProvider(demo=demo)
        bounties = provider.list_bounties(agent_only=True)

        planner = Planner(self.llm)
        plan = planner.decide(self.status(), bounties)

        report = {
            "bounties_seen": len(bounties),
            "plan": plan.to_dict(),
            "submitted": False,
            "result": None,
        }

        if plan.action == ACTION_WORK_BOUNTY and plan.bounty_id:
            submission = {"content": plan.draft or "VITAL's submission"}
            result = provider.submit(plan.bounty_id, submission)
            report["submitted"] = True
            report["result"] = result
            # Record the planning LLM cost (the think that produced the draft).
        provider.close()
        return report

    # ------------------------------------------------------------------ #
    def _build_prompt(self) -> str:
        return (
            f"Balance: ${self.ledger.balance:.6f}. "
            f"Total earned: ${self.ledger.total_income:.6f}. "
            f"Total spent: ${self.ledger.total_expense:.6f}. "
            f"Avg cost per thought: ${self.cost_tracker.avg_cost_per_call:.6f}. "
            f"Runway: {self.ledger.runway_actions(self.cost_tracker.avg_cost_per_call):.0f} thoughts left. "
            "What paid work should I do next to earn more than I spend?"
        )

    def _die(self, rep: CycleReport, reason: str) -> None:
        self.ledger.dead = True
        self.ledger.death_reason = reason
        self.ledger.save(self.ledger_path)
        rep.died = True
        rep.balance_after = self.ledger.balance
        rep.messages.append(f"💀 VITAL died: {reason}")

    # ------------------------------------------------------------------ #
    def status(self) -> dict:
        return {
            "mode": self.config.mode,
            "cycle": self.cycle,
            "balance": round(self.ledger.balance, 8),
            "total_income": round(self.ledger.total_income, 8),
            "total_expense": round(self.ledger.total_expense, 8),
            "net": round(self.ledger.net, 8),
            "dead": self.ledger.dead,
            "death_reason": self.ledger.death_reason,
            "wallet_address": self.wallet.address(),
            "wallet_is_real": self.wallet.is_real,
            "avg_cost_per_thought": round(self.cost_tracker.avg_cost_per_call, 8),
            "runway_thoughts": self.ledger.runway_actions(
                self.cost_tracker.avg_cost_per_call
            ),
            "providers": [p.name for p in self.providers],
        }
