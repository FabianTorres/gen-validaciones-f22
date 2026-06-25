# Estrategia de Diseño: Fase 2 (Generador Z3)

## 1. El Problema del "Sino 0" (Choque de Tipos)
En las fórmulas del SII (especialmente tipo D y E), es común encontrar condicionales donde la rama `ENTONCES` es una ecuación booleana (ej. `Suma = 0`), pero la rama `SINO` se define flojamente como `0` en lugar de `Verdadero`. Z3 prohíbe devolver un Booleano en una rama y un Entero en otra.

## 2. La Solución: Inferencia de Tipos Dinámica en `evaluator.py`
Para no romper la Fase 1 ni exigir corrección manual del Excel, delegaremos la inferencia semántica al Evaluador de Z3.

**Algoritmo de Inferencia para `z3.If`:**
1. **Evaluar la rama `ENTONCES`:** Identificar su naturaleza final -> `Matemática` (int/real) o `Lógica` (bool).
2. **Mutar la rama `SINO` según el contexto:**
   * **Contexto Matemático (Validaciones A, B, C):** Si el `ENTONCES` devuelve números (ej. `[100] + 5`), el `SINO 0` se inyecta literalmente como el entero `0`.
   * **Contexto Lógico (Validaciones D, E):** Si el `ENTONCES` es una condición (ej. `[100] = 5`), el `SINO 0` se intercepta y se inyecta silenciosamente a Z3 como `z3.BoolVal(True)`.

## 3. Manejo del Estado "BLANCO"
El Normalizador (Fase 1) ya sanitiza el token `B` mutándolo a `"BLANCO"` en el AST. 
* **Regla en Fase 2:** El evaluador debe interceptar comparaciones contra el string `"BLANCO"` y traducirlas a condiciones de nulidad o igualdades a `0`, dependiendo de la definición técnica final del modelo de datos para campos vacíos.