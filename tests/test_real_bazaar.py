"""Tests for the x402 Bazaar discovery module (offline-safe)."""

from __future__ import annotations

from vital.real.bazaar import PaidAPI, _atomic_to_usdc, fetch_bazaar


def test_atomic_to_usdc():
    assert _atomic_to_usdc(1_000_000) == 1.0
    assert _atomic_to_usdc(1000) == 0.001
    assert _atomic_to_usdc("bad") == 0.0
    assert _atomic_to_usdc(None) == 0.0


def test_paid_api_to_dict():
    a = PaidAPI(
        url="https://x/api", method="GET", description="d",
        price_usdc=0.001, network="eip155:8453", pay_to="0x1", source="cdp",
    )
    d = a.to_dict()
    assert d["url"] == "https://x/api"
    assert d["price_usdc"] == 0.001


def test_fetch_bazaar_bad_url_returns_empty():
    # A bogus catalog URL must not raise; it returns [].
    result = fetch_bazaar("https://invalid.invalid/nope", limit=5, timeout=5.0)
    assert result == []
