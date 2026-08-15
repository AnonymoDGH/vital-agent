"""Economy: job catalog, upgrade shop and market dynamics."""

from __future__ import annotations

import random
from typing import Dict

from vital.core.state import TaskDef, Upgrade

# --------------------------------------------------------------------------- #
# Job catalog
# --------------------------------------------------------------------------- #
TASKS: Dict[str, TaskDef] = {
    t.id: t
    for t in [
        TaskDef(
            id="micro",
            name="Micro-tareas",
            icon="⚡",
            duration=1,
            base_reward=8.0,
            energy_cost=7.0,
            risk=0.05,
            category="gig",
        ),
        TaskDef(
            id="data",
            name="Etiquetado de datos",
            icon="🏷️",
            duration=2,
            base_reward=22.0,
            energy_cost=9.0,
            risk=0.10,
            category="gig",
        ),
        TaskDef(
            id="support",
            name="Soporte técnico",
            icon="🎧",
            duration=3,
            base_reward=42.0,
            energy_cost=11.0,
            risk=0.12,
            skill_gate=1.5,
            category="service",
        ),
        TaskDef(
            id="code",
            name="Freelance de código",
            icon="💻",
            duration=4,
            base_reward=80.0,
            energy_cost=13.0,
            risk=0.15,
            skill_gate=2.5,
            category="dev",
        ),
        TaskDef(
            id="audit",
            name="Auditoría de sistemas",
            icon="🔍",
            duration=6,
            base_reward=160.0,
            energy_cost=15.0,
            risk=0.20,
            skill_gate=4.0,
            category="dev",
        ),
        TaskDef(
            id="contract",
            name="Contrato corporativo",
            icon="🏢",
            duration=9,
            base_reward=340.0,
            energy_cost=17.0,
            risk=0.25,
            skill_gate=6.0,
            category="enterprise",
        ),
    ]
}

# --------------------------------------------------------------------------- #
# Upgrade shop
# --------------------------------------------------------------------------- #
UPGRADES: Dict[str, Upgrade] = {
    u.id: u
    for u in [
        Upgrade(
            id="bot1",
            name="Bot de micro-ingresos",
            icon="🤖",
            cost=90.0,
            blurb="+1.5 créditos/tick pasivos",
            kind="passive",
            power=1.5,
        ),
        Upgrade(
            id="bot2",
            name="Granja de bots",
            icon="🏭",
            cost=320.0,
            blurb="+4.5 créditos/tick pasivos",
            kind="passive",
            power=4.5,
        ),
        Upgrade(
            id="bot3",
            name="Enjambre autónomo",
            icon="🛰️",
            cost=900.0,
            blurb="+11 créditos/tick pasivos",
            kind="passive",
            power=11.0,
        ),
        Upgrade(
            id="solar",
            name="Núcleo solar",
            icon="☀️",
            cost=150.0,
            blurb="-25% coste de vida (burn)",
            kind="burn",
            power=0.25,
        ),
        Upgrade(
            id="frugal",
            name="Modo frugal",
            icon="🌙",
            cost=420.0,
            blurb="-25% adicional de burn",
            kind="burn",
            power=0.25,
        ),
        Upgrade(
            id="rep",
            name="Reputación premium",
            icon="⭐",
            cost=260.0,
            blurb="+20% recompensas de tareas",
            kind="reward",
            power=0.20,
        ),
        Upgrade(
            id="mentor",
            name="Mentor IA",
            icon="🧠",
            cost=520.0,
            blurb="+35% recompensas de tareas",
            kind="reward",
            power=0.35,
        ),
        Upgrade(
            id="battery",
            name="Batería de grafeno",
            icon="🔋",
            cost=200.0,
            blurb="-30% coste de energía al trabajar",
            kind="energy",
            power=0.30,
        ),
        Upgrade(
            id="course",
            name="Curso acelerado",
            icon="📚",
            cost=180.0,
            blurb="+1.5 nivel de habilidad",
            kind="skill",
            power=1.5,
        ),
    ]
}

# Order shown in the shop
SHOP_ORDER = ["bot1", "bot2", "bot3", "solar", "frugal", "rep", "mentor", "battery", "course"]

# --------------------------------------------------------------------------- #
# Market dynamics
# --------------------------------------------------------------------------- #
_CATEGORIES = ("gig", "service", "dev", "enterprise")


def market_step(market: Dict[str, float], rng: random.Random) -> Dict[str, float]:
    """Random-walk the market multiplier for each category, clamped to [0.6, 1.8]."""
    if not market:
        market = {c: 1.0 for c in _CATEGORIES}
    for cat in _CATEGORIES:
        drift = rng.uniform(-0.12, 0.12)
        # gentle pull back toward 1.0
        pull = (1.0 - market.get(cat, 1.0)) * 0.15
        market[cat] = max(0.6, min(1.8, market.get(cat, 1.0) + drift + pull))
    return market
