"""The agent's real brain: an LLM client that costs real money.

Every time VITAL "thinks" it makes a real LLM API call and PAYS for it. That
cost is its cost of living. In demo mode the call is simulated (no network, no
spend) but still priced so the economics behave the same.

The client returns the text plus an LLMUsage so the caller can record the real
cost in the CostTracker and Ledger.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Optional

from vital.real.costs import LLMUsage, PRICING


@dataclass
class ThinkResult:
    """Result of one thinking step."""

    text: str
    usage: LLMUsage
    cost_usd: float
    simulated: bool = False


class LLMClient:
    """Calls a real LLM (or simulates it in demo mode)."""

    def __init__(self, config):
        self.config = config
        self._client = None

    # ------------------------------------------------------------------ #
    def think(self, prompt: str, system: str = "") -> ThinkResult:
        """One reasoning step. Costs real money in real mode."""
        if not self.config.is_real:
            return self._simulate(prompt)
        if self.config.llm_provider == "anthropic":
            return self._think_anthropic(prompt, system)
        return self._think_openai(prompt, system)

    # ------------------------------------------------------------------ #
    def _simulate(self, prompt: str) -> ThinkResult:
        """Demo: fabricate a plausible response and price it like a real call.

        We model a realistic agent thought: a few hundred prompt tokens of
        context plus a short completion. This keeps demo economics in the same
        ballpark as real mode so the survival dynamics match.
        """
        model = self.config.llm_model
        # ~1500 prompt + ~400 completion tokens ≈ a real reasoning step w/ context
        usage = LLMUsage(model=model, prompt_tokens=1500, completion_tokens=400)
        cost = usage.cost_usd()
        text = (
            "[demo] I considered my options. I should look for paid work to "
            "cover my costs and grow my balance."
        )
        return ThinkResult(text=text, usage=usage, cost_usd=cost, simulated=True)

    def _think_openai(self, prompt: str, system: str) -> ThinkResult:
        import openai

        if self._client is None:
            self._client = openai.OpenAI(api_key=self.config.openai_api_key)
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        resp = self._client.chat.completions.create(
            model=self.config.llm_model,
            messages=messages,
            max_tokens=512,
        )
        usage = LLMUsage.from_openai(resp)
        cost = usage.cost_usd()
        text = resp.choices[0].message.content or ""
        return ThinkResult(text=text, usage=usage, cost_usd=cost, simulated=False)

    def _think_anthropic(self, prompt: str, system: str) -> ThinkResult:
        import anthropic

        if self._client is None:
            self._client = anthropic.Anthropic(api_key=self.config.anthropic_api_key)
        resp = self._client.messages.create(
            model=self.config.llm_model,
            system=system or "You are VITAL, an autonomous agent that must earn money to survive.",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=512,
        )
        usage = LLMUsage.from_anthropic(resp)
        cost = usage.cost_usd()
        text = "".join(b.text for b in resp.content if getattr(b, "type", "") == "text")
        return ThinkResult(text=text, usage=usage, cost_usd=cost, simulated=False)
