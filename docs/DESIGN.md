# VITAL — Diseño

## El concepto

VITAL es un agente que **sabe cuánto le queda de vida**. Su saldo de créditos
es literalmente su esperanza de vida: `runway = créditos / burn`. Cada decisión
parte de ese número.

## El bucle de un tick

```
1. El mercado se mueve (paseo aleatorio por categoría) + inflación del burn
2. El cerebro decide: WORK | REST | BUY | WAIT
3. Se ejecuta la decisión
4. Se cobra el ingreso pasivo
5. Se paga el coste de vida (burn)
6. Se regenera energía pasiva
7. El ánimo deriva hacia neutro
8. Puede dispararse un evento del mundo
9. Contabilidad + historial
10. Comprobación de muerte / victoria
```

## El cerebro (política de utilidad)

Una máquina de prioridades simple y legible:

```
SI runway < 12        → trabajo rápido de emergencia (o descanso si no hay energía)
SI energía < 25       → descansar
SI runway ≥ 30 y hay colchón → invertir en mejora (prioridad: pasivos)
SI hay tarea rentable → trabajar
SI no                 → descansar
```

La elección de tarea puntúa `recompensa/duración` ajustada por riesgo y
multiplicador de mercado, y respeta los requisitos de habilidad.

## Por qué la inflación

Sin inflación, un agente competente se estanca en un equilibrio aburrido:
gana lo justo para vivir y nunca muere ni gana de verdad. La inflación
(`burn ×2 cada 300 ticks`) convierte la quietud en muerte y obliga al agente a
**crecer o morir**, que es la promesa del proyecto.

## Muerte y victoria

- Muerte: `créditos ≤ 0` → `alive=False`, se registra la causa.
- Victoria por fortuna: `créditos ≥ target_credits`.
- Victoria por libertad: `ingreso pasivo ≥ burn × passive_freedom_ratio`.

Al terminar, el motor deja de avanzar (los ticks son no-op).

## Persistencia

El estado completo (`config`, `agent`, `world`) se serializa a JSON con
escritura atómica (`tmp` + `os.replace`). La TUI autoguarda cada 5 ticks y al
desmontar; `vital status` y `vital reset` operan sobre ese archivo.

## La TUI

Construida con **Textual** siguiendo la estética de Cursor AI:

- Tema oscuro `#0d1117` / paneles `#161b22` / bordes `#30363d`.
- Acento púrpura `#a371f7` (Cursor), verde/rojo/amarillo para estado.
- Barra lateral de "vitales" con tarjetas redondeadas.
- Pestañas: Panel (log), Trabajos, Tienda, Mundo.
- Sparkline del historial de créditos.
- Modal centrado para muerte (rojo) y victoria (verde).
