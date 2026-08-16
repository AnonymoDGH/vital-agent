"""Tests for the job scanner (live-work hunter)."""

from __future__ import annotations

import datetime

import pytest

from vital.real.scanner import (
    JobScanner,
    Opportunity,
    ScanReport,
    _is_live,
    load_superteam_key,
)


def test_is_live_future_deadline():
    now = datetime.datetime(2026, 8, 15)
    assert _is_live("2026-12-31T00:00:00.000Z", now) is True


def test_is_live_past_deadline():
    now = datetime.datetime(2026, 8, 15)
    assert _is_live("2026-01-01T00:00:00.000Z", now) is False


def test_is_live_bad_deadline():
    now = datetime.datetime(2026, 8, 15)
    assert _is_live("not-a-date", now) is False
    assert _is_live("", now) is False


def test_opportunity_to_dict():
    o = Opportunity(
        source="superteam", id="1", title="t", reward_usd=100.0,
        token="USDC", deadline="2026-12-31", url="u",
    )
    d = o.to_dict()
    assert d["source"] == "superteam"
    assert d["reward_usd"] == 100.0


def test_scan_report_to_dict():
    r = ScanReport(scanned_at="now")
    r.opportunities.append(
        Opportunity(source="s", id="1", title="t", reward_usd=1.0,
                    token="USDC", deadline="d")
    )
    d = r.to_dict()
    assert d["scanned_at"] == "now"
    assert len(d["opportunities"]) == 1


def test_scanner_sorts_by_reward_desc():
    """The scanner must present the highest-paying live work first."""
    s = JobScanner(demo=True)
    report = s.scan()
    rewards = [o.reward_usd for o in report.opportunities]
    assert rewards == sorted(rewards, reverse=True)


def test_load_superteam_key_returns_none_or_str():
    # In CI there is no credentials file; locally there may be. Either is fine.
    key = load_superteam_key()
    assert key is None or isinstance(key, str)
