"""Superteam Earn bounty provider — real crypto bounties an agent can work.

Superteam Earn (superteam.fun) is a Solana-ecosystem bounty board. It has a
verified-live Agent API (2025):

    POST https://superteam.fun/api/agents                     -> register, get apiKey
    GET  https://superteam.fun/api/listings?type=bounty       -> open bounties
    POST https://superteam.fun/api/agents/submissions/create  -> submit work (Bearer key)

Bounties pay USDC/SOL. Some listings are marked AGENT_ALLOWED / AGENT_ONLY.
Final payout requires a human to visit /earn/claim/<claimCode> (agents skip
KYC but a human signs the claim).

This module is defensive: every network call is wrapped, and in demo mode it
returns simulated listings so the flow can be exercised offline.

Full spec: https://superteam.fun/skill.md
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from typing import Optional

BASE_URL = "https://superteam.fun/api"


@dataclass
class Bounty:
    """One bounty listing."""

    id: str
    title: str
    reward_usd: float
    token: str
    agent_allowed: bool
    url: str = ""
    description: str = ""
    skills: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "reward_usd": self.reward_usd,
            "token": self.token,
            "agent_allowed": self.agent_allowed,
            "url": self.url,
            "skills": self.skills,
        }


class SuperteamProvider:
    """Client for the Superteam Earn Agent API."""

    def __init__(self, api_key: Optional[str] = None, demo: bool = True):
        self.api_key = api_key or os.environ.get("SUPERTEAM_API_KEY")
        self.demo = demo
        self._http = None

    # ------------------------------------------------------------------ #
    def _client(self):
        if self._http is None:
            import httpx

            self._http = httpx.Client(timeout=30.0)
        return self._http

    # ------------------------------------------------------------------ #
    def register(self) -> dict:
        """Register as an agent; returns {apiKey, claimCode, ...}."""
        if self.demo:
            return {"apiKey": "demo-key", "claimCode": "demo-claim", "demo": True}
        try:
            resp = self._client().post(f"{BASE_URL}/agents", json={})
            resp.raise_for_status()
            data = resp.json()
            self.api_key = data.get("apiKey") or self.api_key
            return data
        except Exception as exc:
            return {"error": str(exc)}

    def list_bounties(self, agent_only: bool = True) -> list[Bounty]:
        """Fetch open bounties. If agent_only, keep AGENT_ALLOWED/AGENT_ONLY.

        Uses the official agent endpoint /api/agents/listings/live when an
        api_key is available (returns agent-eligible listings by default);
        falls back to the public /api/listings otherwise.
        """
        if self.demo:
            return self._demo_bounties()

        listings = []
        if self.api_key:
            try:
                resp = self._client().get(
                    f"{BASE_URL}/agents/listings/live",
                    params={"take": 50, "type": "bounty"},
                    headers={"Authorization": f"Bearer {self.api_key}"},
                )
                resp.raise_for_status()
                data = resp.json()
                listings = data if isinstance(data, list) else data.get("listings", [])
            except Exception:
                listings = []
        if not listings:
            try:
                resp = self._client().get(f"{BASE_URL}/listings", params={"type": "bounty"})
                resp.raise_for_status()
                data = resp.json()
                listings = data if isinstance(data, list) else data.get("listings", data.get("bounties", []))
            except Exception:
                return []

        out: list[Bounty] = []
        for item in listings:
            if not isinstance(item, dict):
                continue
            access = str(item.get("agentAccess") or item.get("agent_access") or "").upper()
            allowed = access in ("AGENT_ALLOWED", "AGENT_ONLY")
            if agent_only and not allowed:
                continue
            reward = item.get("rewardAmount") or item.get("usdValue") or item.get("reward") or 0
            try:
                reward = float(reward)
            except (TypeError, ValueError):
                reward = 0.0
            out.append(
                Bounty(
                    id=str(item.get("id", "")),
                    title=str(item.get("title", "")),
                    reward_usd=reward,
                    token=str(item.get("token", "USDC")),
                    agent_allowed=allowed,
                    url=str(item.get("link") or item.get("url") or item.get("slug") or ""),
                    description=str(item.get("description", ""))[:500],
                    skills=list(item.get("skills", []) or []),
                )
            )
        return out

    def details(self, slug: str) -> dict:
        """Fetch full listing details by slug.

        Tries the authenticated agent endpoint first, then the public one.
        """
        if self.demo:
            return {"slug": slug, "demo": True}
        headers = (
            {"Authorization": f"Bearer {self.api_key}"} if self.api_key else {}
        )
        for url in (
            f"{BASE_URL}/agents/listings/details/{slug}",
            f"{BASE_URL}/listings/details/{slug}",
        ):
            try:
                resp = self._client().get(url, headers=headers)
                if resp.status_code == 200:
                    return resp.json()
            except Exception:
                continue
        return {"error": f"no details found for slug {slug!r}"}

    def submit(self, bounty_id: str, submission: dict) -> dict:
        """Submit work for a bounty. Requires a registered api_key."""
        if self.demo:
            return {"ok": True, "bounty_id": bounty_id, "demo": True}
        if not self.api_key:
            return {"error": "no api_key; call register() first"}
        try:
            resp = self._client().post(
                f"{BASE_URL}/agents/submissions/create",
                json={"bountyId": bounty_id, **submission},
                headers={"Authorization": f"Bearer {self.api_key}"},
            )
            resp.raise_for_status()
            return resp.json()
        except Exception as exc:
            return {"error": str(exc)}

    # ------------------------------------------------------------------ #
    def _demo_bounties(self) -> list[Bounty]:
        return [
            Bounty(
                id="demo-1",
                title="Write a thread about x402 payments",
                reward_usd=150.0,
                token="USDC",
                agent_allowed=True,
                url="https://superteam.fun/demo/1",
                skills=["writing"],
            ),
            Bounty(
                id="demo-2",
                title="Build a small Solana script",
                reward_usd=500.0,
                token="USDC",
                agent_allowed=True,
                url="https://superteam.fun/demo/2",
                skills=["development"],
            ),
        ]

    def close(self) -> None:
        if self._http is not None:
            self._http.close()
            self._http = None
