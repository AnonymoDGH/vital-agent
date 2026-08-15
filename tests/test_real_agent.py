"""Tests for the real survival loop (RealAgent) in demo mode."""

from __future__ import annotations

import os

import pytest

from vital.real.agent import RealAgent
from vital.real.config import RealConfig


def make_agent(tmp_path, balance=1.0, **kw):
    cfg = RealConfig(
        mode="demo",
        starting_balance_usd=balance,
        ledger_path=str(tmp_path / "ledger.json"),
        **kw,
    )
    return RealAgent(cfg)


def test_agent_starts_with_seed_balance(tmp_path):
    a = make_agent(tmp_path, balance=1.0)
    assert a.ledger.balance == pytest.approx(1.0)
    assert a.ledger.total_income == pytest.approx(1.0)  # seed counted once
    assert not a.ledger.dead


def test_run_cycle_thinks_and_pays(tmp_path):
    a = make_agent(tmp_path, balance=1.0)
    rep = a.run_cycle()
    assert rep.think_cost > 0
    assert a.cost_tracker.calls == 1
    # balance changed by (income - think_cost)
    assert a.ledger.total_expense == pytest.approx(rep.think_cost)


def test_agent_persists_ledger(tmp_path):
    a = make_agent(tmp_path, balance=1.0)
    a.run(5)
    assert os.path.exists(a.ledger_path)
    # a fresh agent on the same path resumes the same ledger
    b = RealAgent(
        RealConfig(mode="demo", starting_balance_usd=1.0, ledger_path=a.ledger_path)
    )
    assert b.ledger.balance == pytest.approx(a.ledger.balance)


def test_agent_dies_when_broke(tmp_path):
    # Tiny balance, no income providers that pay -> dies quickly.
    cfg = RealConfig(
        mode="demo",
        starting_balance_usd=0.0001,
        ledger_path=str(tmp_path / "ledger.json"),
        income_providers=["none"],  # no income at all
    )
    a = RealAgent(cfg)
    a.run(50)
    assert a.ledger.dead
    assert a.ledger.death_reason


def test_status_reports_fields(tmp_path):
    a = make_agent(tmp_path, balance=1.0)
    a.run(3)
    s = a.status()
    for key in ("mode", "cycle", "balance", "total_income", "total_expense",
                "net", "dead", "wallet_address", "runway_thoughts", "providers"):
        assert key in s


def test_real_mode_without_credentials_raises(tmp_path):
    cfg = RealConfig(
        mode="real",
        openai_api_key=None,
        cdp_api_key_id=None,
        ledger_path=str(tmp_path / "ledger.json"),
    )
    with pytest.raises(RuntimeError):
        RealAgent(cfg)
