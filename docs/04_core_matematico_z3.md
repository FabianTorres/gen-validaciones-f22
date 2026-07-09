# Core Matemático (Z3 Solver) e Ingeniería Interna

La Fase 2 del proyecto utiliza **Z3-Solver** (un solucionador de Satisfacibilidad Modulo Teorías o SMT) para resolver el Árbol de Sintaxis Abstracta (AST). Este documento registra los desafíos de arquitectura y las soluciones implementadas para domar el motor de C++ subyacente.

## 1. Arquitectura del Orquestador (Patrón Strategy)
Para evitar archivos monolíticos, la Fase 2 delega responsabilidades:
* **El Director (`test_builder.py`):** Lee la raíz del AST, clasifica la regla y resetea la memoria de Z3 por cada iteración.
* **Los Proveedores (`providers/`):** Inyectan el "Universo Constante" (ej. Parámetros anuales leídos de un JSON) y el "Universo de Identidad" (Búsqueda de RUTs reales) inmovilizándolos en la memoria del motor antes del cálculo.
* **Los Expertos (`strategies/`):** Clases (`BoundaryBuilder`, `ImplicationBuilder`, etc.) que aplican la lógica QA inyectando restricciones adicionales a Z3 (ej. el +1 peso) y extrayendo los escenarios usando el mecanismo `push()` y `pop()` de Z3 para limpiar la memoria entre casos.

## 2. Inferencia de Tipos Dinámica (El Problema del "Sino 0")
En el F22, es común encontrar `SI... ENTONCES [Ecuación] SINO 0`. Z3 prohíbe bifurcaciones donde una rama es lógica (`Boolean`) y otra matemática (`Integer`).
* **Solución (`evaluator.py`):** El evaluador intercepta la función `z3.If`. Si detecta que la rama `ENTONCES` devuelve una proposición lógica (ej. Validación Tipo D), transmuta automáticamente el `0` de la rama `SINO` en `z3.BoolVal(True)`, permitiendo que Z3 compile sin alterar el texto original del Excel.

## 3. Coerción de Tipos de Datos (Prevención del Parser Error)
Z3 es estrictamente tipado. Si se multiplica un Código F22 instanciado como Entero por un Parámetro decimal (ej. Reajuste de `1.05`), el motor C++ interno colapsa arrojando `b'parser error'`.
* **Solución (`z3_core.py`):** Se unificó el universo matemático. Todas las variables numéricas se instancian nativamente como **Reales (`z3.Real`)**. Z3 resuelve las ecuaciones en el espacio continuo y, justo antes de exportar el JSON para Selenium, la clase abstracta de las estrategias fuerza el casteo a Entero puro (`int`) dependiendo de la configuración global en `settings.py`.

## 4. Manejo de Estados Nulos y Blancos
El token `B` o texto vacío es sanitizado por la Fase 1 al string `"BLANCO"`. 
* **Manejo en Z3:** El `evaluator.py` actúa como *Gatekeeper*. Si lee el string `"BLANCO"`, no intenta instanciarlo como variable de texto (lo cual corrompería la matemática), sino que lo traduce inmediatamente al entero `0`, igualando el comportamiento interno del sistema del SII para campos vacíos.