"""Formatting helpers shared by the TUI and CLI."""

from __future__ import annotations

from vital.core.state import Agent


def fmt_credits(value: float) -> str:
    if value >= 1_000_000:
        return f"{value / 1_000_000:.2f}M₵"
    if value >= 10_000:
        return f"{value / 1_000:.1f}k₵"
    return f"{value:,.1f}₵"


def fmt_ticks(ticks: float) -> str:
    if ticks == float("inf"):
        return "∞"
    t = int(ticks)
    if t < 60:
        return f"{t} ticks"
    if t < 3600:
        return f"{t // 60}m {t % 60:02d}t"
    return f"{t // 3600}h {(t % 3600) // 60:02d}m"


def life_bar_color(agent: Agent) -> str:
    """Color for the life bar depending on runway urgency."""
    runway = agent.runway
    if runway < 10:
        return "#ff3b30"  # red
    if runway < 25:
        return "#ff9f0a"  # orange
    if runway < 60:
        return "#ffd60a"  # yellow
    return "#30d158"      # green


def mood_face(agent: Agent) -> str:
    if not agent.alive:
        return "💀"
    if agent.retired:
        return "😎"
    if agent.mood > 0.8:
        return "😄"
    if agent.mood > 0.55:
        return "🙂"
    if agent.mood > 0.3:
        return "😐"
    return "😟"


def status_word(agent: Agent) -> str:
    if not agent.alive:
        return "MUERTO"
    if agent.retired:
        return "LIBRE"
    if agent.runway < 10:
        return "CRÍTICO"
    if agent.runway < 25:
        return "EN RIESGO"
    if agent.active_task:
        return "TRABAJANDO"
    return "ESTABLE"
