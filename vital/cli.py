"""Command line interface for VITAL.

Usage:
    vital            -> launch the TUI
    vital tui        -> launch the TUI
    vital headless N -> run N ticks without UI and print a summary
    vital reset      -> delete the saved game
    vital status     -> print the saved agent's status
"""

from __future__ import annotations

import argparse
import sys

from vital.core.engine import Engine
from vital.core.formatting import fmt_credits, fmt_ticks, status_word
from vital.core import persistence


def _cmd_headless(ticks: int, seed: int | None) -> int:
    from vital.core.state import GameConfig

    engine = Engine(config=GameConfig(seed=seed))
    reports = engine.run(ticks)
    agent = engine.agent

    print("=" * 60)
    print(f" VITAL — simulación headless ({len(reports)} ticks)")
    print("=" * 60)
    for rep in reports[-15:]:
        line = f"  t{rep.tick:>4}  "
        if rep.decision:
            line += f"{rep.decision.action.value:<5} "
        if rep.task_completed:
            line += f"✅ {rep.task_completed} +{rep.task_reward:.1f}₵  "
        if rep.upgrade_bought:
            line += f"🛒 {rep.upgrade_bought}  "
        if rep.event_name:
            line += f"🎲 {rep.event_name}  "
        print(line)
    print("-" * 60)
    print(f"  Estado final : {status_word(agent)}")
    print(f"  Créditos     : {fmt_credits(agent.credits)}")
    print(f"  Esperanza    : {fmt_ticks(agent.runway)}")
    print(f"  Ganado       : {fmt_credits(agent.total_earned)}")
    print(f"  Gastado      : {fmt_credits(agent.total_spent)}")
    print(f"  Tareas       : {agent.tasks_done} hechas / {agent.tasks_failed} fallidas")
    print(f"  Mejoras      : {len(agent.upgrades)}")
    if not agent.alive:
        print(f"  ☠️  Causa: {agent.death_cause}")
    if agent.retired:
        print("  🏆 ¡VICTORIA! VITAL es financieramente libre.")
    print("=" * 60)
    return 0 if (agent.alive or agent.retired) else 1


def _cmd_status() -> int:
    engine = persistence.load_engine()
    if engine is None:
        print("No hay partida guardada. Ejecuta `vital` para empezar.")
        return 1
    agent = engine.agent
    print(f"VITAL guardado — tick {engine.world.tick}")
    print(f"  Estado   : {status_word(agent)}")
    print(f"  Créditos : {fmt_credits(agent.credits)}")
    print(f"  Esperanza: {fmt_ticks(agent.runway)}")
    print(f"  Energía  : {agent.energy:.0f}")
    print(f"  Habilidad: {agent.skill:.2f}")
    return 0


def _cmd_tui() -> int:
    from vital.tui.app import VitalApp

    app = VitalApp()
    app.run()
    return 0


def main(argv: list[str] | None = None) -> int:
    # Windows consoles default to cp1252; force UTF-8 so emoji survive.
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass

    parser = argparse.ArgumentParser(
        prog="vital",
        description="VITAL: un agente que debe ganar su propio dinero... o morir.",
    )
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("tui", help="Lanza la interfaz TUI")

    p_head = sub.add_parser("headless", help="Simula N ticks sin interfaz")
    p_head.add_argument("ticks", nargs="?", type=int, default=200)
    p_head.add_argument("--seed", type=int, default=None)

    sub.add_parser("reset", help="Borra la partida guardada")
    sub.add_parser("status", help="Muestra el estado guardado")

    args = parser.parse_args(argv)

    if args.command == "headless":
        return _cmd_headless(args.ticks, args.seed)
    if args.command == "reset":
        persistence.clear_save()
        print("Partida borrada.")
        return 0
    if args.command == "status":
        return _cmd_status()
    # default: tui
    return _cmd_tui()


if __name__ == "__main__":
    sys.exit(main())
