"""Tests for the real agent's planner (LLM decides paid work)."""

from __future__ import annotations

import pytest

from vital.real.bounties import Bounty
from vital.real.costs import LLMUsage
from vital.real.llm import ThinkResult
from vital.real.planner import (
    ACTION_PROMOTE_SERVICE,
    ACTION_REST,
    ACTION_WAIT,
    ACTION_WORK_BOUNTY,
    Plan,
    Planner,
)


class FakeLLM:
    """Returns a canned reply so planner tests are deterministic."""

    def __init__(self, reply: str):
        self.reply = reply
        self.calls = 0

    def think(self, prompt: str, system: str = "") -> ThinkResult:
        self.calls += 1
        usage = LLMUsage(model="test", prompt_tokens=10, completion_tokens=10)
        return ThinkResult(text=self.reply, usage=usage, cost_usd=0.0001)


BOUNTIES = [
    Bounty(id="b1", title="small", reward_usd=50.0, token="USDC", agent_allowed=True),
    Bounty(id="b2", title="big", reward_usd=500.0, token="USDC", agent_allowed=True),
]


def test_parse_work_bounty():
    p = Planner(FakeLLM('{"action":"work_bounty","bounty_id":"b2","draft":"d","reason":"r"}'))
    plan = p.decide({}, BOUNTIES)
    assert plan.action == ACTION_WORK_BOUNTY
    assert plan.bounty_id == "b2"
    assert plan.draft == "d"


def test_parse_tolerates_json_embedded_in_prose():
    reply = 'Sure! Here you go: {"action":"rest","reason":"tired"} hope that helps'
    p = Planner(FakeLLM(reply))
    plan = p.decide({}, BOUNTIES)
    assert plan.action == ACTION_REST


def test_invalid_action_falls_back_to_wait():
    p = Planner(FakeLLM('{"action":"hack_the_planet"}'))
    plan = p.decide({}, BOUNTIES)
    assert plan.action == ACTION_WAIT


def test_bogus_bounty_id_falls_back_to_best():
    p = Planner(FakeLLM('{"action":"work_bounty","bounty_id":"nope"}'))
    plan = p.decide({}, BOUNTIES)
    assert plan.action == ACTION_WORK_BOUNTY
    assert plan.bounty_id == "b2"  # highest reward


def test_work_bounty_with_no_bounties_waits():
    p = Planner(FakeLLM('{"action":"work_bounty","bounty_id":"b1"}'))
    plan = p.decide({}, [])
    assert plan.action == ACTION_WAIT
    assert plan.bounty_id == ""


def test_unparseable_reply_waits():
    p = Planner(FakeLLM("I refuse to speak JSON."))
    plan = p.decide({}, BOUNTIES)
    assert plan.action == ACTION_WAIT
    assert "parse" in plan.reason


def test_build_prompt_lists_bounties():
    p = Planner(FakeLLM("{}"))
    prompt = p.build_prompt({"balance": 1.0, "total_income": 1.0,
                             "total_expense": 0.0, "runway_thoughts": 10}, BOUNTIES)
    assert "b1" in prompt and "b2" in prompt
    assert "$500" in prompt


def test_plan_to_dict():
    plan = Plan(action=ACTION_PROMOTE_SERVICE, reason="r")
    d = plan.to_dict()
    assert d["action"] == ACTION_PROMOTE_SERVICE
