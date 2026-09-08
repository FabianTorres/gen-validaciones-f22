# Sesión actual (handoff entre sesiones)

> Actualizar al cerrar cada sesión: qué se hizo, qué queda, cola QA.

## Estado al 2026-09-08
- Proyecto funcional; en fase de estabilización con analista QA.
- Resueltos hoy (ver `docs/07_troubleshooting.md`):
  1. `b.82` `FALTA_RUT` (Tipo 8 + 14D1) → fix en `src/generador/providers/rut_provider.py` (normalización `str`/`int` + atributos). Usuario tenía commit de respaldo previo.
  2. `b.82` `Falta el AST [1440]` → causa operativa: `cargar-asts` ejecutado con `at=2016` en vez de `2026`; recargado con AT correcto.
- Archivos de contexto creados: `AGENTS.md`, `docs/07_troubleshooting.md`, este archivo.
- `debug_rut_b82.py` (script temporal de repro) fue eliminado; el único cambio en código es `rut_provider.py`.

## Cola QA (pendiente del analista)
- A la espera de nuevos errores. Al llegar uno nuevo:
  1. Agregar entrada en `docs/07_troubleshooting.md` (plantilla al final).
  2. Actualizar esta sección (resuelto/pendiente).

## Notas para la próxima sesión
- Orden de lectura: `AGENTS.md` → este archivo → `docs/07_troubleshooting.md`.
- Ante `Falta el AST [X]`: verificar primero `cargar-asts` con el AT correcto antes de tocar código.
- Ante `FALTA_RUT`/`SIN_RUT_VALIDO`: revisar tipos `str` vs `int` en el doc del RUT en Cosmos (`tipo_contribuyente`, `subtipo`).
- No commitear scripts `debug_*` temporales.
