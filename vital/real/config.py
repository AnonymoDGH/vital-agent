"""Real-mode configuration.

Everything is driven by environment variables so no secrets live in code.
By default VITAL runs in DEMO mode (no credentials, no real money).

To enable REAL mode you must set VITAL_MODE=real AND provide credentials.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class RealConfig:
    """Configuration for the real economy."""

    mode: str = "demo"  # "demo" | "real"

    # --- Wallet (Coinbase CDP / AgentKit) ---
    cdp_api_key_id: Optional[str] = None
    cdp_api_key_secret: Optional[str] = None
    wallet_id: Optional[str] = None          # reuse an existing wallet
    network: str = "base"                    # "base" | "base-sepolia"
    spend_currency: str = "usdc"

    # --- LLM (the agent's brain + cost of living) ---
    llm_provider: str = "openai"             # "openai" | "anthropic"
    openai_api_key: Optional[str] = None
    anthropic_api_key: Optional[str] = None
    llm_model: str = "gpt-4o-mini"

    # --- Survival economics ---
    starting_balance_usd: float = 1.00       # real USD the agent starts with
    min_balance_usd: float = 0.00            # below this the agent "dies"
    max_spend_per_action_usd: float = 0.05   # safety cap per LLM call
    daily_budget_usd: float = 1.00           # hard daily cap

    # --- Income ---
    income_providers: list[str] = field(default_factory=lambda: ["demo"])

    # --- Persistence ---
    ledger_path: Optional[str] = None

    @property
    def is_real(self) -> bool:
        return self.mode == "real"

    def validate(self) -> list[str]:
        """Return a list of problems (empty if OK)."""
        problems = []
        if self.is_real:
            if self.llm_provider == "openai" and not self.openai_api_key:
                problems.append("VITAL_MODE=real but OPENAI_API_KEY is not set")
            if self.llm_provider == "anthropic" and not self.anthropic_api_key:
                problems.append("VITAL_MODE=real but ANTHROPIC_API_KEY is not set")
            if not self.cdp_api_key_id or not self.cdp_api_key_secret:
                problems.append(
                    "VITAL_MODE=real but CDP_API_KEY_ID / CDP_API_KEY_PRIVATE_KEY "
                    "are not set (needed for a real wallet)"
                )
        return problems


def load_real_config() -> RealConfig:
    """Build a RealConfig from environment variables."""
    return RealConfig(
        mode=os.environ.get("VITAL_MODE", "demo").lower(),
        cdp_api_key_id=os.environ.get("CDP_API_KEY_ID"),
        cdp_api_key_secret=os.environ.get("CDP_API_KEY_PRIVATE_KEY"),
        wallet_id=os.environ.get("VITAL_WALLET_ID"),
        network=os.environ.get("VITAL_NETWORK", "base"),
        spend_currency=os.environ.get("VITAL_SPEND_CURRENCY", "usdc"),
        llm_provider=os.environ.get("VITAL_LLM_PROVIDER", "openai"),
        openai_api_key=os.environ.get("OPENAI_API_KEY"),
        anthropic_api_key=os.environ.get("ANTHROPIC_API_KEY"),
        llm_model=os.environ.get("VITAL_LLM_MODEL", "gpt-4o-mini"),
        starting_balance_usd=float(os.environ.get("VITAL_START_BALANCE", "1.00")),
        min_balance_usd=float(os.environ.get("VITAL_MIN_BALANCE", "0.00")),
        max_spend_per_action_usd=float(os.environ.get("VITAL_MAX_SPEND", "0.05")),
        daily_budget_usd=float(os.environ.get("VITAL_DAILY_BUDGET", "1.00")),
        income_providers=os.environ.get("VITAL_INCOME", "demo").split(","),
        ledger_path=os.environ.get("VITAL_LEDGER_PATH"),
    )
