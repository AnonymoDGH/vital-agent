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


def _cmd_real(cycles: int) -> int:
    """Run the REAL-economy agent (earn real money to pay real costs)."""
    from vital.real.agent import RealAgent
    from vital.real.config import load_real_config

    cfg = load_real_config()
    problems = cfg.validate()
    if problems:
        print("⚠️  Configuración incompleta para modo REAL:")
        for p in problems:
            print(f"   - {p}")
        print("   Ejecutando en modo DEMO (sin dinero real).")
        cfg.mode = "demo"

    try:
        agent = RealAgent(cfg)
    except RuntimeError as exc:
        print(f"❌ No se pudo iniciar el agente real: {exc}")
        return 1

    mode = "REAL 💸" if cfg.is_real else "DEMO (simulado)"
    print("=" * 62)
    print(f" VITAL — economía {mode}")
    print(f"   Wallet : {agent.wallet.address()}")
    print(f"   Saldo  : ${agent.ledger.balance:.6f}")
    print(f"   Ingresos: {[p.name for p in agent.providers]}")
    print("=" * 62)

    reports = agent.run(cycles)
    for rep in reports[-12:]:
        line = f"  c{rep.cycle:>3}  pensar ${rep.think_cost:.6f}  "
        if rep.earned > 0:
            line += f"ganado ${rep.earned:.6f}  "
        line += f"saldo ${rep.balance_after:.6f}  runway {rep.runway_actions:.0f}"
        if rep.died:
            line += "  💀"
        print(line)

    print("-" * 62)
    s = agent.status()
    print(f"  Estado      : {'💀 MUERTO' if s['dead'] else 'vivo'}")
    if s["dead"]:
        print(f"  Causa       : {s['death_reason']}")
    print(f"  Saldo       : ${s['balance']:.6f}")
    print(f"  Ingresos    : ${s['total_income']:.6f}")
    print(f"  Gastos      : ${s['total_expense']:.6f}")
    print(f"  Neto        : ${s['net']:.6f}")
    print(f"  Coste/pensar: ${s['avg_cost_per_thought']:.6f}")
    print(f"  Runway      : {s['runway_thoughts']:.0f} pensamientos")
    print("=" * 62)
    return 0 if not s["dead"] else 1


def _cmd_real_tui() -> int:
    from vital.tui.real_app import RealApp

    app = RealApp()
    app.run()
    return 0


def _cmd_wallet() -> int:
    """Show the agent's wallet (demo or real)."""
    from vital.real.config import load_real_config
    from vital.real.wallet import make_wallet

    cfg = load_real_config()
    try:
        wallet = make_wallet(cfg)
    except RuntimeError as exc:
        print(f"❌ No se pudo crear la wallet real: {exc}")
        print("   (En modo demo no se necesita; usa VITAL_MODE=real + credenciales CDP)")
        return 1
    kind = "REAL on-chain" if wallet.is_real else "DEMO (simulada)"
    print("=" * 62)
    print(f" VITAL wallet — {kind}")
    print(f"   Dirección : {wallet.address()}")
    print(f"   Saldo     : ${wallet.balance():.6f}")
    print("=" * 62)
    if not wallet.is_real:
        print("   Para una wallet REAL: pon VITAL_MODE=real y las credenciales CDP")
        print("   (CDP_API_KEY_ID, CDP_API_KEY_SECRET, CDP_WALLET_SECRET).")
        print("   Docs: docs/REAL_MODE.md")
    return 0


def _cmd_bounties(agent_only: bool) -> int:
    """List real bounties the agent could work (Superteam Earn)."""
    from vital.real.bounties import SuperteamProvider

    demo = not _env_real()
    provider = SuperteamProvider(demo=demo)
    bounties = provider.list_bounties(agent_only=agent_only)
    mode = "DEMO" if demo else "REAL (Superteam Earn)"
    print("=" * 62)
    print(f" Bounties — {mode} · {len(bounties)} encontrados")
    print("=" * 62)
    for b in bounties:
        flag = "🤖" if b.agent_allowed else "  "
        print(f"  {flag} [{b.id[:8]}] {b.title[:48]}")
        print(f"       ${b.reward_usd:.0f} {b.token} · skills: {','.join(b.skills) or '-'}")
    if not demo:
        print("-" * 62)
        print("  🤖 = AGENT_ALLOWED. El cobro final requiere que un humano")
        print("       visite /earn/claim/<claimCode> (los agentes no pasan KYC).")
    provider.close()
    return 0


