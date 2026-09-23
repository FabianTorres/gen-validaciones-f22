# Sesión actual (handoff entre sesiones)

> Actualizar al cerrar cada sesión: qué se hizo, qué queda, cola QA.

## Nota 2026-09-23
- `a.222.6` `FALTA_RUT` (exige `14D1`+`M14A`) analizado: no hay RUT con ambos, pero sí Tipo 2 + `14D1`; el `M14A` es espurio (viene de `[1111]`/`b.88` por ramas muertas de `[1512]`/`a.221` y decisión arbitraria de Z3). **Inconsistencia de la documentación del SII → no se modifica código.** Detalle en `docs/07_troubleshooting.md`.

## Estado al 2026-09-22
- **Resuelto `a.220` (parámetros inventados en dependencias).** El radar de parámetros de `TestMatrixBuilder` usaba `self.asts_dependencias` (atributo nunca asignado) en vez de la variable local `asts_dep`, así que parámetros usados solo en fórmulas de dependencia (`P647`, `P720`) quedaban como variables libres y Z3 los "inventaba". Fix en `src/generador/test_builder.py:119-128` + guard pasivo en `src/generador/providers/param_provider.py` (`[PARAM GUARD]`, solo log). Detalle en `docs/07_troubleshooting.md`.
- **Verificación:** `a.220` vía API con semilla 546782 → `P647 == 27/100`, `guard=[]`, cadena SAC consistente (`[1109]=6.075.354 → [1111]=1.093.564`). Regresión local sin excepciones en `a.219, b.83, b.88, b.74, a.221, b.82, a.7, b.89`.
- **Pendiente:** regenerar y re-guardar `a.220` (la versión guardada v1 es inválida); validar en portal `AUTO C1305`; QA del resto de la cadena SAC 14A.

## Estado al 2026-09-09
- Proyecto funcional; en fase de estabilización con analista QA.
- Resueltos (ver `docs/07_troubleshooting.md`):
  1. `b.82` `FALTA_RUT` (Tipo 8 + 14D1) → fix en `src/generador/providers/rut_provider.py` (normalización `str`/`int` + atributos). Usuario tenía commit de respaldo previo.
  2. `b.82` `Falta el AST [1440]` → causa operativa: `cargar-asts` ejecutado con `at=2016` en vez de `2026`; recargado con AT correcto.
  3. `a.221` `FALTA_RUT` masivo → repair de RUT (opción B) en `src/generador/strategies/base_strategy.py`, acotado a familias felices + tope 6 perfiles. **Validado en matriz real:** `a.221.3` (principal, RUT `61.968.400-1`) y `a.221.9` (ROUND, RUT `1.439.068-5`, objetivo 546782 > 0). Mínimo QA cumplido.
- Inconsistencia de negocio detectada y a reportar: `14D1+M14A` simultáneos (0/133 RUTs); `[1512]` demostrado generable (caso `a.221.9`) para futuro uso como dependencia.
- Archivos de contexto creados: `AGENTS.md`, `docs/07_troubleshooting.md`, este archivo. Scripts `debug_*` temporales eliminados.

## Cola QA (pendiente del analista)
- Inconsistencia abierta (diagnóstico, sin acción): `IF_1=FALSE + IF_2=TRUE` es SAT colateral (`a.221.1`) pero UNSAT en el escenario dedicado `VERDADERO_ANIDADO_2` con semilla 546872. Se deja así por ahora.
- Vigilar: validaciones que usen `[1512]` como dependencia (es generable, ver nota en troubleshooting).
- Al llegar un error nuevo:
  1. Agregar entrada en `docs/07_troubleshooting.md` (plantilla al final).
  2. Actualizar esta sección (resuelto/pendiente).

## Notas para la próxima sesión
- Orden de lectura: `AGENTS.md` → este archivo → `docs/07_troubleshooting.md`.
- Ante `Falta el AST [X]`: verificar primero `cargar-asts` con el AT correcto antes de tocar código.
- Ante `FALTA_RUT`/`SIN_RUT_VALIDO`: revisar tipos `str` vs `int` en el doc del RUT en Cosmos (`tipo_contribuyente`, `subtipo`).
- No commitear scripts `debug_*` temporales.
