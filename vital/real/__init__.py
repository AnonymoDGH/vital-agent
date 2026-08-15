"""VITAL real economy — the agent earns and spends REAL money.

This package connects VITAL to the real internet economy:

    vital.real.costs    -> track REAL LLM/API spend (the agent's cost of living)
    vital.real.wallet   -> a real on-chain wallet (USDC on Base) via pluggable backends
    vital.real.income   -> pluggable income providers (bounties, x402, tips)
    vital.real.ledger   -> the real ledger: balance, income, expenses
    vital.real.config   -> real-mode configuration from environment variables
    vital.real.agent    -> the real survival loop: think (pay) -> work (earn)

Two modes:
    DEMO (default)  -> no credentials needed, simulated wallet & income, safe.
    REAL            -> activated by env vars, uses real APIs, spends real money.

WARNING: REAL mode can spend real funds. Read docs/REAL_MODE.md first.
"""

from vital.real.config import RealConfig, load_real_config
from vital.real.costs import CostTracker, LLMUsage
from vital.real.ledger import Ledger
from vital.real.wallet import Wallet, DemoWallet
from vital.real.income import IncomeProvider, IncomeResult, BountyIncome

__all__ = [
    "RealConfig",
    "load_real_config",
    "CostTracker",
    "LLMUsage",
    "Ledger",
    "Wallet",
    "DemoWallet",
    "IncomeProvider",
    "IncomeResult",
    "BountyIncome",
]
