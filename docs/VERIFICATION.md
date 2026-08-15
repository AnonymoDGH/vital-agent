# VITAL — Informe de verificación manual

Todo lo siguiente se ejecutó y comprobó a mano (no solo se escribió).

## 1. Entorno
- Python 3.14.3, pip 26.1.2, git 2.49.0, Node v22.22.1 presentes.
- `textual 8.2.7`, `rich`, `pytest 9.1.0` disponibles.
- Se verificó la API de Textual 8 (widgets, `run_test`, `export_screenshot`,
  `Sparkline.data`, `ProgressBar.update`, `DataTable.add_row/add_columns`,
  `Log.write_line`, `App.notify`) antes de escribir el código.

## 2. Instalación
- `pip install -e .` → instala `vital-agent 0.1.0` y el comando `vital`. ✅

## 3. Tests unitarios
- `pytest` → **30 tests pasan** (motor, economía, cerebro, persistencia, balance).
- Se corrigió un test que asumía fondos suficientes para una mejora.

## 4. Simulación headless
- `vital headless 120 --seed 7` → resumen correcto.
- Se detectó y arregló un `UnicodeEncodeError` (cp1252) forzando UTF-8 en stdout.
- Camino de muerte verificado: agente ocioso con 10₵ muere en el tick 5.
- Camino de trabajo verificado: completa tareas y gana créditos.

## 5. Balance "gana o muere"
- Se midió la distribución sobre 40 semillas (1500 ticks):
  `wins=31 deaths=8 still_alive=1`.
- Se añadió **inflación** porque sin ella el agente nunca moría (40/40 victorias).
- Con inflación 300: muertes reales en ticks ~910–1006, victorias en ~137–792.

## 6. TUI (headless `run_test`)
- Smoke test: la app compone sin errores y exporta SVG. ✅
- Se detectó que las capturas salían en **escala de grises**: la variable de
  entorno `NO_COLOR=1` del sistema añadía un filtro `Monochrome`. Se limpió y se
  forzó `TEXTUAL_COLOR_SYSTEM=truecolor`. ✅
- Verificación de contenido del SVG: títulos de tarjetas, pestañas, log,
  sparkline, footer y colores de acento presentes.

## 7. Capturas PNG
- Se convirtieron los SVG a PNG con **Edge headless** (cairosvg no tenía la DLL).
- `tools/verify_png.py` comprueba tamaño, fondo oscuro, colores de acento y
  densidad de texto → **6 capturas OK** (panel, jobs, shop, world, death, victory).

## 8. Overlays de muerte/victoria
- Se mejoró de "escribir en el log" a un **modal centrado** con borde de color.
- Verificado que se dispara de forma **natural** por el bucle de ticks:
  - muerte (seed 3, tick 392) → modal rojo. ✅
  - victoria (seed 10, tick 137) → modal verde. ✅

## 9. CLI
- `vital --help`, `vital status`, `vital reset`, `vital headless` → todos OK.
- `vital status` sin partida → mensaje correcto.
- `vital reset` borra el guardado. ✅

## 10. Persistencia
- Autoguardado cada 5 ticks + al desmontar → `save.json` creado. ✅
- `vital status` lee el guardado. ✅
- La TUI **reanuda** desde la partida guardada al arrancar. ✅
- Round-trip save/load probado en tests. ✅

## 11. Interacciones (pilot)
- `espacio` pausa/reanuda (los ticks son no-op en pausa). ✅
- Teclas `1`–`4` cambian de pestaña. ✅
- Botón de compra rechaza si no hay créditos y compra si los hay. ✅

## 12. Arranque real
- `python -m vital.cli tui` arranca en un proceso real y sigue vivo 4s sin
  crashear (stderr vacío). ✅
