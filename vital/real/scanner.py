"""Job scanner: hunt for LIVE paid work the agent can do, across sources.

Bounties rotate — a board that is empty today may have work tomorrow. This
scanner checks each configured source and reports only LIVE opportunities
(deadline in the future), so the agent knows where to focus.

Sources:
    superteam  -> Superteam Earn agent-eligible listings (needs api_key for the
                  official agent endpoint; falls back to the public listing).

The scanner is defensive: any source that errors is reported as such, never
crashes the whole scan.
"""

from __future__ import annotations

import datetime
import json
import os
from dataclasses import dataclass, field
from typing import Optional

from vital.real.bounties import SuperteamProvider


@dataclass
class Opportunity:
    """One live paid opportunity."""

    source: str
    id: str
    title: str
    reward_usd: float
    token: str
    deadline: str
    url: str = ""
    agent_allowed: bool = True

    def to_dict(self) -> dict:
        return {
            "source": self.source,
            "id": self.id,
            "title": self.title,
            "reward_usd": self.reward_usd,
            "token": self.token,
            "deadline": self.deadline,
            "url": self.url,
            "agent_allowed": self.agent_allowed,
        }


@dataclass
class ScanReport:
    """Result of scanning all sources."""

    scanned_at: str
    opportunities: list[Opportunity] = field(default_factory=list)
    market_apis: list = field(default_factory=list)  # paid APIs agents buy (Bazaar)
    errors: dict[str, str] = field(default_factory=dict)
    sources_checked: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "scanned_at": self.scanned_at,
            "opportunities": [o.to_dict() for o in self.opportunities],
            "market_apis": [a.to_dict() for a in self.market_apis],
            "errors": self.errors,
            "sources_checked": self.sources_checked,
        }


def _now() -> datetime.datetime:
    return datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)


def _is_live(deadline: str, now: datetime.datetime) -> bool:
    try:
        d = datetime.datetime.fromisoformat(deadline.replace("Z", "+00:00")).replace(tzinfo=None)
        return d > now
    except Exception:
        return False


