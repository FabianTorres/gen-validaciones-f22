# Reglas de Negocio F22 - Fase 2 (Z3 & QA Automático)

Este documento define las reglas de dominio del Formulario 22 y el comportamiento esperado del motor matemático (Z3) para generar casos de prueba compatibles con la automatización en Ambiente QA (Selenium).

## 1. Objetivo del Generador
El sistema no solo resuelve ecuaciones, sino que debe generar un set de datos (Payload) lógico y coherente que será inyectado por un bot de Selenium en el portal web del SII. 

## 2. Naturaleza de las Variables (Z3 Solver)
Para Z3, no todos los elementos de la fórmula son variables matemáticas a despejar. Se dividen rígidamente en dos grupos:

### A. Inputs Modificables (Lo que Z3 debe calcular)
Son los únicos elementos que el usuario QA puede digitar en el portal y, por lo tanto, las únicas variables que Z3 tiene libertad de alterar matemáticamente para cuadrar la ecuación.
* **Códigos F22:** Formato `[XXX]` (ej. `[123]`, `[955]`). *Excepción: `[03]`.*
* **Vectores:** Formato `Vx01XXXX` (ej. `Vx014110`).

### B. Valores de Solo Lectura (Constantes externas)
Son elementos cuyo valor viene predefinido por el SII o la base de datos, y Z3 debe tratarlos como números fijos (constantes) dentro de su ecuación.
* **Parámetros (`PXXX`):** Representan valores anuales o fijos (ej. `P09`, `P174`).
  * Su valor se extrae de una tabla externa provista por el SII.
  * Pueden ser de tipo: *Enteros*, *Decimales* o *Fechas* (DD/MM/AAAA, AAAA/MM/DD, DDMMAAAA, AAAAMMDD).

## 3. Diccionario de Funciones del SII
El evaluador `evaluator.py` debe interpretar las siguientes funciones nativas del SII respetando estrictamente esta lógica:
* `MAX{X, Y}`: Selecciona el mayor valor entre X e Y.
* `MIN{X, Y}`: Selecciona el menor valor entre X e Y.
* `ABS{X}`: Valor absoluto de X.
* `ROUND{X}`: Redondeo aritmético estándar (>= 0.5 hacia arriba, < 0.5 hacia abajo).
* `POS{X}`: Si X > 0, retorna X. Si es negativo o cero, retorna 0.
* `NEG{X}`: Si X < 0, retorna el valor absoluto de X `ABS(X)`. Si es positivo o cero, retorna 0.

## 4. Lógica de Identidad (RUT y Atributos)
El código `[03]` representa el RUT del contribuyente. Las funciones asociadas a este código no se resuelven con álgebra, sino mediante una búsqueda de base de datos.

* **Funciones de Identidad:** `TIPO{[03]}` y `SUBTIPO{[03]}`.
* **Variables de Identidad:** `atributo` (ej. `14D1`, `14TT`).
* **Mecanismo de Resolución:**
  1. Z3 detectará las restricciones lógicas exigidas por la fórmula (ej. *Se necesita TIPO = 2 y ATRIBUTO = M14A*).
  2. El motor consultará un "Archivo de RUTs" de pruebas con el formato: `RUT | TIPO | SUBTIPO | ATRIBUTO` (ej. `3-5|2|112|14D1;14TT`).
  3. Al encontrar una fila que cumpla las condiciones, el motor tomará ese `RUT` y se lo asignará permanentemente a la variable `[03]` en el set de datos final para que Selenium lo digite.