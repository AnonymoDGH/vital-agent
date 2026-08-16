"""Real on-chain wallet via Coinbase Developer Platform (CDP) SDK v2.

This backend gives VITAL a REAL wallet holding USDC on Base. Requirements:

    pip install cdp-sdk

    CDP_API_KEY_ID=...           # free, from https://portal.cdp.coinbase.com/api-keys/secret
    CDP_API_KEY_SECRET=...       # the secret key
    CDP_WALLET_SECRET=...        # REQUIRED in 2025: portal.cdp.coinbase.com/wallets/non-custodial/security

Verified against cdp-sdk v1.47+ (async API, `from cdp import CdpClient`):
    - cdp.evm.get_or_create_account(name=...)  -> non-custodial EOA server wallet
    - account.list_token_balances(network="base")
    - account.transfer(to=..., amount=<smallest unit>, token="usdc", network="base")
    - account.request_faucet(network="base-sepolia", token="usdc")  # testnet only

USDC has 6 decimals: 1 USDC == 1_000_000 units. Network ids in cdp-sdk are
"base" / "base-sepolia" (AgentKit uses "base-mainnet" — do not mix them).

The Wallet interface is synchronous, so each call runs the async SDK in a
fresh event loop via asyncio.run(). That is fine for the agent's cadence
(a handful of wallet calls per minute at most).
"""

from __future__ import annotations

import asyncio
import os
from typing import Optional

from vital.real.wallet import TxResult, Wallet

USDC_DECIMALS = 6


class CDPWallet(Wallet):
    """A real wallet backed by Coinbase CDP (cdp-sdk v2)."""

    def __init__(self, config):
        self.config = config
        self._account_name = os.environ.get("VITAL_WALLET_NAME", "vital-agent")
        self._address: Optional[str] = None
        self._check_credentials()
        # Resolve the account once so we know our address.
        self._address = self._run(self._get_address())

    # ------------------------------------------------------------------ #
    def _check_credentials(self) -> None:
        missing = [
            name
            for name in ("CDP_API_KEY_ID", "CDP_API_KEY_SECRET", "CDP_WALLET_SECRET")
            if not os.environ.get(name)
        ]
        if missing:
            raise RuntimeError(
                "Real wallet requires env vars: " + ", ".join(missing)
                + " (get them free at https://portal.cdp.coinbase.com)"
            )

    @staticmethod
    def _client():
        try:
            from cdp import CdpClient
        except ImportError as exc:  # pragma: no cover - depends on env
            raise RuntimeError(
                "Real wallet requires the Coinbase SDK: pip install cdp-sdk"
            ) from exc
        return CdpClient()

    def _run(self, coro):
        """Run an async SDK coroutine in a fresh event loop."""
        return asyncio.run(coro)

    # ------------------------------------------------------------------ #
    async def _account(self, cdp):
        """Return the agent's account via the verified idempotent method.

        get_or_create_account(name=...) is the confirmed cdp-sdk v2 call; it
        returns the existing account when the name already exists, so it is safe
        to call repeatedly.
        """
        return await cdp.evm.get_or_create_account(name=self._account_name)

    async def _get_address(self) -> str:
        async with self._client() as cdp:
            account = await self._account(cdp)
            return account.address

    async def _get_balance(self) -> float:
        async with self._client() as cdp:
            account = await self._account(cdp)
            balances = await account.list_token_balances(network=self.config.network)
            for b in balances.balances:
                if getattr(b.token, "symbol", "") == "USDC":
                    decimals = getattr(b.amount, "decimals", USDC_DECIMALS) or USDC_DECIMALS
                    return float(b.amount.amount) / (10 ** decimals)
            return 0.0

    async def _transfer(self, to: str, amount_usdc: float) -> str:
        async with self._client() as cdp:
            account = await self._account(cdp)
            amount_units = int(round(amount_usdc * (10 ** USDC_DECIMALS)))
            result = await account.transfer(
                to=to,
                amount=amount_units,
                token="usdc",
                network=self.config.network,
            )
            return getattr(result, "transaction_hash", "") or str(result)

    async def _faucet(self) -> str:
        """Testnet only: request free USDC on base-sepolia."""
        async with self._client() as cdp:
            account = await self._account(cdp)
            result = await account.request_faucet(
                network="base-sepolia", token="usdc"
            )
            return str(result)

    # ------------------------------------------------------------------ #
    # Wallet interface
    # ------------------------------------------------------------------ #
    def address(self) -> str:
        return self._address or ""

    def balance(self) -> float:
        try:
            return self._run(self._get_balance())
        except Exception:
            return 0.0

    def receive(self, amount: float, memo: str = "") -> TxResult:
        """Inbound transfers arrive on-chain; we observe them via balance()."""
        return TxResult(
            ok=True,
            amount=amount,
            tx_id="onchain-inbound",
            error="income is observed on-chain, not self-credited",
        )

    def pay(self, amount: float, to: str = "", memo: str = "") -> TxResult:
        if not to:
            return TxResult(ok=False, amount=amount, error="no destination address")
        try:
            tx = self._run(self._transfer(to, amount))
            return TxResult(ok=True, amount=amount, tx_id=str(tx))
        except Exception as exc:  # pragma: no cover - network
            return TxResult(ok=False, amount=amount, error=str(exc))

    @property
    def is_real(self) -> bool:
        return True
