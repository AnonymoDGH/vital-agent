# ◆ VITAL

> **Un agente autónomo que conoce su crédito de vida restante. Debe ganar su propio dinero… o muere.**

VITAL es una simulación de supervivencia económica. El agente nace con una
reserva finita de **créditos vitales** (`₵`). Cada tick que pasa, vivir cuesta
créditos. Si el saldo llega a `0`, **muere**. La única forma de sobrevivir es
trabajar, invertir en ingresos pasivos y alcanzar la **libertad financiera**
antes de que la inflación del coste de la vida lo devore.

```
┌──────────────────────────────────────────────────────────────┐
│ ◆ VITAL · agente autónomo de créditos vitales   ● ESTABLE    │
├──────────────┬───────────────────────────────────────────────┤
│ CRÉDITOS     │  ◈ Panel   ⚡ Trabajos   🛒 Tienda   🌐 Mundo │
│ 274.7₵ 😄    │                                               │
│ ESPERANZA    │  Actividad del agente                         │
│ 2m 46t       │   t40  Trabajo para ganar créditos            │
│ ENERGÍA ▓▓▓  │   t41  ✅ 'Freelance de código' +97.9₵        │
│ ECONOMÍA     │   t42  🛒 Comprado 'Batería de grafeno'       │
│  ▲ +1.50₵/t  │                                               │
│  ▼ -1.60₵/t  │                                               │
└──────────────┴───────────────────────────────────────────────┘
```

---

## 📸 Capturas

| Panel principal | Trabajos |
|---|---|
| ![Panel](assets/screenshots/panel.png) | ![Trabajos](assets/screenshots/jobs.png) |

| Tienda | Mundo |
|---|---|
| ![Tienda](assets/screenshots/shop.png) | ![Mundo](assets/screenshots/world.png) |

| 💀 Muerte | 🏆 Victoria |
|---|---|
| ![Muerte](assets/screenshots/death.png) | ![Victoria](assets/screenshots/victory.png) |

---

## 🎮 Cómo se juega

VITAL decide solo. Tú lo observas (o lo dejas correr en segundo plano). Su
**cerebro** evalúa cada tick:

1. **Si está a punto de morir** → coge el trabajo más rápido disponible.
2. **Si tiene poca energía** → descansa.
3. **Si tiene colchón** → invierte en mejoras de ingresos pasivos.
4. **Si no** → trabaja en la tarea más rentable que su habilidad permita.

### Condiciones de fin

| Resultado | Condición |
|---|---|
| 💀 **Muerte** | `créditos ≤ 0` |
| 🏆 **Victoria** | `créditos ≥ 6 000₵` **o** `ingreso pasivo ≥ 8× coste de vida` |

La **inflación** hace que el coste de vida se duplique cada 300 ticks, así que
quedarse quieto es una sentencia de muerte.

---

## 🚀 Instalación

```bash
git clone <repo> vital-agent
cd vital-agent
pip install -e .          # instala el comando `vital`
```

Requiere **Python ≥ 3.10**. Dependencias: `textual`, `rich`.

## ▶️ Uso

```bash
vital                 # lanza la TUI interactiva
vital tui             # igual que arriba
vital headless 200    # simula 200 ticks sin interfaz y muestra resumen
vital headless 500 --seed 7   # reproducible con semilla
vital status          # estado de la partida guardada
vital reset           # borra la partida guardada
```

### Atajos de teclado (TUI)

| Tecla | Acción |
|---|---|
| `espacio` | Pausar / reanudar |
| `s` | Guardar ahora |
| `n` | Nueva vida |
| `1`–`4` | Cambiar de pestaña |
| `q` | Salir |

La partida se **autoguarda** cada 5 ticks y al cerrar.

---

## 🧠 Arquitectura

```
vital/
├── core/               # motor puro, sin I/O ni TUI (testeable)
│   ├── state.py        # dataclasses: Agent, WorldState, GameConfig, TaskDef, Upgrade
│   ├── economy.py      # catálogo de trabajos, tienda y dinámica de mercado
│   ├── brain.py        # política de decisión basada en utilidad
│   ├── engine.py       # avanza la simulación tick a tick
│   ├── events.py       # eventos aleatorios del mundo
│   ├── persistence.py  # guardar/cargar en JSON
│   └── formatting.py   # helpers de formato compartidos
├── tui/
│   ├── app.py          # aplicación Textual (estilo Cursor-AI)
│   └── app.tcss        # hoja de estilos oscura
└── cli.py              # punto de entrada `vital`
```

El **motor es puro**: solo muta el `Agent`/`WorldState` que recibe y devuelve un
`TickReport`. No hay temporizadores ni I/O dentro — la TUI o el CLI deciden
cuándo ocurre un tick. Esto lo hace determinista con una semilla y trivialmente
testeable.

### Economía

- **6 trabajos**, de micro-tareas rápidas a contratos corporativos, cada uno con
  duración, pago, coste de energía, riesgo y requisito de habilidad.
- **9 mejoras**: bots de ingresos pasivos, reducción de burn, multiplicadores de
  recompensa, batería y cursos de habilidad.
- **Mercado** por categoría con multiplicador que hace un paseo aleatorio
  acotado `[0.6, 1.8]`.
- **10 eventos** aleatorios: propinas, impuestos, agotamiento, booms y caídas de
  mercado, virus, etc.

---

## 🧪 Tests

```bash
pip install -e ".[dev]"
pytest
```

30 tests cubren: invariantes de vida/muerte, trabajo y recompensas, mejoras,
mercado, cerebro, persistencia y —lo más importante— la promesa **"gana o
muere"**: sobre 25 semillas se comprueba que hay **tanto victorias como
muertes** (ni todo fácil ni todo imposible).

---

## ⚖️ Balance

Distribución medida sobre 40 semillas (1500 ticks máx.):

```
wins=33  deaths=7  still_alive=0
win ticks   min/avg/max: 394 / 486 / 609
death ticks min/avg/max: 772 / 785 / 803
```

---

## 📄 Licencia

MIT.
