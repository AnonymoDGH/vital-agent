"""Wallet abstraction: where the agent's real money lives.

A Wallet holds the agent's balance (USDC on Base in real mode) and can
report it, receive income, and pay for things.

Backends:
    DemoWallet  -> simulated balance, no network, always available.
    CDPWallet   -> real on-chain wallet via Coinbase CDP / AgentKit (lazy import).

The interface is deliberately tiny so backends are interchangeable.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional


@dataclass
class TxResult:
    """Result of a wallet transaction."""

    ok: bool
    amount: float
    tx_id: str = ""
    error: str = ""


class Wallet(ABC):
    """Abstract wallet the agent uses to hold and move money."""

    @abstractmethod
    def address(self) -> str:
        """Public receiving address (for getting paid)."""

    @abstractmethod
    def balance(self) -> float:
        """Current balance in the spend currency (USD-equivalent)."""

    @abstractmethod
    def receive(self, amount: float, memo: str = "") -> TxResult:
        """Credit income into the wallet."""

    @abstractmethod
    def pay(self, amount: float, to: str = "", memo: str = "") -> TxResult:
        """Spend money (pay for an API call, a service, etc.)."""

    @property
    @abstractmethod
    def is_real(self) -> bool:
        """True if this wallet moves real money."""


class DemoWallet(Wallet):
    """Simulated wallet for demo mode. No network, no real money."""

    def __init__(self, starting_balance: float = 1.00):
        self._balance = float(starting_balance)
        self._address = "0xDEMO000000000000000000000000000000000000"
        self._tx_counter = 0

    def address(self) -> str:
        return self._address

    def balance(self) -> float:
        return self._balance

    def receive(self, amount: float, memo: str = "") -> TxResult:
        if amount <= 0:
            return TxResult(ok=False, amount=amount, error="amount must be > 0")
        self._balance += amount
        self._tx_counter += 1
        return TxResult(ok=True, amount=amount, tx_id=f"demo-rx-{self._tx_counter}")

    def pay(self, amount: float, to: str = "", memo: str = "") -> TxResult:
        if amount <= 0:
            return TxResult(ok=False, amount=amount, error="amount must be > 0")
        if amount > self._balance:
            return TxResult(ok=False, amount=amount, error="insufficient balance")
        self._balance -= amount
        self._tx_counter += 1
        return TxResult(ok=True, amount=amount, tx_id=f"demo-tx-{self._tx_counter}")

    @property
    def is_real(self) -> bool:
        return False


def make_wallet(config) -> Wallet:
    """Factory: build the right wallet for the config.

    In real mode this attempts to build a CDP wallet; if the AgentKit package
    is missing or credentials are bad it raises so the caller can fall back.
    """
    if not config.is_real:
        return DemoWallet(starting_balance=config.starting_balance_usd)

    # Lazy import so demo mode never requires the heavy real dependencies.
    from vital.real.wallet_cdp import CDPWallet

    return CDPWallet(config)
