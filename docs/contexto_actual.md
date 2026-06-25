# Estado del Proyecto: Generador Validaciones F22

**Fase Actual:** Cierre exitoso y consolidación de la Fase 1 (Normalizador). Preparativos iniciales para el inicio de la Fase 2 (Integración con `z3-solver`).

## Detalles de la Fase 1 (Normalizador)
El sistema implementa una **Arquitectura Limpia (Separation of Concerns)** dividiendo el procesamiento en 5 fases estrictas para evitar ambigüedades entre la sintaxis y las reglas de negocio.

### Fase 1: Capa de Sanitización Inteligente (Pre-procesamiento)
Actúa antes del Parser para limpiar la entrada humana del Excel:
* **Fósiles tipográficos:** Convierte flechas (`Þ`, `⇒`) a `=>` y símbolos especiales (`¹`, `≠`, `≥`, `£`) a operadores matemáticos estándar (`!=`, `>=`, `<=`).
* **Tokenización Codiciosa (Greedy Tokenization):** Inyecta "colchones" de espacios (`218. o .` -> `218 .o. `) para evitar que el motor confunda puntos de separación con números decimales flotantes.

### Fase 2: Análisis Sintáctico Universal (Lark)
El Parser lee el texto sin aplicar juicios de negocio. 
* Soporta **Condicionales Recursivos** (`SINO SI...`).
* Soporta **Cotas Encadenadas** continuas (`A <= B <= C`).
* Define un único `condicional` universal donde la rama `SINO` es siempre *sintácticamente* opcional, delegando la rigurosidad a la capa semántica.

### Fase 3: Desenrollado y Mutación del AST (Desugaring)
Intervención quirúrgica del árbol en memoria:
* **Compuertas Booleanas:** Expande asignaciones múltiples (`TIPO = 1, 2, 3`) en compuertas puras (`TIPO = 1 .O. TIPO = 2...`).
* **Sanitización de Nulos:** Muta el token `B` al string explícito `"BLANCO"` para blindar el posterior tipado en Z3.

### Fase 4: Linter Semántico (Juez de Negocios)
Un `Transformer` de Lark que evalúa el contexto de la regla (`id_val`).
* **Validaciones Bloqueantes (Tipos C, D, E):** Exige estrictamente la existencia de una rama `SINO`. Si falta, interrumpe el flujo y levanta un `ValueError` controlado (`SINO_FALTANTE_ESTRICTO`).
* **Validaciones Informativas (Tipos M, N):** Permite el paso de condicionales de "Acción" sin rama `SINO`.

### Fase 5: Formateador Visual (Pretty-Printer)
Toma el AST validado por el Linter y lo reconstruye en un formato estándar, indentado y jerárquico (`SI / ENTONCES / SINO`) listo para el Frontend.

## Siguientes Pasos
1. **Fase 2 (Generador Z3):** Iniciar la inyección de los nodos AST procesados hacia el motor de satisfacibilidad.
2. **Inferencia de Tipos Dinámica:** Implementar el interceptor semántico que transformará el comodín `SINO 0` en `z3.BoolVal(True)` cuando el bloque `ENTONCES` retorne una proposición lógica.