"""Check deadlines of all agent-eligible bounties (real API)."""
from __future__ import annotations

import datetime
import json
import os

import httpx

HERE = os.path.dirname(os.path.abspath(__file__))
CREDS = os.path.join(HERE, "..", "data", "superteam_credentials.json")


def main() -> None:
    creds = json.load(open(CREDS, encoding="utf-8"))
    key = creds["apiKey"]
    r = httpx.get(
        "https://superteam.fun/api/agents/listings/live",
        params={"take": 50, "type": "bounty"},
        headers={"Authorization": f"Bearer {key}"},
        timeout=30,
        follow_redirects=True,
    )
    lst = r.json()
    lst = lst if isinstance(lst, list) else lst.get("listings", [])
    now = datetime.datetime(2026, 8, 15)
    print("today ~", now.date())
    print()
    for x in lst:
        dl = x.get("deadline", "")
        try:
            d = datetime.datetime.fromisoformat(dl.replace("Z", "+00:00")).replace(tzinfo=None)
            live = d > now
        except Exception:
            live = None
        mark = "LIVE" if live else ("EXPIRED" if live is False else "?")
        reward = str(x.get("rewardAmount"))
        token = str(x.get("token"))
        title = x.get("title", "")[:45]
        print(f"{mark:8} {reward:>6} {token:5} deadline={dl[:10]}  {title}")


if __name__ == "__main__":
    main()
