"""The real agent's planner: an LLM decides what paid work to pursue.

This is the "get a real job" brain. Given the agent's finances and the income
opportunities it can see (bounties, its own x402 service, tips), the LLM picks
an action and, for bounties, drafts the work to submit.

The planner returns a structured Plan (JSON) so the survival loop can execute
it deterministically. It is fully testable with a fake LLM.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Optional

from vital.real.bounties import Bounty

# The actions the planner may choose.
ACTION_WORK_BOUNTY = "work_bounty"
ACTION_PROMOTE_SERVICE = "promote_service"
ACTION_REST = "rest"
ACTION_WAIT = "wait"

VALID_ACTIONS = {ACTION_WORK_BOUNTY, ACTION_PROMOTE_SERVICE, ACTION_REST, ACTION_WAIT}


@dataclass
class Plan:
    """A single decided action."""

    action: str = ACTION_WAIT
    bounty_id: str = ""
    draft: str = ""
    reason: str = ""

    def to_dict(self) -> dict:
        return {
            "action": self.action,
            "bounty_id": self.bounty_id,
            "draft": self.draft,
            "reason": self.reason,
        }


PLANNER_SYSTEM = (
    "You are VITAL, an autonomous agent that must earn real money to pay for its "
    "own compute and survive. You see your finances and a list of paid "
    "opportunities. Choose exactly ONE action and reply with ONLY a JSON object, "
    "no prose. Schema: "
    '{"action": "work_bounty"|"promote_service"|"rest"|"wait", '
    '"bounty_id": "<id if work_bounty else empty>", '
    '"draft": "<the work to submit if work_bounty, else empty>", '
    '"reason": "<one short sentence>"}'
)


class Planner:
    """Decides the agent's next paid action using an LLM."""

    def __init__(self, llm_client):
        self.llm = llm_client

    # ------------------------------------------------------------------ #
    def build_prompt(self, status: dict, bounties: list[Bounty]) -> str:
        lines = [
            f"Balance: ${status.get('balance', 0):.6f}",
            f"Total earned: ${status.get('total_income', 0):.6f}",
            f"Total spent: ${status.get('total_expense', 0):.6f}",
            f"Runway: {status.get('runway_thoughts', 0):.0f} thoughts left",
            "",
            "Paid opportunities you can act on:",
        ]
        if bounties:
            for b in bounties[:8]:
                lines.append(
                    f"- bounty id={b.id} reward=${b.reward_usd:.0f} {b.token} "
                    f"title={b.title!r} skills={','.join(b.skills) or '-'}"
                )
        else:
            lines.append("- (no open bounties; you may promote_service or wait)")
        lines.append("")
        lines.append("Choose your next action. Reply with ONLY the JSON object.")
        return "\n".join(lines)

    def decide(self, status: dict, bounties: list[Bounty]) -> Plan:
        """Ask the LLM for a plan; parse it defensively."""
        prompt = self.build_prompt(status, bounties)
        result = self.llm.think(prompt, system=PLANNER_SYSTEM)
        return self.parse(result.text, bounties)

    # ------------------------------------------------------------------ #
    def parse(self, text: str, bounties: list[Bounty]) -> Plan:
        """Parse the LLM's JSON reply into a Plan, tolerating noise."""
        obj = self._extract_json(text)
        if obj is None:
            return Plan(action=ACTION_WAIT, reason="could not parse LLM reply")

        action = str(obj.get("action", ACTION_WAIT)).strip().lower()
        if action not in VALID_ACTIONS:
            action = ACTION_WAIT

        bounty_id = str(obj.get("bounty_id", "")).strip()
        draft = str(obj.get("draft", "")).strip()
        reason = str(obj.get("reason", "")).strip()

        # Only allow a bounty_id that actually exists.
        valid_ids = {b.id for b in bounties}
        if action == ACTION_WORK_BOUNTY and bounty_id not in valid_ids:
            # fall back to the best available bounty if the id is bogus
            if bounties:
                best = max(bounties, key=lambda b: b.reward_usd)
                bounty_id = best.id
            else:
                action = ACTION_WAIT
                bounty_id = ""

        return Plan(action=action, bounty_id=bounty_id, draft=draft, reason=reason)

    @staticmethod
    def _extract_json(text: str) -> Optional[dict]:
        """Pull the first JSON object out of possibly-noisy LLM output."""
        if not text:
            return None
        # try the whole thing first
        try:
            obj = json.loads(text)
            if isinstance(obj, dict):
                return obj
        except (json.JSONDecodeError, ValueError):
            pass
        # find the first {...} block
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            try:
                obj = json.loads(match.group(0))
                if isinstance(obj, dict):
                    return obj
            except (json.JSONDecodeError, ValueError):
                return None
        return None
