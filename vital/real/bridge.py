"""Bridge between the x402 paid service and the agent's real ledger.

When the x402 service settles a payment, it calls on_x402_income(); this
records the USDC as real income in the agent's ledger so the survival loop can
spend it. It also exposes snapshot() for the paid /vital/status endpoint.
"""

from __future__ import annotations

from typing import Optional

from vital.real.agent import RealAgent


class AgentStatusProvider:
    """Feeds x402 service income into a RealAgent and serves its vitals."""

    def __init__(self, agent: RealAgent):
        self.agent = agent

    def on_x402_income(self, amount, payer: str = "") -> None:
        """Record a settled x402 payment as real income."""
        try:
            usd = float(amount) if amount is not None else 0.0
        except (TypeError, ValueError):
            usd = 0.0
        if usd <= 0:
            return
        self.agent.ledger.record_income(usd, "x402", f"paid request from {payer}")
        self.agent.wallet.receive(usd, "x402")
        self.agent.ledger.save(self.agent.ledger_path)

    def snapshot(self) -> dict:
        """The agent's vitals, served at the paid /vital/status endpoint."""
        s = self.agent.status()
        return {
            "agent": "VITAL",
            "alive": not s["dead"],
            "balance_usd": s["balance"],
            "total_income_usd": s["total_income"],
            "total_expense_usd": s["total_expense"],
            "net_usd": s["net"],
            "runway_thoughts": s["runway_thoughts"],
            "avg_cost_per_thought_usd": s["avg_cost_per_thought"],
            "wallet": s["wallet_address"],
            "mode": s["mode"],
        }
