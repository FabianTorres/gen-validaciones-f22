# Estado del Proyecto: Generador Validaciones F22

**Fase Actual:** Cierre de pruebas exhaustivas de la Fase 1 (Normalizador). La Fase 1 se encuentra consolidada y robustecida. Preparativos iniciales para el inicio de la Fase 2 (Integración con `z3-solver`).

## Detalles de la Fase 1 (Normalizador)
El sistema toma líneas de texto crudo desde `data/input_excel.txt` y aplica un flujo de 4 pasos: Sanitización de Texto, Análisis Sintáctico (Lark), Mutación del AST (Desugaring/Sanitización) y Validación Semántica.

### 1. Capa de Sanitización Inteligente (Pre-procesamiento)
Limpia "fósiles tipográficos" y artefactos visuales del Excel original antes de tocar el Parser:
* **Flechas rotas:** Convierte `Þ` y `⇒` a `=>`.
* **Símbolos de la fuente Symbol:** Convierte `¹` y `≠` a `!=`; `≥` y `³` a `>=`; `≤` y `£` a `<=`.
* **Errores de tipeo lógico:** Corrige comas erróneas como `.y,` a `.y.` y dobles comillas de Excel `""x""` a `"x"`.
* **Líneas decorativas:** Elimina divisores visuales (múltiples guiones bajos `___`).

### 2. Reglas Léxicas Soportadas (Tokens)
* **Textos Seguros:** Soporta combinaciones (ej. `M14A`) usando *Negative Lookahead* para no secuestrar palabras clave lógicas. Intercepta conjunciones de lenguaje natural (`o` y `y` aisladas) convirtiéndolas a operadores estrictos `.O.` y `.Y.`.
* **Variables y Códigos:** Estandariza variables entre corchetes (`[ m ]` -> `M`) y códigos F22 numéricos (`[123]`).
* **Operadores Lógicos y Relacionales:** `.y.`, `.o.`, `>=`, `<=`, `>`, `<`, `=`, `!=`. 

### 3. Fases Intermedias del Árbol (AST Mutation)
Antes de formatear, el árbol en memoria sufre dos intervenciones quirúrgicas vitales para la Fase 2:
* **Desenrollado Lógico (Desugaring):** Traduce azúcar sintáctico de bases de datos (`TIPO = 1, 2, 3`) a compuertas booleanas puras (`TIPO = 1 .O. TIPO = 2 .O. TIPO = 3`), cuidando la precedencia con paréntesis.
* **Sanitización de Nulos:** Busca el token solitario `B` en contextos de comparación y lo muta desde la raíz del árbol a la cadena explícita `"BLANCO"`, evitando que Z3 lo interprete como una variable matemática no inicializada.

### 4. Manejo de Errores y Análisis Semántico (Fail-Fast)
El sistema no adivina ni autocompleta, delegando la corrección al humano mediante mensajes estructurados (JSON):
* **Unexpected Characters/Tokens:** Errores de sintaxis y caracteres inválidos capturados por Lark.
* **Validación Semántica de Condicionales:** El motor diferencia la intención del condicional analizando el árbol. Si detecta un "Cálculo" (Tipos C, D, E) sin su rama `SINO`, lanza un `ValueError` personalizado (`SINO_FALTANTE`). Si detecta una "Acción" (Tipos M, N), permite el paso sin el `SINO`.

## Siguientes Pasos
1. **Transición a Fase 2:** Con el AST purificado, iniciar el diseño de la inyección de nodos hacia `z3-solver`.
2. **Definición de Inferencia de Tipos:** Establecer el motor dinámico para resolver el choque de tipos en los `SINO 0`.