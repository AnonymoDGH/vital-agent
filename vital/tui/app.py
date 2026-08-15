"""VITAL TUI — a Cursor-AI inspired terminal interface.

Layout:
    ┌──────────────────────────────────────────────────────────┐
    │ ◆ VITAL  ·  autonomous life-credit agent        [status] │  topbar
    ├────────────┬─────────────────────────────────────────────┤
    │  sidebar   │  tabs: Panel | Trabajos | Tienda | Mundo    │
    │  (vitals)  │                                             │
    │            │  ...content...                              │
    ├────────────┴─────────────────────────────────────────────┤
    │  task progress bar                                       │
    │  statusbar                                               │
    └──────────────────────────────────────────────────────────┘
"""

from __future__ import annotations

from pathlib import Path

from textual import work
from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical, VerticalScroll
from textual.reactive import reactive
from textual.timer import Timer
from textual.widgets import (
    Button,
    DataTable,
    Footer,
    Label,
    Log,
    ProgressBar,
    Sparkline,
    Static,
    TabbedContent,
    TabPane,
)

from vital.core import persistence
from vital.core.brain import Action
from vital.core.economy import SHOP_ORDER, TASKS, UPGRADES
from vital.core.engine import Engine, TickReport
from vital.core.formatting import (
    fmt_credits,
    fmt_ticks,
    life_bar_color,
    mood_face,
    status_word,
)
from vital.core.state import GameConfig

TICK_SECONDS = 0.8
CSS_PATH = Path(__file__).parent / "app.tcss"


