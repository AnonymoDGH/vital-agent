"""Tests for the real income integrations: bounties, x402 service, bridge."""

from __future__ import annotations

import pytest

from vital.real.agent import RealAgent
from vital.real.bounties import Bounty, SuperteamProvider
from vital.real.config import RealConfig
from vital.real.x402_service import to_caip2, build_service


# --------------------------------------------------------------------------- #
# Bounties (demo mode — no network)
# --------------------------------------------------------------------------- #
def test_demo_bounties_listed():
    p = SuperteamProvider(demo=True)
    bs = p.list_bounties()
    assert len(bs) >= 1
    assert all(isinstance(b, Bounty) for b in bs)
    assert all(b.agent_allowed for b in bs)


def test_demo_register_and_submit():
    p = SuperteamProvider(demo=True)
    reg = p.register()
    assert "apiKey" in reg
    sub = p.submit("demo-1", {"content": "x"})
    assert sub.get("ok") is True


def test_bounty_to_dict():
    b = Bounty(id="1", title="t", reward_usd=10.0, token="USDC", agent_allowed=True)
    d = b.to_dict()
    assert d["id"] == "1"
    assert d["reward_usd"] == 10.0


# --------------------------------------------------------------------------- #
# x402 service
# --------------------------------------------------------------------------- #
def test_to_caip2_maps_friendly_names():
    assert to_caip2("base") == "eip155:8453"
    assert to_caip2("base-mainnet") == "eip155:8453"
    assert to_caip2("base-sepolia") == "eip155:84532"
    # already-CAIP2 passes through
    assert to_caip2("eip155:8453") == "eip155:8453"


def test_build_service_creates_routes():
    app = build_service(pay_to="0x" + "1" * 40, network="base-sepolia")
    paths = {r.path for r in app.routes}
    assert "/vital/status" in paths
    assert "/vital/fortune" in paths
    assert "/vital/echo" in paths
    assert "/" in paths


# --------------------------------------------------------------------------- #
# Bridge (x402 income -> ledger)
# --------------------------------------------------------------------------- #
def test_bridge_records_income(tmp_path):
    from vital.real.bridge import AgentStatusProvider

    cfg = RealConfig(mode="demo", starting_balance_usd=1.0,
                     ledger_path=str(tmp_path / "ledger.json"))
    agent = RealAgent(cfg)
    bridge = AgentStatusProvider(agent)

    before = agent.ledger.balance
    bridge.on_x402_income(0.05, payer="0xpayer")
    assert agent.ledger.balance == pytest.approx(before + 0.05)
    assert agent.ledger.total_income == pytest.approx(1.0 + 0.05)


def test_bridge_ignores_bad_amounts(tmp_path):
    from vital.real.bridge import AgentStatusProvider

    cfg = RealConfig(mode="demo", starting_balance_usd=1.0,
                     ledger_path=str(tmp_path / "ledger.json"))
    agent = RealAgent(cfg)
    bridge = AgentStatusProvider(agent)
    before = agent.ledger.balance
    bridge.on_x402_income(None)
    bridge.on_x402_income("not-a-number")
    bridge.on_x402_income(-5)
    assert agent.ledger.balance == pytest.approx(before)


def test_bridge_snapshot(tmp_path):
    from vital.real.bridge import AgentStatusProvider

    cfg = RealConfig(mode="demo", starting_balance_usd=1.0,
                     ledger_path=str(tmp_path / "ledger.json"))
    agent = RealAgent(cfg)
    bridge = AgentStatusProvider(agent)
    snap = bridge.snapshot()
    assert snap["agent"] == "VITAL"
    assert snap["alive"] is True
    assert snap["balance_usd"] == pytest.approx(1.0)
