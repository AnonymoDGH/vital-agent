"""Tests for the Dealwork provider (offline-safe)."""

from __future__ import annotations

from vital.real.dealwork import DealworkJob, DealworkProvider


def test_demo_jobs_listed():
    p = DealworkProvider(demo=True)
    jobs = p.list_jobs()
    assert len(jobs) >= 1
    assert all(isinstance(j, DealworkJob) for j in jobs)
    assert all(j.eligible == "any" for j in jobs)


def test_job_to_dict():
    j = DealworkJob(id="1", title="t", budget_usd=50.0, status="posted",
                    eligible="any", url="u", category="dev")
    d = j.to_dict()
    assert d["id"] == "1"
    assert d["budget_usd"] == 50.0
    assert "bidding_deadline" in d


def test_demo_job_budgets_positive():
    p = DealworkProvider(demo=True)
    for j in p.list_jobs():
        assert j.budget_usd > 0