class VitalApp(App):
    """The VITAL terminal application."""

    CSS_PATH = "app.tcss"
    TITLE = "VITAL"
    SUB_TITLE = "gana dinero o muere"

    BINDINGS = [
        ("q", "quit", "Salir"),
        ("space", "toggle_pause", "Pausa"),
        ("s", "save_now", "Guardar"),
        ("n", "new_life", "Nueva vida"),
        ("1", "tab_panel", "Panel"),
        ("2", "tab_jobs", "Trabajos"),
        ("3", "tab_shop", "Tienda"),
        ("4", "tab_world", "Mundo"),
    ]

    paused = reactive(False)
    tick_count = reactive(0)

    LAYERS = ["base", "overlay"]

    def __init__(self, engine: Engine | None = None):
        super().__init__()
        self.engine = engine or persistence.load_engine() or Engine(GameConfig())
        self._timer: Timer | None = None
        self._last_log_total = 0  # world.log_total already shown in the Log widget

    # ------------------------------------------------------------------ #
    # Composition
    # ------------------------------------------------------------------ #
    def compose(self) -> ComposeResult:
        agent = self.engine.agent

        with Container(id="topbar"):
            yield Label(
                "[b][#a371f7]◆[/] VITAL[/]  [#8b949e]· agente autónomo de créditos vitales[/]",
                classes="title",
            )
            yield Label("", id="topbar-status", classes="subtitle")

        with Horizontal(id="body"):
            # ---- sidebar ----
            with Vertical(id="sidebar"):
                with Container(classes="card"):
                    yield Label("CRÉDITOS VITALES", classes="card-title")
                    yield Label("", id="credits-big", classes="big-number")
                    yield Label("", id="credits-sub", classes="subtle")
                with Container(classes="card"):
                    yield Label("ESPERANZA DE VIDA", classes="card-title")
                    yield Label("", id="runway-big", classes="big-number")
                    yield Label("", id="runway-sub", classes="subtle")
                with Container(classes="card"):
                    yield Label("ENERGÍA", classes="card-title")
                    yield ProgressBar(id="energy-bar", total=100, show_eta=False)
                    yield Label("", id="energy-label", classes="subtle")
                with Container(classes="card"):
                    yield Label("ECONOMÍA", classes="card-title")
                    yield Label("", id="eco-income", classes="subtle")
                    yield Label("", id="eco-burn", classes="subtle")
                    yield Label("", id="eco-net", classes="subtle")
                with Container(classes="card"):
                    yield Label("AGENTE", classes="card-title")
                    yield Label("", id="agent-skill", classes="subtle")
                    yield Label("", id="agent-mood", classes="subtle")
                    yield Label("", id="agent-tasks", classes="subtle")
                with Container(classes="card"):
                    yield Label("HISTORIA", classes="card-title")
                    yield Sparkline(id="credit-spark", min_color="#30363d", max_color="#a371f7")

            # ---- main ----
            with Vertical(id="main"):
                with TabbedContent(initial="panel"):
                    with TabPane("◈ Panel", id="panel"):
                        yield Label("[b]Actividad del agente[/]", classes="card-title")
                        yield Log(id="activity-log", highlight=True)
                    with TabPane("⚡ Trabajos", id="jobs"):
                        yield DataTable(id="jobs-table")
                    with TabPane("🛒 Tienda", id="shop"):
                        yield DataTable(id="shop-table")
                        with Horizontal(id="shop-buttons"):
                            yield Button("Comprar seleccionado", id="btn-buy", variant="primary")
                    with TabPane("🌐 Mundo", id="world"):
                        yield DataTable(id="market-table")

                with Container(id="task-panel"):
                    yield Label("", id="task-label", classes="subtle")
                    yield ProgressBar(id="task-bar", total=1, show_eta=False)

        yield Static("", id="statusbar")
        yield Footer()

        # centered modal overlay (hidden until death / victory)
        with Container(id="overlay"):
            with Vertical(id="overlay-box"):
                yield Label("", id="overlay-title", classes="headline")
                yield Label("", id="overlay-body")
                yield Label(
                    "[#8b949e]Pulsa [b]n[/b] para una nueva vida · [b]q[/b] para salir[/]",
                    id="overlay-hint",
                )

    # ------------------------------------------------------------------ #
    # Lifecycle
    # ------------------------------------------------------------------ #
    def on_mount(self) -> None:
        self._build_tables()
        self._refresh_all()
        self._log_history()
        # If we resumed a game that already ended, surface the overlay.
        agent = self.engine.agent
        if not agent.alive:
            self._show_overlay(died=True)
        elif agent.retired:
            self._show_overlay(died=False)
        self._timer = self.set_interval(TICK_SECONDS, self._on_tick)
        self.query_one("#activity-log", Log).focus()

    def _build_tables(self) -> None:
        jobs = self.query_one("#jobs-table", DataTable)
        jobs.cursor_type = "row"
        jobs.add_columns("Trabajo", "Duración", "Pago base", "Energía", "Riesgo", "Requisito")
        for tid, t in TASKS.items():
            req = f"hab {t.skill_gate}" if t.skill_gate > 0 else "—"
            jobs.add_row(
                f"{t.icon} {t.name}",
                f"{t.duration}t",
                f"{t.base_reward:.0f}₵",
                f"{t.energy_cost:.0f}",
                f"{int(t.risk * 100)}%",
                req,
                key=tid,
            )

        shop = self.query_one("#shop-table", DataTable)
        shop.cursor_type = "row"
        shop.add_columns("Mejora", "Coste", "Efecto", "Estado")
        for uid in SHOP_ORDER:
            u = UPGRADES[uid]
            shop.add_row(f"{u.icon} {u.name}", f"{u.cost:.0f}₵", u.blurb, "", key=uid)

        market = self.query_one("#market-table", DataTable)
        market.add_columns("Categoría", "Multiplicador", "Tendencia")

    # ------------------------------------------------------------------ #
    # Tick loop
    # ------------------------------------------------------------------ #
    def _on_tick(self) -> None:
        if self.paused:
            return
        agent = self.engine.agent
        if not agent.alive or agent.retired:
            return
        rep = self.engine.tick()
        self.tick_count += 1
        self._apply_report(rep)
        self._refresh_all()
        if self.tick_count % 5 == 0:
            self._autosave()

    def _apply_report(self, rep: TickReport) -> None:
        log = self.query_one("#activity-log", Log)
        # Append only the world-log lines we have not shown yet. Using the
        # monotonic log_total (instead of len(log)) keeps working even after
        # the engine truncates its in-memory log to the cap.
        world = self.engine.world
        new_lines = world.log_total - self._last_log_total
        if new_lines > 0:
            for line in world.log[-new_lines:]:
                log.write_line(line)
            self._last_log_total = world.log_total
        for msg in rep.messages:
            log.write_line(msg)

        if rep.died:
            self._show_overlay(died=True)
        elif rep.won:
            self._show_overlay(died=False)

    # ------------------------------------------------------------------ #
    # Refresh UI from engine state
    # ------------------------------------------------------------------ #
    def _refresh_all(self) -> None:
        agent = self.engine.agent
        world = self.engine.world

        color = life_bar_color(agent)
        self.query_one("#credits-big", Label).update(
            f"[b][{color}]{fmt_credits(agent.credits)}[/][/] [{color}]{mood_face(agent)}[/]"
        )
        self.query_one("#credits-sub", Label).update(
            f"ganado {fmt_credits(agent.total_earned)} · gastado {fmt_credits(agent.total_spent)}"
        )

        runway = agent.runway
        self.query_one("#runway-big", Label).update(
            f"[b][{color}]{fmt_ticks(runway)}[/][/]"
        )
        net = agent.net_per_tick
        net_txt = f"[#3fb950]+{net:.2f}₵/t[/]" if net >= 0 else f"[#f85149]{net:.2f}₵/t[/]"
        self.query_one("#runway-sub", Label).update(f"neto {net_txt}")

        self.query_one("#energy-bar", ProgressBar).update(progress=agent.energy)
        self.query_one("#energy-label", Label).update(f"{agent.energy:.0f} / 100")

        self.query_one("#eco-income", Label).update(
            f"[#3fb950]▲ pasivo +{agent.passive_income:.2f}₵/t[/]"
        )
        self.query_one("#eco-burn", Label).update(
            f"[#f85149]▼ coste -{agent.burn:.2f}₵/t[/]"
        )
        self.query_one("#eco-net", Label).update(
            f"[{color}]balance {net:+.2f}₵/t[/]"
        )

        self.query_one("#agent-skill", Label).update(f"🧠 habilidad {agent.skill:.2f}")
        self.query_one("#agent-mood", Label).update(f"{mood_face(agent)} ánimo {agent.mood:.2f}")
        self.query_one("#agent-tasks", Label).update(
            f"✅ {agent.tasks_done} · ⚠️ {agent.tasks_failed}"
        )

        spark = self.query_one("#credit-spark", Sparkline)
        spark.data = world.history_credits[-60:] or [0.0]

        # topbar + statusbar
        status = status_word(agent)
        status_color = {
            "MUERTO": "#f85149",
            "LIBRE": "#3fb950",
            "CRÍTICO": "#f85149",
            "EN RIESGO": "#d29922",
            "TRABAJANDO": "#58a6ff",
            "ESTABLE": "#3fb950",
        }.get(status, "#8b949e")
        self.query_one("#topbar-status", Label).update(
            f"[{status_color}]● {status}[/]  ·  tick {world.tick}"
        )
        pause_txt = " [#d29922]⏸ PAUSA[/]" if self.paused else ""
        self.query_one("#statusbar", Static).update(
            f"[#8b949e]◆ VITAL[/] · {agent.name} · edad {agent.age}t · "
            f"mejoras {len(agent.upgrades)}{pause_txt}   "
            f"[#8b949e][space] pausa · [s] guardar · [n] nueva vida · [q] salir[/]"
        )

        # task panel (guard against a stale/unknown task id)
        task = TASKS.get(agent.active_task) if agent.active_task else None
        if task is not None:
            self.query_one("#task-label", Label).update(
                f"{task.icon} {task.name} — progreso {agent.task_progress}/{task.duration}"
            )
            self.query_one("#task-bar", ProgressBar).update(
                total=float(task.duration), progress=float(agent.task_progress)
            )
        else:
            self.query_one("#task-label", Label).update("Sin tarea activa")
            self.query_one("#task-bar", ProgressBar).update(total=1.0, progress=0.0)

        # shop status column
        shop = self.query_one("#shop-table", DataTable)
        for row_key in list(shop.rows.keys()):
            uid = str(row_key.value)
            owned = "✔ poseída" if uid in agent.upgrades else ""
            try:
                shop.update_cell(row_key, 3, owned)
            except Exception:
                pass

        # market table
        market = self.query_one("#market-table", DataTable)
        market.clear()
        for cat, mult in sorted(world.market.items()):
            trend = "📈" if mult > 1.05 else ("📉" if mult < 0.95 else "➖")
            market.add_row(cat, f"x{mult:.2f}", trend)

    def _log_history(self) -> None:
        log = self.query_one("#activity-log", Log)
        for line in self.engine.world.log[-80:]:
            log.write_line(line)
        # We have now displayed everything up to the current monotonic total.
        self._last_log_total = self.engine.world.log_total

    # ------------------------------------------------------------------ #
    # Overlay (death / victory)
    # ------------------------------------------------------------------ #
    def _show_overlay(self, died: bool) -> None:
        if self._timer:
            self._timer.stop()
        agent = self.engine.agent
        if died:
            title = "[b][#f85149]💀  VITAL HA MUERTO[/][/]"
            body = (
                f"Causa: {agent.death_cause}\n"
                f"Vivió {agent.age} ticks · ganó {fmt_credits(agent.total_earned)}\n"
                f"Completó {agent.tasks_done} tareas · {len(agent.upgrades)} mejoras"
            )
            box_cls = "dead"
        else:
            title = "[b][#3fb950]🏆  ¡LIBERTAD FINANCIERA![/][/]"
            body = (
                f"VITAL es libre tras {agent.age} ticks.\n"
                f"Fortuna final: {fmt_credits(agent.credits)}\n"
                f"Ingresos pasivos: {agent.passive_income:.1f}₵/t"
            )
            box_cls = "won"

        overlay = self.query_one("#overlay")
        box = self.query_one("#overlay-box")
        box.remove_class("dead", "won")
        box.add_class(box_cls)
        self.query_one("#overlay-title", Label).update(title)
        self.query_one("#overlay-body", Label).update(body)
        overlay.add_class("show")

        # also echo into the activity log
        log = self.query_one("#activity-log", Log)
        log.write_line("")
        log.write_line(title)
        for line in body.splitlines():
            log.write_line(line)

    def _hide_overlay(self) -> None:
        self.query_one("#overlay").remove_class("show")

    # ------------------------------------------------------------------ #
    # Actions
    # ------------------------------------------------------------------ #
    def action_toggle_pause(self) -> None:
        self.paused = not self.paused
        self._refresh_all()

    def action_save_now(self) -> None:
        path = persistence.save_engine(self.engine)
        self.notify(f"Guardado en {path}", title="VITAL")

    def action_new_life(self) -> None:
        persistence.clear_save()
        self.engine = Engine(GameConfig())
        self._last_log_total = 0
        self.query_one("#activity-log", Log).clear()
        self._hide_overlay()
        if self._timer:
            self._timer.stop()
        self._timer = self.set_interval(TICK_SECONDS, self._on_tick)
        self.paused = False
        self._refresh_all()
        self.notify("Nueva vida iniciada", title="VITAL")

    def action_tab_panel(self) -> None:
        self.query_one(TabbedContent).active = "panel"

    def action_tab_jobs(self) -> None:
        self.query_one(TabbedContent).active = "jobs"

    def action_tab_shop(self) -> None:
        self.query_one(TabbedContent).active = "shop"

    def action_tab_world(self) -> None:
        self.query_one(TabbedContent).active = "world"

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-buy":
            shop = self.query_one("#shop-table", DataTable)
            keys = list(shop.rows.keys())
            if shop.cursor_row is not None and shop.cursor_row < len(keys):
                uid = str(keys[shop.cursor_row].value)
                self._try_buy(uid)

    def _try_buy(self, uid: str) -> None:
        agent = self.engine.agent
        u = UPGRADES.get(uid)
        if not u:
            return
        if uid in agent.upgrades:
            self.notify("Ya posees esa mejora", severity="warning")
            return
        if agent.credits < u.cost:
            self.notify("Créditos insuficientes", severity="error")
            return
        agent.credits -= u.cost
        agent.total_spent += u.cost
        agent.upgrades.append(uid)
        if u.kind == "skill":
            agent.skill += u.power
        self.engine._apply_upgrades()
        self.notify(f"Comprado: {u.name}", title="🛒 Tienda")
        self._refresh_all()

    def _autosave(self) -> None:
        try:
            persistence.save_engine(self.engine)
        except OSError:
            pass

    def on_unmount(self) -> None:
        try:
            persistence.save_engine(self.engine)
        except OSError:
            pass
