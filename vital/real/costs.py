"""Real cost tracking: what the agent ACTUALLY pays for its thinking.

The agent's cost of living is the real USD it spends on LLM API calls.
This module computes that cost from token usage using a pricing table.

Prices are USD per 1M tokens. Update PRICING as model prices change.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

# USD per 1M tokens: (input, output). Update as prices change.
# Verified 2025 against the LiteLLM price table and Anthropic pricing page.
PRICING: dict[str, tuple[float, float]] = {
    # OpenAI
    "gpt-4o-mini": (0.15, 0.60),
    "gpt-4o": (2.50, 10.00),
    "gpt-4.1-mini": (0.40, 1.60),
    "gpt-4.1-nano": (0.10, 0.40),
    "o3-mini": (1.10, 4.40),
    "o4-mini": (1.10, 4.40),
    "gpt-5": (1.25, 10.00),
    "gpt-5-mini": (0.25, 2.00),
    "gpt-5-nano": (0.05, 0.40),
    # Anthropic
    "claude-3-5-haiku-20241022": (0.80, 4.00),
    "claude-3-5-haiku-latest": (0.80, 4.00),
    "claude-3-5-sonnet-20241022": (3.00, 15.00),
    "claude-3-7-sonnet-latest": (3.00, 15.00),
    "claude-haiku-4-5": (1.00, 5.00),
    "claude-sonnet-4-5": (3.00, 15.00),
    "claude-sonnet-4-6": (3.00, 15.00),
    "claude-sonnet-5": (2.00, 10.00),
    "claude-opus-4-5": (5.00, 25.00),
}

DEFAULT_PRICING = (1.00, 3.00)  # fallback if model unknown


@dataclass
class LLMUsage:
    """Token usage from one LLM call."""

    model: str
    prompt_tokens: int = 0
    completion_tokens: int = 0

    @property
    def total_tokens(self) -> int:
        return self.prompt_tokens + self.completion_tokens

    def cost_usd(self) -> float:
        """Real USD cost of this call."""
        inp, out = PRICING.get(self.model, DEFAULT_PRICING)
        return (self.prompt_tokens * inp + self.completion_tokens * out) / 1_000_000

    @classmethod
    def from_openai(cls, response) -> "LLMUsage":
        """Extract usage from an OpenAI chat completion response."""
        u = getattr(response, "usage", None)
        model = getattr(response, "model", "gpt-4o-mini")
        return cls(
            model=model,
            prompt_tokens=getattr(u, "prompt_tokens", 0) or 0,
            completion_tokens=getattr(u, "completion_tokens", 0) or 0,
        )

    @classmethod
    def from_anthropic(cls, response) -> "LLMUsage":
        """Extract usage from an Anthropic message response."""
        u = getattr(response, "usage", None)
        model = getattr(response, "model", "claude-3-5-haiku-latest")
        return cls(
            model=model,
            prompt_tokens=getattr(u, "input_tokens", 0) or 0,
            completion_tokens=getattr(u, "output_tokens", 0) or 0,
        )


@dataclass
class CostTracker:
    """Accumulates real spend across calls."""

    total_usd: float = 0.0
    calls: int = 0
    total_tokens: int = 0
    by_model: dict[str, float] = field(default_factory=dict)
    history: list[float] = field(default_factory=list)  # cost per call

    def record(self, usage: LLMUsage) -> float:
        """Record one call; returns its cost in USD."""
        cost = usage.cost_usd()
        self.total_usd += cost
        self.calls += 1
        self.total_tokens += usage.total_tokens
        self.by_model[usage.model] = self.by_model.get(usage.model, 0.0) + cost
        self.history.append(cost)
        if len(self.history) > 512:
            self.history = self.history[-512:]
        return cost

    @property
    def avg_cost_per_call(self) -> float:
        return self.total_usd / self.calls if self.calls else 0.0

    def to_dict(self) -> dict:
        return {
            "total_usd": round(self.total_usd, 8),
            "calls": self.calls,
            "total_tokens": self.total_tokens,
            "by_model": {k: round(v, 8) for k, v in self.by_model.items()},
        }

    @classmethod
    def from_dict(cls, d: dict) -> "CostTracker":
        return cls(
            total_usd=d.get("total_usd", 0.0),
            calls=d.get("calls", 0),
            total_tokens=d.get("total_tokens", 0),
            by_model=dict(d.get("by_model", {})),
        )