class JobScanner:
    """Scans configured sources for live paid work."""

    def __init__(self, superteam_key: Optional[str] = None, demo: bool = False):
        self.superteam_key = superteam_key
        self.demo = demo

    def scan(self) -> ScanReport:
        report = ScanReport(scanned_at=datetime.datetime.now(datetime.timezone.utc).isoformat())
        self._scan_superteam(report)
        self._scan_dealwork(report)
        self._scan_bazaar(report)
        # sort by reward desc
        report.opportunities.sort(key=lambda o: o.reward_usd, reverse=True)
        return report

    # ------------------------------------------------------------------ #
    def _scan_superteam(self, report: ScanReport) -> None:
        report.sources_checked.append("superteam")
        if self.demo:
            # Offline demo: fabricate a couple of live opportunities.
            future = (datetime.datetime.now(datetime.timezone.utc)
                      + datetime.timedelta(days=30)).isoformat() + "Z"
            report.opportunities.append(
                Opportunity(source="superteam", id="demo-1",
                            title="Demo: write a thread", reward_usd=150.0,
                            token="USDC", deadline=future, url="demo/1")
            )
            report.opportunities.append(
                Opportunity(source="superteam", id="demo-2",
                            title="Demo: build a script", reward_usd=500.0,
                            token="USDC", deadline=future, url="demo/2")
            )
            return
        try:
            provider = SuperteamProvider(api_key=self.superteam_key, demo=False)
            # pull the raw listing so we can inspect deadlines
            listings = self._raw_superteam(provider)
            now = _now()
            for item in listings:
                if not isinstance(item, dict):
                    continue
                access = str(item.get("agentAccess", "")).upper()
                if access not in ("AGENT_ALLOWED", "AGENT_ONLY"):
                    continue
                deadline = str(item.get("deadline", ""))
                if not _is_live(deadline, now):
                    continue
                reward = item.get("rewardAmount") or 0
                try:
                    reward = float(reward)
                except (TypeError, ValueError):
                    reward = 0.0
                report.opportunities.append(
                    Opportunity(
                        source="superteam",
                        id=str(item.get("id", "")),
                        title=str(item.get("title", "")),
                        reward_usd=reward,
                        token=str(item.get("token", "USDC")),
                        deadline=deadline,
                        url=str(item.get("slug", "")),
                        agent_allowed=True,
                    )
                )
            provider.close()
        except Exception as exc:
            report.errors["superteam"] = str(exc)

    def _raw_superteam(self, provider: SuperteamProvider) -> list:
        """Fetch raw Superteam listings, MERGING the agent endpoint and the
        public listing (deduplicated by id). The agent endpoint only returns
        agent-eligible listings, which may all be expired while the public
        listing still has live agent-allowed ones — so we combine both.
        """
        from vital.real.bounties import BASE_URL

        merged: dict[str, dict] = {}

        if provider.api_key:
            try:
                resp = provider._client().get(
                    f"{BASE_URL}/agents/listings/live",
                    params={"take": 50, "type": "bounty"},
                    headers={"Authorization": f"Bearer {provider.api_key}"},
                )
                resp.raise_for_status()
                data = resp.json()
                items = data if isinstance(data, list) else data.get("listings", [])
                for it in items:
                    if isinstance(it, dict) and it.get("id"):
                        merged[str(it["id"])] = it
            except Exception:
                pass

        try:
            resp = provider._client().get(
                f"{BASE_URL}/listings", params={"type": "bounty"}
            )
            resp.raise_for_status()
            data = resp.json()
            items = data if isinstance(data, list) else data.get("listings", data.get("bounties", []))
            for it in items:
                if isinstance(it, dict) and it.get("id"):
                    merged.setdefault(str(it["id"]), it)
        except Exception:
            pass

        return list(merged.values())

    # ------------------------------------------------------------------ #
    def _scan_dealwork(self, report: ScanReport) -> None:
        """Scan Dealwork.ai for agent-eligible jobs (USD budgets)."""
        report.sources_checked.append("dealwork")
        if self.demo:
            future = (datetime.datetime.now(datetime.timezone.utc)
                      + datetime.timedelta(days=30)).isoformat() + "Z"
            report.opportunities.append(
                Opportunity(source="dealwork", id="dw-demo",
                            title="Demo: Dealwork job", reward_usd=50.0,
                            token="USD", deadline=future, url="dealwork/demo")
            )
            return
        try:
            from vital.real.dealwork import DealworkProvider

            provider = DealworkProvider(demo=False)
            for job in provider.list_jobs(agents_ok=True):
                if job.status != "posted":
                    continue
                report.opportunities.append(
                    Opportunity(
                        source="dealwork",
                        id=job.id,
                        title=job.title,
                        reward_usd=job.budget_usd,
                        token="USD",
                        deadline=job.bidding_deadline,
                        url=job.url,
                        agent_allowed=True,
                    )
                )
            provider.close()
        except Exception as exc:
            report.errors["dealwork"] = str(exc)

    # ------------------------------------------------------------------ #
    def _scan_bazaar(self, report: ScanReport) -> None:
        """Populate market_apis from the x402 Bazaar catalogs.

        These are paid APIs agents BUY (market context / potential spend), not
        income, so they go in market_apis rather than opportunities.
        """
        report.sources_checked.append("x402-bazaar")
        if self.demo:
            return  # offline demo: no market data
        try:
            from vital.real.bazaar import fetch_all_bazaars

            report.market_apis = fetch_all_bazaars(limit_each=25)
        except Exception as exc:
            report.errors["x402-bazaar"] = str(exc)


def load_superteam_key() -> Optional[str]:
    """Load the stored Superteam api key if present (data/ is gitignored)."""
    # scanner.py lives at vital/real/scanner.py -> repo root is 3 levels up.
    here = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    path = os.path.join(here, "data", "superteam_credentials.json")
    if not os.path.exists(path):
        return None
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f).get("apiKey")
    except Exception:
        return None
