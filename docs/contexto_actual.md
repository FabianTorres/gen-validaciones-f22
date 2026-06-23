# Estado del Proyecto: Generador Validaciones F22

**Fase Actual:** Cierre de pruebas exhaustivas de la Fase 1 (Normalizador). La Fase 1 se encuentra consolidada y robustecida. Preparativos iniciales para el inicio de la Fase 2 (Integración con `z3-solver`).

## Detalles de la Fase 1 (Normalizador)
El sistema toma líneas de texto crudo desde `data/input_excel.txt` y aplica un doble proceso: primero una capa de **Sanitización Inteligente** y luego un análisis y validación estricta utilizando la librería `lark` (v1.3.1).

### 1. Capa de Sanitización Inteligente (Pre-procesamiento)
Antes de que el motor lea la fórmula, se limpian "fósiles tipográficos", errores de teclado y artefactos visuales del Excel original:
* **Flechas rotas:** Convierte `Þ` y `⇒` a `=>`.
* **Símbolos de la fuente Symbol:** Convierte `¹` y `≠` a `!=`; `≥` y `³` a `>=`; `≤` y `£` a `<=`.
* **Errores de tipeo:** Corrige dedos resbalados en la coma como `.y,` a `.y.` y `.o,` a `.o.`.
* **Líneas decorativas:** Elimina divisores visuales (múltiples guiones bajos `___`).

### 2. Reglas Léxicas Soportadas (Tokens)
* **Códigos F22:** `[XXX]` (solo numéricos, ej. `[986]`, `[03]`).
* **Variables Declaradas:** El motor unifica variables estándar (`alfa`) y variables en corchetes (`[ m ]`, `[ j ]`), limpiando espacios, quitando corchetes a las letras y transformando todo implacablemente a mayúsculas latinas puras (ej. ambas pasan a ser `ALFA`, `M`, `J`).
* **Textos Seguros:** Soporta combinaciones alfanuméricas (ej. `M14A`, `14D1`) pero utiliza *Negative Lookahead* para evitar secuestrar palabras clave lógicas (`SI`, `SINO`, `ENTONCES`).
* **Parámetros y Vectores:** Detecta `PXX`, `VxXX` y `Vx01XX`, normalizando siempre a `Vx01XXXX`.
* **Funciones:** `MIN`, `MAX`, `POS`, `NEG`, `ROUND`, `ABS`.
* **RUT:** Funciones lógicas `SUBTIPO` y `ATRIBUTO`.
* **Operadores Lógicos y Relacionales:** `.y.`, `.o.`, `>=`, `<=`, `>`, `<`, `=`, `!=`. 

### 3. Reglas Sintácticas Complejas (Parser)
* **Árboles Condicionales:** Soporta condicionales anidados (`SI... ENTONCES... SINO...`) tanto en el bloque principal como dentro de las asignaciones y consecuencias de una implicación.
* **Validaciones Libres (Tipo M):** Soporta "sopas" de validación donde las variables se declaran arriba y la condición lógica principal queda al final (ej. `Suma = X`, `Alfa = Y`, `ENTONCES Suma = Alfa`). El formateador reordena la jerarquía ubicando la regla principal arriba y las variables abajo con la etiqueta `DONDE`.
* **Protección de Precedencia:** Envuelve automáticamente en paréntesis las series lógicas del tipo `SUBTIPO = 112 .o. 113` -> `SUBTIPO = ( 112 .O. 113 )` para evitar ambigüedades en motores matemáticos.
* **Comparaciones Condicionales:** Permite que el lado derecho de una comparación matemática sea un árbol condicional completo (ej. `>= SI... ENTONCES...`).

### 4. Manejo de Errores (Fail-Fast)
El módulo `formatter.py` atrapa excepciones de `lark` y devuelve un puntero visual `^` indicando la posición exacta del error. No adivina ni autocompleta:
* **Unexpected Characters/Tokens:** Errores de sintaxis y caracteres inválidos.
* **Unexpected EOF:** Atrapa fórmulas truncadas, incompletas o lógicamente ambiguas (ej. terminar en `SINO 0` en lugar de `SINO [123] = 0`), obligando al usuario a corregir la regla de negocio original por seguridad.
* Las fórmulas erróneas se reportan en consola y se descartan explícitamente de la generación del output.

### 5. Casos Fuera de Alcance
* **Validaciones Tipo F:** El operador unario de existencia (símbolo `$`) fue descartado y no se implementará en este motor por definición de alcance operativo.

## Siguientes Pasos
1. **Transición a Fase 2:** Con el output de `data/output_frontend.txt` unificado, estructurado y libre de ambigüedades, iniciar el diseño de la inyección de estos Árboles de Sintaxis Abstracta (AST) hacia el solver matemático (`z3-solver`).
2. **Definición de Tipos Z3:** Establecer la instanciación dinámica de variables (Enteros vs Reales) según los requisitos del modelo lógico del SII.