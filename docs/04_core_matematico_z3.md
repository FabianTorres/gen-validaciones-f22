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

## 5. Mapeo de Dominios Binarios y Restricción (Checkboxes)
El sistema se enfrenta a variables de entrada que operan como marcas discretas en la UI (ej. un checkbox "X") en lugar de campos matemáticos continuos. Si Z3 evalúa esto como texto libre, el motor C++ colapsa (`b'parser error'`). Si se instancia como una variable Real sin control, el sistema sufre de "Domain Overflow" (Z3 podría asignar un valor absurdo como `500` a un checkbox para equilibrar la ecuación y alcanzar la semilla).
* **Solución (Escudo Interceptor en `evaluator.py`):** El evaluador intercepta los tokens antes de que toquen el motor matemático. Si detecta el token puro `"X"`, lo transmuta inmediatamente al entero `1`. El token `"BLANCO"` o texto vacío[cite: 3] se transforma en `0`[cite: 3].
* **Bloqueo de Dominio (`z3_core.py`):** Simultáneamente, al instanciar la variable en memoria (ej. `[95]`), el motor consulta el catálogo base en caché. Si el código es de tipo marca, inyecta una restricción de dominio binario inquebrantable (`z3.Or(var == 0, var == 1)`). Esto obliga a Z3 a resolver condiciones complejas como `[95] != "X"` usando estrictamente lógica binaria matemática (`[95] != 1`), garantizando que Selenium reciba valores inyectables.

### Soporte Extendido de Funciones Matemáticas
El motor `Evaluator` soporta la evaluación nativa de funciones complejas de negocio inyectando lógicas condicionales directamente en el solver Z3:
* **NEG:** Implementa la lógica de valor absoluto condicionado. Si el argumento evaluado es menor a 0, Z3 retorna su valor absoluto (`-arg`). Si es positivo o cero, Z3 lo fuerza a `0`.
* **POS, MIN, MAX, ROUND:** (Mantienen su comportamiento base).

### Contexto Base y Prevención de Anomalías (Path Locking & MCDC Recursivo)
Para evitar que el motor resuelva fronteras matemáticas evadiendo el flujo lógico principal (Falso Positivo de Ruta)[cite: 3], o invente "números fantasma" al desconocer las reglas que rigen a las variables auxiliares, el `CalculationBuilder` implementa un motor de rastreo avanzado sobre el Árbol de Sintaxis Abstracta (AST):
* **Empaquetado de Contexto Base:** Z3 opera bajo resolución simultánea. Antes de generar escenarios, el Builder extrae la regla principal (`autocalculado`) junto a TODAS las variables y ecuaciones auxiliares (nodos `cota` y `declaracion_variable`) de la raíz de la validación. Todo se empaqueta como "Premisas Universales", obligando a Z3 a respetar la matemática del sistema completo y no solo de la regla aislada.
* **Bloqueo Semántico de Rutas (Reachability):** Antes de evaluar los límites de una función (`MIN`, `MAX`, `POS`, `NEG`, `ABS`)[cite: 3] o bifurcaciones internas, el método `_obtener_camino_a_nodo` rastrea el árbol en dos dimensiones:
  1. *Sintáctica:* Verifica el anidamiento físico (si la función reside dentro de una rama `ENTONCES` o `SINO` específica)[cite: 3].
  2. *Semántica:* Verifica el uso de variables calculadas (identificando en qué rama superior se invoca la variable evaluada).
* Posteriormente, inyecta la suma de estas restricciones lógicas previas en las premisas base[cite: 3], obligando al solver a caminar estrictamente por el bloque de código requerido[cite: 3] y garantizando cobertura algorítmica sobre ramas anidadas sin perder el flujo principal.

### Inyección de Brecha de Frontera (Safety Gap)
Las pruebas de límites matemáticos (ej. forzar que un `POS` evalúe a negativo) utilizan una brecha dinámica (`gap`). 
* Si `settings.USAR_DECIMALES` es falso, `gap = 1`. 
* Esto asegura que Z3 genere valores que superen holgadamente el límite por un número entero (ej. forzando un `-1` real en lugar de un `0`), protegiendo la aserción de QA contra redondeos ocultos o colisiones en la interfaz web del SII.

# Estrategias Avanzadas de Z3
## Fusión de Variables y Referencias en Memoria

Para que Z3 pueda resolver reglas de negocio complejas, requiere que las variables de estado declaradas (`E = SI(...)`) y sus ejecuciones en fórmulas (`... * E`) apunten exactamente a la misma referencia de memoria. 

El Evaluador de la Fase 2 implementa una política de **Fusión de Variables** estricta. Al procesar los tokens del AST (`TEXTO` o `VARIABLE_CORCHETE`), el evaluador aplica una limpieza profunda: elimina corchetes y espacios en blanco (`[ e ]` se transforma internamente en `"E"`). 
Al invocar `motor.obtener_o_crear_variable("E")`, Z3 garantiza que ambas instancias del árbol sintáctico se resuelvan como un único puntero. Esto evita que el motor asigne valores "libres" (ej. un millón) para cuadrar la ecuación rápidamente, obligándolo a respetar la lógica condicional que dicta si la variable debe valer 0 o 1.

## Análisis Estático de Rutas y Prevención de Pruebas Fantasma (BVA + MCDC)

Las funciones internas (como `MIN`, `MAX`, `POS`, `NEG`, `ABS`) encapsuladas dentro de reglas tipo Cota presentan un desafío algorítmico: si una de estas funciones se encuentra dentro de un bloque condicional anidado (por ejemplo, en el `SINO` de una regla), aplicar el Análisis de Valores Límite (BVA) de forma global genera **"pruebas fantasma"**. Es decir, Z3 puede forzar matemáticamente los argumentos del `MIN`, pero evaluar el límite contra una ruta que representa código muerto (ej. la rama `ENTONCES`).

Para lograr una cobertura perfecta sin falsos positivos, la estrategia `BoundaryBuilder` implementa un modelo híbrido BVA + MCDC (Modified Condition/Decision Coverage):

1. **Inyección MCDC:** El motor mapea todas las condiciones lógicas del árbol y ejecuta el BVA sobre cada rama lógica posible de manera aislada (Rutas Verdaderas, Falsas y Anidadas).
2. **Rastreador de Guardias (`_obtener_guardias_nodo`):** Antes de estresar una función interna, un analizador estático recorre el AST desde la raíz hasta encontrar la función objetivo. Si detecta que la función está "encerrada" en un bloque condicional, captura matemáticamente esa condición lógica y la inyecta como un **candado obligatorio** en el solver (Guardias Activas).
3. **Ejecución Precisa:** Z3 está matemáticamente forzado a navegar por la rama lógica correcta antes de evaluar los argumentos de la función, asegurando que las pruebas de frontera operen exclusivamente sobre código vivo.
