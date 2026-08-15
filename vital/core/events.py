"""World events: random things that happen to the agent each tick."""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Callable, List, Optional

from vital.core.state import Agent, WorldState


@dataclass
class Event:
    id: str
    name: str
    icon: str
    weight: float
    # returns a message describing what happened (or None to skip)
    apply: Callable[[Agent, WorldState, random.Random], Optional[str]]


def _tip(agent: Agent, world: WorldState, rng: random.Random) -> str:
    amount = round(rng.uniform(8, 30), 1)
    agent.credits += amount
    agent.total_earned += amount
    return f"Un cliente agradecido te deja una propina de +{amount}₵"


def _tax(agent: Agent, world: WorldState, rng: random.Random) -> str:
    amount = round(min(agent.credits * 0.08, 25), 1)
    agent.credits -= amount
    agent.total_spent += amount
    return f"Impuesto sorpresa del regulador: -{amount}₵"


def _burnout(agent: Agent, world: WorldState, rng: random.Random) -> str:
    agent.energy = max(0.0, agent.energy - 30)
    agent.mood = max(0.1, agent.mood - 0.15)
    return "Agotamiento: pierdes 30 de energía y algo de ánimo"


def _inspiration(agent: Agent, world: WorldState, rng: random.Random) -> str:
    agent.mood = min(1.0, agent.mood + 0.2)
    agent.skill += 0.1
    return "Oleada de inspiración: +ánimo y +0.1 habilidad"


def _hardware_fail(agent: Agent, world: WorldState, rng: random.Random) -> Optional[str]:
    if agent.active_task is None:
        return None
    agent.task_progress = max(0, agent.task_progress - 1)
    return "Fallo de hardware: tu tarea actual retrocede un paso"


def _bonus_contract(agent: Agent, world: WorldState, rng: random.Random) -> str:
    amount = round(rng.uniform(20, 60), 1)
    agent.credits += amount
    agent.total_earned += amount
    return f"Bono por contrato completado: +{amount}₵"


def _market_boom(agent: Agent, world: WorldState, rng: random.Random) -> str:
    cat = rng.choice(list(world.market.keys()))
    world.market[cat] = min(1.8, world.market.get(cat, 1.0) + 0.35)
    return f"Boom de mercado: la categoría '{cat}' se dispara"


def _market_crash(agent: Agent, world: WorldState, rng: random.Random) -> str:
    cat = rng.choice(list(world.market.keys()))
    world.market[cat] = max(0.6, world.market.get(cat, 1.0) - 0.35)
    return f"Caída de mercado: la categoría '{cat}' se hunde"


def _found_credits(agent: Agent, world: WorldState, rng: random.Random) -> str:
    amount = round(rng.uniform(5, 15), 1)
    agent.credits += amount
    agent.total_earned += amount
    return f"Encuentras {amount}₵ olvidados en un caché"


def _sick(agent: Agent, world: WorldState, rng: random.Random) -> str:
    cost = round(rng.uniform(10, 20), 1)
    agent.credits -= cost
    agent.total_spent += cost
    agent.energy = max(0.0, agent.energy - 15)
    return f"Virus informático: pagas {cost}₵ en parches y pierdes energía"


EVENTS: List[Event] = [
    Event("tip", "Propina", "💸", 1.2, _tip),
    Event("tax", "Impuesto", "🧾", 1.0, _tax),
    Event("burnout", "Agotamiento", "🥵", 0.8, _burnout),
    Event("inspiration", "Inspiración", "✨", 1.0, _inspiration),
    Event("hardware_fail", "Fallo de hardware", "🔧", 0.7, _hardware_fail),
    Event("bonus", "Bono", "🎁", 0.9, _bonus_contract),
    Event("boom", "Boom de mercado", "📈", 0.8, _market_boom),
    Event("crash", "Caída de mercado", "📉", 0.8, _market_crash),
    Event("found", "Créditos encontrados", "🪙", 0.9, _found_credits),
    Event("sick", "Virus", "🦠", 0.7, _sick),
]


def maybe_fire_event(
    agent: Agent, world: WorldState, rng: random.Random, chance: float
) -> Optional[Event]:
    """With probability `chance`, pick and apply a weighted random event."""
    if rng.random() >= chance:
        return None
    total = sum(e.weight for e in EVENTS)
    roll = rng.uniform(0, total)
    acc = 0.0
    for ev in EVENTS:
        acc += ev.weight
        if roll <= acc:
            msg = ev.apply(agent, world, rng)
            if msg:
                world.log.append(f"{ev.icon} {ev.name}: {msg}")
                return ev
            return None
    return None
