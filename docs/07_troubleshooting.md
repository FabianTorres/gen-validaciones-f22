# 07. Troubleshooting QA (bitácora de incidentes)

Formato por entrada: síntoma → causa → fix → verificación. Agregar nuevas entradas arriba con fecha.

---

## 2026-09-08 · b.82 `FALTA_RUT` con Tipo 8 + 14D1 (resuelto)

**Síntoma:** caso `b.82.12` devuelve `rut: FALTA_RUT`, `estado_interno: ERROR_RUT`:
`requiere Tipo: 8, Subtipo: Cualquiera, Requeridos: ['14D1']`, aunque `59.494.257-4` (Tipo 8 + 14D1) existe en Cosmos.

**Causa:** mismatch `str` vs `int`. `base_strategy.py:92` pide `tipo_req=int(8)`, pero el doc en Cosmos tenía `tipo_contribuyente="8"` (string) porque `RutItem` acepta `Union[int,str]` (`schemas.py:44-45`) y la migración no normaliza (`migrar_catalogos.py`). `rut_provider.py:36` comparaba estricto: `"8" != 8` → descartaba al único candidato. Mismo riesgo con `subtipo "816"` y atributos en minúsculas/con espacios.

**Fix:** normalización tolerante en `src/generador/providers/rut_provider.py:obtener_rut` (solo ese archivo):
- `tipo/subtipo`: `int(str(v).strip())` cuando es numérico; si no, string `upper().strip()`. `None` se sigue ignorando.
- atributos: `upper().strip()` en ambos lados.
- Se conserva ordenamiento universal-primero y `SIN_RUT_VALIDO` cuando realmente no hay match.

**Verificación:** repro con catálogo mixto → antes `SIN_RUT_VALIDO`, después `59.494.257-4`. Bordes OK: int/str ambas direcciones, subtipo str, attr lower/espacios, prohibidos bloquean, sin-match sigue `SIN_RUT_VALIDO`.

---

## 2026-09-08 · `Falta el arbol AST para el código [1440]` en b.82 (resuelto, causa operativa)

**Síntoma:** `POST /api/v1/generar-casos` (b.82) → `400`, log se queda en `Resolviendo dependencias recursivas...`. Mensaje: `Falta el arbol AST para el código [1440]...`.

**Causa:** RAM de ASTs vacía o cargada con AT equivocado. El `lifespan` solo carga `Catalogos`, nunca ASTs (`main_api.py:68-77`). Se había ejecutado `POST /reglas/memoria/cargar-asts` con `at=2016` en vez de `2026`. El escáner (`test_builder.py:158-168`) ve `codigos[1440].autocalculado=True` pero no encuentra `asts_latest[2026]["[1440]"]` y aborta **antes** de Z3/RUTs. No relacionado con el fix de RUTs (ese código corre mucho después).

**Fix:** `POST /api/v1/reglas/memoria/cargar-asts {"at": 2026}` y reintentar.

**Verificación / diagnóstico rápido:**
1. Log backend: buscar `Memoria AST Masiva lista: N árboles` (ausente o N=0 = RAM vacía).
2. `GET /api/v1/reglas/dependencias/1440?at=2026` → si trae `ast`, el doc existe y era solo RAM; si vacío, falta el doc o está en otro AT/formato de `codigo_objetivo`.
3. `GET /api/v1/catalogos/codigo?at=2026` → confirmar flag `autocalculado` de `1440`.
4. Confirmar que el frontend envía el mismo `at` en `generar-casos`.

---

## Plantilla para el próximo incidente

```md
## AAAA-MM-DD · <id_validacion> <síntoma corto> (estado)
**Síntoma:** ...
**Causa:** ... (`archivo.py:línea`)
**Fix:** ...
**Verificación:** ...
```
