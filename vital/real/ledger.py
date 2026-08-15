"""The real ledger: the agent's true balance sheet.

This is what decides whether VITAL lives or dies in real mode. It tracks:
    - real balance (from the wallet)
    - real income (each earning event)
    - real expenses (each LLM call / payment)
    - runway: how many more "actions" the agent can afford at its current burn

Everything is persisted to a JSON file so the agent's financial life survives
restarts.
"""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class LedgerEntry:
    """One line in the ledger."""

    ts: float
    kind: str          # "income" | "expense"
    amount: float      # USD, positive
    source: str        # e.g. "openai:gpt-4o-mini", "bounty:gitcoin", "tip"
    memo: str = ""

    def to_dict(self) -> dict:
        return {
            "ts": self.ts,
            "kind": self.kind,
            "amount": round(self.amount, 8),
            "source": self.source,
            "memo": self.memo,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "LedgerEntry":
        return cls(
            ts=d.get("ts", 0.0),
            kind=d.get("kind", "expense"),
            amount=d.get("amount", 0.0),
            source=d.get("source", ""),
            memo=d.get("memo", ""),
        )


@dataclass
class Ledger:
    """The agent's financial life."""

    balance: float = 0.0
    total_income: float = 0.0
    total_expense: float = 0.0
    entries: list[LedgerEntry] = field(default_factory=list)
    born_ts: float = field(default_factory=time.time)
    dead: bool = False
    death_reason: str = ""

    ENTRY_CAP = 1000

    # ------------------------------------------------------------------ #
    def record_income(self, amount: float, source: str, memo: str = "") -> None:
        if amount <= 0:
            return
        self.balance += amount
        self.total_income += amount
        self._append(LedgerEntry(time.time(), "income", amount, source, memo))

    def record_expense(self, amount: float, source: str, memo: str = "") -> bool:
        """Record a spend. Returns False if it would overdraw (agent can't pay)."""
        if amount <= 0:
            return True
        if amount > self.balance:
            return False
        self.balance -= amount
        self.total_expense += amount
        self._append(LedgerEntry(time.time(), "expense", amount, source, memo))
        return True

    def _append(self, entry: LedgerEntry) -> None:
        self.entries.append(entry)
        if len(self.entries) > self.ENTRY_CAP:
            self.entries = self.entries[-self.ENTRY_CAP:]

    # ------------------------------------------------------------------ #
    @property
    def net(self) -> float:
        return self.total_income - self.total_expense

    def runway_actions(self, avg_cost: float) -> float:
        """How many more actions the agent can afford at avg_cost each."""
        if avg_cost <= 0:
            return float("inf")
        return self.balance / avg_cost

    def burn_per_hour(self, window_seconds: float = 3600.0) -> float:
        """USD spent per hour over the recent window."""
        now = time.time()
        spent = sum(
            e.amount for e in self.entries
            if e.kind == "expense" and now - e.ts <= window_seconds
        )
        hours = window_seconds / 3600.0
        return spent / hours if hours > 0 else 0.0

    # ------------------------------------------------------------------ #
    def to_dict(self) -> dict:
        return {
            "balance": round(self.balance, 8),
            "total_income": round(self.total_income, 8),
            "total_expense": round(self.total_expense, 8),
            "born_ts": self.born_ts,
            "dead": self.dead,
            "death_reason": self.death_reason,
            "entries": [e.to_dict() for e in self.entries[-200:]],
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Ledger":
        return cls(
            balance=d.get("balance", 0.0),
            total_income=d.get("total_income", 0.0),
            total_expense=d.get("total_expense", 0.0),
            born_ts=d.get("born_ts", time.time()),
            dead=d.get("dead", False),
            death_reason=d.get("death_reason", ""),
            entries=[LedgerEntry.from_dict(e) for e in d.get("entries", [])],
        )

    # ------------------------------------------------------------------ #
    def save(self, path: str) -> None:
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, ensure_ascii=False, indent=2)
        os.replace(tmp, path)

    @classmethod
    def load(cls, path: str) -> Optional["Ledger"]:
        if not os.path.exists(path):
            return None
        try:
            with open(path, "r", encoding="utf-8") as f:
                return cls.from_dict(json.load(f))
        except (json.JSONDecodeError, KeyError, TypeError, ValueError):
            return None
