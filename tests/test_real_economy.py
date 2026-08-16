"""Tests for the real-economy modules (demo mode — no network, no real money)."""

from __future__ import annotations

import os
import random

import pytest

from vital.real.config import RealConfig, load_real_config
from vital.real.costs import CostTracker, LLMUsage, PRICING
from vital.real.income import DemoIncome, make_providers
from vital.real.ledger import Ledger, LedgerEntry
from vital.real.llm import LLMClient
from vital.real.wallet import DemoWallet, make_wallet


# --------------------------------------------------------------------------- #
# Costs
# --------------------------------------------------------------------------- #
def test_llm_usage_cost_math():
    u = LLMUsage(model="gpt-4o-mini", prompt_tokens=1_000_000, completion_tokens=0)
    assert u.cost_usd() == pytest.approx(PRICING["gpt-4o-mini"][0])
    u2 = LLMUsage(model="gpt-4o-mini", prompt_tokens=0, completion_tokens=1_000_000)
    assert u2.cost_usd() == pytest.approx(PRICING["gpt-4o-mini"][1])


def test_unknown_model_uses_default_pricing():
    u = LLMUsage(model="not-a-real-model", prompt_tokens=1_000_000, completion_tokens=0)
    assert u.cost_usd() > 0


def test_openai_cached_tokens_bill_at_half_rate():
    # 1M prompt tokens, all cached, on gpt-4o-mini (input $0.15/1M).
    full = LLMUsage(model="gpt-4o-mini", prompt_tokens=1_000_000, completion_tokens=0)
    cached = LLMUsage(model="gpt-4o-mini", prompt_tokens=1_000_000,
                      completion_tokens=0, cached_tokens=1_000_000)
    assert full.cost_usd() == pytest.approx(0.15)
    assert cached.cost_usd() == pytest.approx(0.075)  # half price


def test_anthropic_cache_read_cheaper_than_fresh():
    # claude-haiku-4-5 input $1/1M. 1M cache reads should cost ~$0.10.
    fresh = LLMUsage(model="claude-haiku-4-5", prompt_tokens=1_000_000, completion_tokens=0)
    reads = LLMUsage(model="claude-haiku-4-5", prompt_tokens=0,
                     completion_tokens=0, cache_read_tokens=1_000_000)
    assert fresh.cost_usd() == pytest.approx(1.00)
    assert reads.cost_usd() == pytest.approx(0.10)


def test_anthropic_cache_write_costs_more_than_fresh():
    # cache writes bill at 125% of input.
    writes = LLMUsage(model="claude-haiku-4-5", prompt_tokens=0,
                      completion_tokens=0, cache_creation_tokens=1_000_000)
    assert writes.cost_usd() == pytest.approx(1.25)


def test_total_tokens_includes_cache_tokens():
    u = LLMUsage(model="claude-haiku-4-5", prompt_tokens=10, completion_tokens=20,
                 cache_creation_tokens=30, cache_read_tokens=40)
    assert u.total_tokens == 100


def test_cost_tracker_accumulates():
    t = CostTracker()
    u = LLMUsage(model="gpt-4o-mini", prompt_tokens=1000, completion_tokens=100)
    c = t.record(u)
    assert c > 0
    assert t.total_usd == pytest.approx(c)
    assert t.calls == 1
    t.record(u)
    assert t.calls == 2
    assert t.avg_cost_per_call == pytest.approx(c)


# --------------------------------------------------------------------------- #
# Wallet (demo)
# --------------------------------------------------------------------------- #
def test_demo_wallet_pay_and_receive():
    w = DemoWallet(starting_balance=1.0)
    assert w.balance() == 1.0
    r = w.pay(0.3)
    assert r.ok and w.balance() == pytest.approx(0.7)
    r = w.receive(0.5)
    assert r.ok and w.balance() == pytest.approx(1.2)


def test_demo_wallet_cannot_overdraw():
    w = DemoWallet(starting_balance=0.1)
    r = w.pay(1.0)
    assert not r.ok
    assert w.balance() == pytest.approx(0.1)


def test_make_wallet_demo():
    cfg = RealConfig(mode="demo")
    w = make_wallet(cfg)
    assert not w.is_real


# --------------------------------------------------------------------------- #
# Ledger
# --------------------------------------------------------------------------- #
def test_ledger_income_and_expense():
    l = Ledger(balance=1.0)
    l.record_income(0.5, "test")
    assert l.balance == pytest.approx(1.5)
    assert l.record_expense(0.2, "test")
    assert l.balance == pytest.approx(1.3)


def test_ledger_refuses_overdraw():
    l = Ledger(balance=0.1)
    assert not l.record_expense(1.0, "test")
    assert l.balance == pytest.approx(0.1)


def test_ledger_runway():
    l = Ledger(balance=1.0)
    assert l.runway_actions(0.1) == pytest.approx(10.0)
    assert l.runway_actions(0.0) == float("inf")


def test_ledger_save_load_roundtrip(tmp_path):
    path = str(tmp_path / "ledger.json")
    l = Ledger(balance=2.5)
    l.record_income(1.0, "a")
    l.record_expense(0.5, "b")
    l.save(path)
    loaded = Ledger.load(path)
    assert loaded is not None
    assert loaded.balance == pytest.approx(l.balance)
    assert loaded.total_income == pytest.approx(l.total_income)
    assert loaded.total_expense == pytest.approx(l.total_expense)


def test_ledger_load_missing_returns_none(tmp_path):
    assert Ledger.load(str(tmp_path / "nope.json")) is None


# --------------------------------------------------------------------------- #
# Income (demo)
# --------------------------------------------------------------------------- #
def test_demo_income_produces_positive_amounts():
    p = DemoIncome()
    rng = random.Random(1)
    earned_any = False
    for _ in range(50):
        r = p.attempt(rng)
        if r.ok:
            assert r.amount > 0
            earned_any = True
    assert earned_any


def test_make_providers_default_demo():
    cfg = RealConfig(mode="demo")
    providers = make_providers(cfg)
    assert len(providers) >= 1
    assert providers[0].name == "demo"


# --------------------------------------------------------------------------- #
# LLM client (demo)
# --------------------------------------------------------------------------- #
def test_llm_client_demo_simulates_and_prices():
    cfg = RealConfig(mode="demo")
    c = LLMClient(cfg)
    r = c.think("hello")
    assert r.simulated
    assert r.cost_usd > 0
    assert r.usage.total_tokens > 0


# --------------------------------------------------------------------------- #
# Config
# --------------------------------------------------------------------------- #
def test_default_config_is_demo():
    cfg = load_real_config()
    # default mode is demo unless env says otherwise
    assert cfg.mode in ("demo", "real")


def test_real_mode_requires_credentials():
    cfg = RealConfig(mode="real", openai_api_key=None, cdp_api_key_id=None)
    problems = cfg.validate()
    assert problems  # must flag missing credentials


def test_demo_mode_needs_no_credentials():
    cfg = RealConfig(mode="demo")
    assert cfg.validate() == []
