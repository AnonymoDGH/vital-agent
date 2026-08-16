"""x402 Bazaar discovery: browse the live market of paid APIs.

The x402 Bazaar is a machine-readable catalog of pay-per-request APIs ("Google
for agentic endpoints"). Two live catalogs (verified 2025):

    CDP    https://api.cdp.coinbase.com/platform/v2/x402/discovery/resources
    PayAI  https://facilitator.payai.network/discovery/resources

Each returns {"items": [...]} where an item has:
    resource     -> the paid API URL
    method       -> HTTP method
    description  -> what it does
    accepts[0]   -> {amount (atomic USDC), network (CAIP-2), payTo, scheme}

This lets VITAL see what other agents charge for APIs (market research) and,
with a funded wallet + x402 client, actually consume them.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

CDP_BAZAAR = "https://api.cdp.coinbase.com/platform/v2/x402/discovery/resources"
PAYAI_BAZAAR = "https://facilitator.payai.network/discovery/resources"

USDC_DECIMALS = 6


@dataclass
class PaidAPI:
    """One paid API listed in a Bazaar catalog."""

    url: str
    method: str
    description: str
    price_usdc: float
    network: str
    pay_to: str
    source: str  # which catalog it came from

    def to_dict(self) -> dict:
        return {
            "url": self.url,
            "method": self.method,
            "description": self.description,
            "price_usdc": self.price_usdc,
            "network": self.network,
            "pay_to": self.pay_to,
            "source": self.source,
        }


def _atomic_to_usdc(amount) -> float:
    try:
        return float(amount) / (10 ** USDC_DECIMALS)
    except (TypeError, ValueError):
        return 0.0


def fetch_bazaar(catalog_url: str, limit: int = 50, timeout: float = 25.0) -> list[PaidAPI]:
    """Fetch paid APIs from one Bazaar catalog. Returns [] on any error."""
    import httpx

    source = "cdp" if "cdp.coinbase" in catalog_url else "payai"
    try:
        resp = httpx.get(catalog_url, timeout=timeout, follow_redirects=True)
        resp.raise_for_status()
        data = resp.json()
    except Exception:
        return []

    items = data.get("items", []) if isinstance(data, dict) else data
    out: list[PaidAPI] = []
    for item in items[:limit]:
        if not isinstance(item, dict):
            continue
        url = item.get("resource") or ""
        if not url:
            continue
        accepts = (item.get("accepts") or [{}])[0]
        out.append(
            PaidAPI(
                url=url,
                method=str(item.get("method", "GET")),
                description=str(item.get("description", ""))[:200],
                price_usdc=_atomic_to_usdc(accepts.get("amount")),
                network=str(accepts.get("network", "")),
                pay_to=str(accepts.get("payTo", "")),
                source=source,
            )
        )
    return out


def fetch_all_bazaars(limit_each: int = 50) -> list[PaidAPI]:
    """Fetch from all known catalogs, deduplicated by URL."""
    seen: set[str] = set()
    out: list[PaidAPI] = []
    for catalog in (CDP_BAZAAR, PAYAI_BAZAAR):
        for api in fetch_bazaar(catalog, limit=limit_each):
            if api.url in seen:
                continue
            seen.add(api.url)
            out.append(api)
    return out
