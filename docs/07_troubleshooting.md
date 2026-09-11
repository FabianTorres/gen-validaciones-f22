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

## 2026-09-09 · a.221 `FALTA_RUT` masivo + caso feliz sin RUT (fix implementado)

**Síntoma:** 7/8 casos de `a.221` con `FALTA_RUT` (`Tipo 2/3/8 + [14D1, M14A]`); ningún RUT tiene ambos atributos (0/133 en catálogo). La rama ROUND (`CALCULO_VERDADERO_ANIDADO_2`) se genera en Fase 2 pero cae por RUT o UNSAT según semilla → QA sin cobertura usable del ROUND.

**Causa:** doble arbitrariedad del modelo único de Z3-Optimize: (1) fija `TIPO`/atributos en valores que pueden no existir en catálogo aunque el path admita otro modelo compatible; (2) los pesos soft hacen que el óptimo prefiera `M14A=True` aunque `M14A=False` también sea SAT. El lookup post-hoc falla aunque exista solución (probado: mismo path `a.221.7` admite `M14A=False` + RUT `1.439.068-5`).

**Fix:** reintento acotado solo en escenarios `ERROR_RUT`, en `src/generador/strategies/base_strategy.py` (`_reparar_rut_con_catalogo`, + kwargs `_modelo_override/_rut_override/_permitir_repair` en `_resolver_y_formatear`). Fase 1: negar cada atributo requerido (lo forzado por el path da UNSAT y se salta). Fase 2: iterar ≤12 perfiles distintos del catálogo (orden determinista, universales primero). Primer (SAT + match) reconstruye el caso `ENRIQUECIDO`; si no, se conserva el `FALTA_RUT`. Los casos que pasaban no se tocan.

**Verificación:** test focalizado con el método real sobre path `a.221.7`+boundary → `rut=17.858.818-4` (Tipo 2 con `14D1` sin `M14A`), `ENRIQUECIDO`. Matriz completa antes/después pendiente de QA vía API.

**Ajuste 2026-09-09 (lentitud):** el repair agregaba hasta ~14 `check` por escenario fallido (cada uno con timeout 15s). Se acotó: (1) gate por familia feliz — repair solo si `tipo_escenario` empieza con `CALCULO_VERDADERO`, `CALCULO_LINEAL_EXACTO`, `LIMITE_EXACTO` o `CUMPLE_CONDICION` (`_TIPOS_REPAIR_ELEGIBLES`); el resto conserva el `FALTA_RUT` sin costo extra. (2) Tope de perfiles `_MAX_PERFILES_REPAIR` 12 → 6. Gate verificado 9/9 + repair intacto en re-test.

---

## 2026-09-09 · a.221 validado en producción con repair (mínimo QA cumplido)

**Contexto:** matriz real `a.221` (semilla 546782), 10 casos: 3 buenos, 7 `FALTA_RUT`.

**Lo que funcionó:**
- `a.221.3` (`CALCULO_VERDADERO_PRINCIPAL`): reparado → RUT `61.968.400-1` (Tipo 5, `[14D1, 201B]`), `ENRIQUECIDO`. Rama principal con RUT válido.
- `a.221.9` (`CALCULO_VERDADERO_ANIDADO_4_2`, rama ROUND `IF_2=TRUE`): reparado → RUT `1.439.068-5` (Tipo 1, `[14D1, PSEI]`), objetivo **546782** = ROUND(4374252 × 0.125). **Caso feliz `[1512] > 0` con RUT válido: mínimo QA cumplido.**
- `a.221.6` (RUT `M14A`, `SINO 0`, objetivo 0): inútil para validar 14D1 (la regla ni aplica, `CONDICION_1=FALSE`), pero es comportamiento **preexistente**, no causado por el repair.

**FALTA_RUT restantes:** todos de familias no felices (`POS_*`, `FALSO_*`), fuera del repair por el gate a propósito, y varios con combinación genuinamente imposible (`14D1+M14A`, 0/133 RUTs en catálogo) → diagnóstico correcto, no bug.

**Inconsistencia de negocio (a reportar):** la validación exige en la práctica un contribuyente `14D1` que además satisfaga dependencias `M14A` (`b.88`/`b.83`); esa combinación no existe en la realidad ni en el catálogo.

**Nota hacia futuro (importante):** `a.221.9` demuestra que `[1512]` **sí es generable** con valor concreto (546782) y RUT 14D1 válido. Si otra validación usa `[1512]` directa o como dependencia y falla, no asumir falta de datos: revisar la identidad exigida por el path (ver entrada anterior y `test` de `M14A=False`).

---

## 2026-09-09 · Espacios dentro de corchetes `[ 491]` crean código fantasma (resuelto)

**Síntoma:** validación tipo `[850] = [861] + [ 862]` (verificado con `a.7`: `[703] = [492] + [ 491]`) fallaba en generación de casos aunque el código existe en el catálogo.

**Causa:** la gramática acepta `[ 862]` como `CODIGO` (`parser.py:91`) y el formateador lo muestra normalizado (`[862]`), pero el token crudo con espacio llegaba a Fase 2, donde `evaluator.py:39` creaba la variable fantasma `[ 862]` (distinta de `[862]`), `z3_core.py:36` la dejaba sin restricción de signo (`" 862".isdigit()` es False), `test_builder.py:154` la saltaba en el scan de dependencias y `base_strategy.py:240` fallaba su lookup al catálogo.

**Fix:** (1) canonicalización en la sanitización previa al parse (`formatter.py`): `[\s*(\d+)\s*] → [\1]` y lo mismo para alfabéticos; un choke point la elimina para todos los consumers. (2) `.strip()` agregado en los 3 puntos sin normalizar (`test_builder.py:154`, `z3_core.py:36`, `base_strategy.py:240`). No se tocó `main.py` (paso 3 descartado por el usuario).

**Verificación:** regresión `a.7` 4/4: Fase 1 `EXITO` con texto `[703] = [492] + [491]`, AST sin `CODIGO` con espacios, variables Z3 `['[491]','[492]','[703]']` sin fantasmas, y sin `491` en catálogo → fail-fast `CODIGO_NO_CATALOGADO` (ese camino ya funcionaba por API).

---

## Plantilla para el próximo incidente

```md
## AAAA-MM-DD · <id_validacion> <síntoma corto> (estado)
**Síntoma:** ...
**Causa:** ... (`archivo.py:línea`)
**Fix:** ...
**Verificación:** ...
```
