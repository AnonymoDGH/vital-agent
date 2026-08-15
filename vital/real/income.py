"""Income providers: how the agent earns REAL money.

Each provider implements a small interface: it can report an opportunity and,
when the agent acts on it, produce income. Providers are pluggable so we can
start with safe ones and add real ones as they become available.

Built-in providers:
    DemoIncome      -> simulated earnings so the loop runs without credentials.
    TipJarIncome    -> exposes the wallet address so humans/agents can tip.
    X402Income      -> sell an HTTP service and get paid per request (x402).
    BountyIncome    -> discover and complete bounties (Gitcoin, etc.).

Real providers require credentials/network and are activated via config.
"""

from __future__ import annotations

import random
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional


@dataclass
class IncomeResult:
    """Outcome of an income attempt."""

    ok: bool
    amount: float = 0.0
    source: str = ""
    memo: str = ""
    error: str = ""


class IncomeProvider(ABC):
    """A source of income the agent can work."""

    name: str = "base"

    @abstractmethod
    def attempt(self, rng: random.Random) -> IncomeResult:
        """Try to earn money once. Returns how much was earned (0 if none)."""

    @property
    def is_real(self) -> bool:
        return False


class DemoIncome(IncomeProvider):
    """Simulated income for demo mode.

    Tuned so expected income is only slightly above the cost of one thought,
    which keeps real "earn or die" tension: losing streaks drain the balance.
    """

    name = "demo"

    def __init__(self, low: float = 0.0002, high: float = 0.003, success: float = 0.40):
        self.low = low
        self.high = high
        self.success = success

    def attempt(self, rng: random.Random) -> IncomeResult:
        if rng.random() > self.success:
            return IncomeResult(ok=False, source=self.name, memo="no work found")
        amount = rng.uniform(self.low, self.high)
        return IncomeResult(
            ok=True,
            amount=round(amount, 6),
            source=self.name,
            memo="simulated gig",
        )


class TipJarIncome(IncomeProvider):
    """Passive: the agent publishes its address and hopes to receive tips.

    In demo mode this occasionally simulates a tip. In real mode it would poll
    the wallet for inbound transfers (see wallet.balance()).
    """

    name = "tipjar"

    def __init__(self, wallet=None, chance: float = 0.05, low=0.01, high=0.10):
        self.wallet = wallet
        self.chance = chance
        self.low = low
        self.high = high

    def attempt(self, rng: random.Random) -> IncomeResult:
        if rng.random() > self.chance:
            return IncomeResult(ok=False, source=self.name, memo="no tips yet")
        amount = rng.uniform(self.low, self.high)
        return IncomeResult(
            ok=True,
            amount=round(amount, 6),
            source=self.name,
            memo="a kind stranger tipped the agent",
        )


class BountyIncome(IncomeProvider):
    """Work real bounties (Superteam Earn) to earn.

    In demo mode it simulates occasionally completing a bounty. In real mode it
    would list AGENT_ALLOWED bounties and submit work; final payout still needs
    a human to claim, so this models the *expected* value of bounty work.
    """

    name = "bounty"

    def __init__(self, provider=None, chance: float = 0.12, low=0.5, high=5.0):
        self.provider = provider
        self.chance = chance
        self.low = low
        self.high = high

    def attempt(self, rng: random.Random) -> IncomeResult:
        if rng.random() > self.chance:
            return IncomeResult(ok=False, source=self.name, memo="no bounty completed")
        amount = rng.uniform(self.low, self.high)
        return IncomeResult(
            ok=True,
            amount=round(amount, 6),
            source=self.name,
            memo="completed a bounty",
        )


def make_providers(config, wallet=None) -> list[IncomeProvider]:
    """Build the list of income providers from config.

    Use VITAL_INCOME=none to run with no income at all (useful for tests and
    for observing pure burn).
    """
    providers: list[IncomeProvider] = []
    names = [n.strip().lower() for n in config.income_providers]
    if names == ["none"]:
        return []
    for name in names:
        if name in ("demo", ""):
            providers.append(DemoIncome())
        elif name == "tipjar":
            providers.append(TipJarIncome(wallet=wallet))
        elif name == "bounty":
            providers.append(BountyIncome())
        # Real providers (x402) are added here once their SDKs are
        # wired; they require credentials and are opt-in via VITAL_INCOME.
    if not providers:
        providers.append(DemoIncome())
    return providers