def _cmd_serve(port: int, price: str, network: str) -> int:
    """Run the x402 paid service (the agent sells an HTTP API for USDC)."""
    from vital.real.config import load_real_config
    from vital.real.x402_service import run_service, TEST_FACILITATOR, PROD_FACILITATOR

    cfg = load_real_config()
    # In demo mode we still need an address to receive; use a placeholder.
    pay_to = _env("VITAL_PAY_TO", "")
    if not pay_to:
        if cfg.is_real:
            # derive from the real wallet
            try:
                from vital.real.wallet import make_wallet

                pay_to = make_wallet(cfg).address()
            except RuntimeError as exc:
                print(f"❌ {exc}")
                return 1
        else:
            pay_to = "0x0000000000000000000000000000000000000000"

    facilitator = PROD_FACILITATOR if network == "base" else TEST_FACILITATOR

    # Build the agent + bridge so settled x402 payments become real income.
    status_provider = None
    try:
        from vital.real.agent import RealAgent
        from vital.real.bridge import AgentStatusProvider

        agent = RealAgent(cfg)
        status_provider = AgentStatusProvider(agent)
    except RuntimeError:
        status_provider = None  # service still runs, income just not tracked

    print("=" * 62)
    print(" VITAL x402 paid service")
    print(f"   Cobrar a : {pay_to}")
    print(f"   Precio   : {price} USDC / request")
    print(f"   Red      : {network}")
    print(f"   Facilit. : {facilitator}")
    print(f"   URL      : http://127.0.0.1:{port}/")
    if status_provider is not None:
        print(f"   Saldo    : ${status_provider.agent.ledger.balance:.6f} (los cobros se suman aquí)")
    print("=" * 62)
    try:
        run_service(
            port=port,
            pay_to=pay_to,
            price_usdc=price,
            network=network,
            facilitator_url=facilitator,
            status_provider=status_provider,
        )
    except RuntimeError as exc:
        print(f"❌ {exc}")
        return 1
    return 0


def _env(name: str, default: str = "") -> str:
    import os

    return os.environ.get(name, default)


def _env_real() -> bool:
    return _env("VITAL_MODE", "demo").lower() == "real"


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

    p_real = sub.add_parser("real", help="Agente de economía REAL (gana dinero real)")
    p_real.add_argument("cycles", nargs="?", type=int, default=50)

    sub.add_parser("real-tui", help="TUI del agente de economía REAL")

    sub.add_parser("wallet", help="Muestra la wallet del agente (demo o real)")

    p_bount = sub.add_parser("bounties", help="Lista bounties reales (Superteam Earn)")
    p_bount.add_argument("--all", action="store_true", help="Incluir bounties no permitidos a agentes")

    p_serve = sub.add_parser("serve", help="Servicio x402: vende una API y cobra USDC")
    p_serve.add_argument("--port", type=int, default=8402)
    p_serve.add_argument("--price", type=str, default="0.001", help="USDC por request")
    p_serve.add_argument("--network", type=str, default="base-sepolia", help="base-sepolia (test) o base (mainnet)")

    args = parser.parse_args(argv)

    if args.command == "headless":
        return _cmd_headless(args.ticks, args.seed)
    if args.command == "reset":
        persistence.clear_save()
        print("Partida borrada.")
        return 0
    if args.command == "status":
        return _cmd_status()
    if args.command == "real":
        return _cmd_real(args.cycles)
    if args.command == "real-tui":
        return _cmd_real_tui()
    if args.command == "wallet":
        return _cmd_wallet()
    if args.command == "bounties":
        return _cmd_bounties(agent_only=not args.all)
    if args.command == "serve":
        return _cmd_serve(args.port, args.price, args.network)
    # default: tui
    return _cmd_tui()


if __name__ == "__main__":
    sys.exit(main())
