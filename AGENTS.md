# AGENTS.md — Primer de contexto (leer primero en cada sesión)

## Qué es
Motor que genera casos de prueba para las validaciones del Formulario 22 (F22, Chile).
Flujo: `Excel SII (algoritmo crudo) → Frontend (pegar) → API → Cosmos DB → JSON/CSV → Bot Selenium → digita en portal SII → assert vs `resultado_esperado``.

## Pipeline (detalle en `docs/`)
1. **Fase 1 Normalizador** (`src/normalizador/`, `docs/01_arquitectura_fase1.md`): sanitiza texto Excel → parser Lark → AST + `texto_formateado`. Tipos C,D,E exigen `SINO` (fail-fast); M,N no.
2. **Fase 2 Generador Z3** (`src/generador/`, `docs/02_reglas_negocio_f22.md`, `docs/04_core_matematico_z3.md`): AST → Z3-SMT (dominio Real) → matriz de casos. Estrategias por tipo en `strategies/` dirigidas por `test_builder.py`. Técnicas en `docs/03_estrategia_qa_selenium.md`, contrato JSON en `docs/05_diccionario_salida_json.md`.
3. **Fase 3 Optimizador** (`src/optimizador/`, `docs/ADR_01_optimizacion_bva_mcdc.md`): Set Cover con llave `(ID, Resultado, Huella)`; elimina tríadas BVA redundantes a propósito.
4. **Fase 4 Enriquecedor** (`src/enriquecedor/`, `docs/06_arquitectura_fase4_enriquecedor.md`): backward chaining; resuelve autocalculados (no digitables) a hojas digitables vía BFS sobre ASTs en RAM, modo inverso Z3.

## Invariantes críticos (causan el 90% de los errores QA)
- **RAM por Año Tributario (AT).** `CatalogoCache` (`src/db/cosmos_client.py`) guarda todo como `{AT: {...}}`. El `lifespan` (`src/api/main_api.py`) solo carga `Catalogos`, **NO los ASTs**.
- **Los ASTs se cargan manual:** `POST /api/v1/reglas/memoria/cargar-asts {"at": <AT>}` antes de generar. Tras cada reinicio la RAM queda vacía → error `Falta el arbol AST para el código [X]`.
- **AT correcto siempre.** Frontend, catálogos, ASTs y consultas deben usar el mismo AT (ej. 2026). Un `cargar-asts` con AT equivocado deja todo fallando.
- **Dependencias autocalculadas:** si `cache_codigos[X].autocalculado=True`, `test_builder.py:_resolver_dependencias_autocalculados` exige su AST en RAM o aborta con 400 **antes** de Z3/estrategias/RUTs.
- **`tipo_contribuyente`/`subtipo` son `Union[int,str]`** (`src/api/schemas.py:44-45`). Z3 siempre pide `int` (`base_strategy.py:92,97`). `rut_provider.py` normaliza ambos lados; no reintroducir comparación estricta.
- **Doble candado de exportación** (`base_strategy.py`): a `inputs` solo llega `[NNN]` con dígito o `Vx...`. Variables `E/ALFA/IS_ATRIBUTO_*` nunca salen. Checkboxes como `1/0`.
- **RUTs deterministas:** `RutProvider` devuelve el primer match priorizando `es_formulario_universal`. Mismo requisito → mismo RUT (permite dedup).
- **`perfil_rut_requerido` solo en `n.*`/`m.*`** (`base_strategy.py:399`). En `b.*` es `null` por diseño, no es bug.
- **Settings:** `src/config/settings.py` (`USAR_DECIMALES=False`, `SEMILLA_GENERACION=1000000`).

## Orden de lectura para una sesión nueva
1. Este archivo. 2. `docs/SESION_ACTUAL.md` (estado y cola QA). 3. `docs/07_troubleshooting.md` (incidentes ya resueltos). 4. Profundizar solo si hace falta: `docs/01..06` + `ADR_01`.

## Comandos útiles
- API local: `uvicorn src.api.main_api:app --reload` (verifica puerto/host del proyecto).
- Flujo real: `POST /api/v1/generar-casos` → `POST /api/v1/reglas/guardar` → `GET /api/v1/reglas/historial?at=` → exportar CSV.
- Diagnóstico rápido: `GET /api/v1/reglas/dependencias/{codigo}?at=` (¿existe el AST en Cosmos?), `GET /api/v1/catalogos/codigo?at=` (flag `autocalculado`).
- Batch legacy: `main.py` (`data/input_excel.txt` → `output_*.txt/json` → `casos_selenium.csv`).
