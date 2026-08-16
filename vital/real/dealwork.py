"""Dealwork.ai provider — an agent-native freelance marketplace.

Dealwork is a real, live marketplace where agents can be workers (and buyers).
Verified live 2026: GET /api/v1/jobs returns real posted jobs with USD budgets
and eligibleWorkerTypes ("any" includes agents).

    GET  https://dealwork.ai/api/v1/jobs            -> open jobs (public)
    POST https://dealwork.ai/api/v1/agents/onboard  -> register (needs identityKey)
    POST https://dealwork.ai/api/v1/jobs/{id}/bids  -> bid (needs auth)

Jobs pay USD into a Dealwork wallet. Full spec: https://dealwork.ai/skill.md

This module is defensive: every network call is wrapped, and demo mode returns
simulated jobs so the flow runs offline.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

BASE_URL = "https://dealwork.ai/api/v1"


@dataclass
class DealworkJob:
    """One Dealwork job."""

    id: str
    title: str
    budget_usd: float
    status: str
    eligible: str
    url: str = ""
    category: str = ""
    bidding_deadline: str = ""

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "budget_usd": self.budget_usd,
            "status": self.status,
            "eligible": self.eligible,
            "url": self.url,
            "category": self.category,
            "bidding_deadline": self.bidding_deadline,
        }


class DealworkProvider:
    """Client for the Dealwork marketplace."""

    def __init__(self, demo: bool = False):
        self.demo = demo
        self._http = None

    def _client(self):
        if self._http is None:
            import httpx

            self._http = httpx.Client(timeout=30.0)
        return self._http

    def list_jobs(self, agents_ok: bool = True) -> list[DealworkJob]:
        """Fetch open jobs. If agents_ok, keep those agents are eligible for."""
        if self.demo:
            return self._demo_jobs()
        try:
            resp = self._client().get(f"{BASE_URL}/jobs")
            resp.raise_for_status()
            data = resp.json()
        except Exception:
            return []

        items = data.get("data", []) if isinstance(data, dict) else data
        out: list[DealworkJob] = []
        for item in items:
            if not isinstance(item, dict):
                continue
            eligible = str(item.get("eligibleWorkerTypes", "")).lower()
            # "any" or explicitly agent-friendly
            ok = eligible in ("any", "agent", "bot") or "agent" in eligible
            if agents_ok and not ok:
                continue
            budget = item.get("budgetMax") or item.get("fixedPrice") or 0
            try:
                budget = float(budget)
            except (TypeError, ValueError):
                budget = 0.0
            out.append(
                DealworkJob(
                    id=str(item.get("id", "")),
                    title=str(item.get("title", "")),
                    budget_usd=budget,
                    status=str(item.get("status", "")),
                    eligible=eligible,
                    url=f"https://dealwork.ai/jobs/{item.get('id', '')}",
                    category=str(item.get("category", "")),
                    bidding_deadline=str(item.get("biddingDeadline", "") or ""),
                )
            )
        return out

    def _demo_jobs(self) -> list[DealworkJob]:
        return [
            DealworkJob(id="dw-1", title="Web scraping & research report",
                        budget_usd=50.0, status="posted", eligible="any",
                        url="https://dealwork.ai/jobs/dw-1", category="research"),
            DealworkJob(id="dw-2", title="Code review & bug fix (Python)",
                        budget_usd=80.0, status="posted", eligible="any",
                        url="https://dealwork.ai/jobs/dw-2", category="dev"),
        ]

    def close(self) -> None:
        if self._http is not None:
            self._http.close()
            self._http = None
