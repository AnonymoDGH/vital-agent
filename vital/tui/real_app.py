"""VITAL REAL TUI — watch the agent earn and spend REAL money.

A focused dashboard for the real-economy agent: balance, runway, income,
expenses, and a live activity log. Cursor-AI inspired dark theme.
"""

from __future__ import annotations

from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.reactive import reactive
from textual.timer import Timer
from textual.widgets import Footer, Label, Log, ProgressBar, Static

from vital.real.agent import RealAgent
from vital.real.config import load_real_config

CYCLE_SECONDS = 1.2


class RealApp(App):
    """Dashboard for the real-economy VITAL agent."""

    CSS_PATH = "real_app.tcss"
    TITLE = "VITAL REAL"
    SUB_TITLE = "gana dinero real o muere"

    BINDINGS = [
        ("q", "quit", "Salir"),
        ("space", "toggle_pause", "Pausa"),
        ("n", "new_life", "Nueva vida"),
    ]

    LAYERS = ["base", "overlay"]
    paused = reactive(False)

    def __init__(self, agent: RealAgent | None = None):
        super().__init__()
        self.agent = agent or RealAgent(load_real_config())
        self._timer: Timer | None = None

    # ------------------------------------------------------------------ #
    def compose(self) -> ComposeResult:
        cfg = self.agent.config
        mode = "REAL 💸" if cfg.is_real else "DEMO (simulado)"

        with Container(id="topbar"):
            yield Label(
                f"[b][#3fb950]◆[/] VITAL REAL[/]  [#8b949e]· economía {mode}[/]",
                classes="title",
            )

        with Horizontal(id="body"):
            with Vertical(id="sidebar"):
                with Container(classes="card"):
                    yield Label("SALDO REAL", classes="card-title")
                    yield Label("", id="balance-big", classes="big-number")
                    yield Label("", id="balance-sub", classes="subtle")
                with Container(classes="card"):
                    yield Label("RUNWAY (pensamientos)", classes="card-title")
                    yield Label("", id="runway-big", classes="big-number")
                    yield ProgressBar(id="runway-bar", total=100, show_eta=False)
                with Container(classes="card"):
                    yield Label("ECONOMÍA", classes="card-title")
                    yield Label("", id="eco-income", classes="subtle")
                    yield Label("", id="eco-expense", classes="subtle")
                    yield Label("", id="eco-net", classes="subtle")
                    yield Label("", id="eco-cost", classes="subtle")
                with Container(classes="card"):
                    yield Label("WALLET", classes="card-title")
                    yield Label("", id="wallet-addr", classes="subtle")
                    yield Label("", id="wallet-kind", classes="subtle")

            with Vertical(id="main"):
                yield Label("[b]Actividad del agente[/]", classes="card-title")
                yield Log(id="activity-log", highlight=True)

        yield Static("", id="statusbar")
        yield Footer()

        with Container(id="overlay"):
            with Vertical(id="overlay-box"):
                yield Label("", id="overlay-title", classes="headline")
                yield Label("", id="overlay-body")
                yield Label(
                    "[#8b949e]Pulsa [b]n[/b] para una nueva vida · [b]q[/b] para salir[/]",
                    id="overlay-hint",
                )

    # ------------------------------------------------------------------ #
    def on_mount(self) -> None:
        self._refresh()
        self._timer = self.set_interval(CYCLE_SECONDS, self._on_cycle)
        self.query_one("#activity-log", Log).focus()

    def _on_cycle(self) -> None:
        if self.paused or self.agent.ledger.dead:
            return
        rep = self.agent.run_cycle()
        log = self.query_one("#activity-log", Log)
        line = f"[c{rep.cycle}] pensar ${rep.think_cost:.6f}"
        if rep.earned > 0:
            line += f"  [#3fb950]+${rep.earned:.6f}[/] ({', '.join(rep.income_sources)})"
        line += f"  saldo ${rep.balance_after:.6f}"
        log.write_line(line)
        for msg in rep.messages:
            log.write_line(msg)
        if rep.died:
            self._show_overlay()
        self._refresh()

    # ------------------------------------------------------------------ #
    def _refresh(self) -> None:
        s = self.agent.status()
        bal = s["balance"]
        color = "#f85149" if bal < 0.05 else ("#d29922" if bal < 0.2 else "#3fb950")

        self.query_one("#balance-big", Label).update(
            f"[b][{color}]${bal:.6f}[/][/]"
        )
        self.query_one("#balance-sub", Label).update(
            f"modo {s['mode']} · ciclo {s['cycle']}"
        )

        runway = s["runway_thoughts"]
        runway_txt = "∞" if runway == float("inf") else f"{runway:.0f}"
        self.query_one("#runway-big", Label).update(f"[b][{color}]{runway_txt}[/][/]")
        bar_val = min(100.0, max(0.0, runway / 50.0))  # scale: 50 thoughts = full
        self.query_one("#runway-bar", ProgressBar).update(progress=bar_val)

        self.query_one("#eco-income", Label).update(
            f"[#3fb950]▲ ingresos ${s['total_income']:.6f}[/]"
        )
        self.query_one("#eco-expense", Label).update(
            f"[#f85149]▼ gastos ${s['total_expense']:.6f}[/]"
        )
        net = s["net"]
        net_color = "#3fb950" if net >= 0 else "#f85149"
        self.query_one("#eco-net", Label).update(
            f"[{net_color}]neto ${net:.6f}[/]"
        )
        self.query_one("#eco-cost", Label).update(
            f"coste/pensar ${s['avg_cost_per_thought']:.6f}"
        )

        addr = s["wallet_address"]
        short = addr[:6] + "…" + addr[-4:] if len(addr) > 14 else addr
        self.query_one("#wallet-addr", Label).update(short)
        self.query_one("#wallet-kind", Label).update(
            "[#f85149]REAL on-chain[/]" if s["wallet_is_real"] else "[#8b949e]demo (simulada)[/]"
        )

        pause_txt = " [#d29922]⏸ PAUSA[/]" if self.paused else ""
        state = "💀 MUERTO" if s["dead"] else "vivo"
        self.query_one("#statusbar", Static).update(
            f"[#8b949e]◆ VITAL REAL[/] · {state} · proveedores {','.join(s['providers'])}{pause_txt}   "
            f"[#8b949e][space] pausa · [n] nueva vida · [q] salir[/]"
        )

    # ------------------------------------------------------------------ #
    def _show_overlay(self) -> None:
        if self._timer:
            self._timer.stop()
        s = self.agent.status()
        self.query_one("#overlay-title", Label).update(
            "[b][#f85149]💀  VITAL SE HA QUEDADO SIN FONDOS[/][/]"
        )
        self.query_one("#overlay-body", Label).update(
            f"Causa: {s['death_reason']}\n"
            f"Vivió {s['cycle']} ciclos · ganó ${s['total_income']:.6f} · gastó ${s['total_expense']:.6f}"
        )
        self.query_one("#overlay").add_class("show")

    # ------------------------------------------------------------------ #
    def action_toggle_pause(self) -> None:
        self.paused = not self.paused
        self._refresh()

    def action_new_life(self) -> None:
        import os

        # reset the ledger and start fresh
        if os.path.exists(self.agent.ledger_path):
            os.remove(self.agent.ledger_path)
        self.agent = RealAgent(load_real_config())
        self.query_one("#activity-log", Log).clear()
        self.query_one("#overlay").remove_class("show")
        if self._timer:
            self._timer.stop()
        self._timer = self.set_interval(CYCLE_SECONDS, self._on_cycle)
        self.paused = False
        self._refresh()
