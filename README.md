# Generador de Validaciones F22 (gen-validaciones-f22)

Motor generador de datos de prueba para certificar las validaciones del Formulario 22.

El sistema toma algoritmos matemáticos/lógicos crudos, los somete a una capa de pre-procesamiento resiliente, los normaliza mediante un analizador léxico/sintáctico libre de contexto, y prepara la estructura lógica para la posterior resolución de restricciones matemáticas, permitiendo generar matrices de casos de prueba (Positivos y Negativos) listos para pruebas automatizadas.

## Estructura del Sistema

El proyecto se divide en dos fases independientes y modulares:

1. **Normalizador (Fase 1):** Aplica una capa de sanitización inteligente sobre la entrada cruda del Excel y analiza su sintaxis de forma estricta. Alerta sobre ambigüedades lógicas o errores de escritura bajo el principio *Fail-Fast*, devolviendo un formato estructurado, jerárquico y unificado de la regla de negocio.
2. **Generador (Fase 2):** Motor matemático encargado de digerir el Árbol de Sintaxis Abstracta (AST) generado en la fase anterior para calcular valores límite y generar combinaciones de datos eficientes (*Data-Driven Testing*).

---

## Características Destacadas del Normalizador (Fase 1)

* **Arquitectura Limpia en 5 Fases:** Separación estricta de responsabilidades (*Separation of Concerns*). El Parser (Lark) lee tolerando flexibilidades humanas, un Linter Semántico inyectado en Python juzga el cumplimiento de las reglas de negocio bloqueantes, y un Formateador dibuja el resultado final.
* **Sanitización Inteligente y Resiliente:** Pre-procesamiento automático que limpia fósiles tipográficos (`Þ` y `⇒` a `=>`; `¹` y `≠` a `!=`), corrige errores de teclado comunes (`.y,` / `""x""`), transforma el lenguaje natural (`o` y `y`) a operadores booleanos, e inyecta colchones de espacios para evitar la "Tokenización Codiciosa".
* **Soporte de Estructuras Complejas:** Capacidad recursiva para procesar árboles anidados, validaciones de lógica libre (Tipo M), Cotas Encadenadas (`A <= B <= C`) y protección de precedencia envolviendo series en paréntesis.
* **Mutación de AST (Desugaring):** Fase intermedia silenciosa que convierte listas compactas de Excel (`TIPO = 1, 2, 3`) en compuertas matemáticas puras y expandidas (`TIPO = 1 .O. TIPO = 2...`), y convierte estados nulos (`B`) en el string explícito `"BLANCO"`.
* **Análisis Semántico de Condicionales:** El motor diferencia entre condicionales de "Cálculo" (que exigen un `SINO` para resolver una ecuación) y condicionales de "Acción" (asignaciones directas donde el `SINO` es opcional).
* **Control de Errores Avanzado (API Ready):** Retorna diccionarios estructurados que capturan excepciones del compilador (`UnexpectedEOF`, `UnexpectedToken`, `ValueError`), desplegando un puntero visual `^` y traduciendo los errores estructurales a sugerencias humanas para el Frontend (ej. *"Las reglas Tipo C exigen obligatoriamente indicar qué ocurre si la condición es falsa"*).

---

## Características Destacadas del Generador Z3 (Fase 2)

* **Fusión Estática de Memoria:** A través del token `VARIABLE_CORCHETE`, el evaluador limpia y unifica variables abstractas (`[ e ]` a `"E"`). Z3 garantiza que las declaraciones condicionales (`E = SI...`) y su uso en ecuaciones (`... * E`) compartan el mismo puntero en memoria, obligando al motor a resolver la lógica en lugar de adivinar variables libres.
* **Doble Candado de Exportación (Sanitización de Payloads):** El sistema distingue entre *variables de estado* (lógica matemática temporal) y *celdas del formulario*. Para que un dato llegue al JSON final de Selenium, debe cumplir con una identidad estructural (`[...]`) y contener estrictamente al menos un dígito numérico. Las variables abstractas jamás se filtran a la UI.
* **Análisis Estático de Rutas (BVA + MCDC):** Las pruebas de Valores Límite en funciones internas (`MIN`, `MAX`, `POS`) no se aplican ciegamente. Un *rastreador de guardias lógicas* escanea el AST y amarra matemáticamente la función a la rama condicional (`ENTONCES` o `SINO`) a la que pertenece. Esto erradica los "falsos positivos" y la ejecución de pruebas sobre código muerto.
* **Determinismo e Idempotencia (Deduplicación de Casos):** El proveedor de RUTs prescinde de la aleatoriedad. Utiliza un catálogo inmovilizado en memoria, donde exigencias lógicas idénticas siempre retornan exactamente el mismo RUT base. Esto permite al algoritmo de deduplicación interceptar ramas matemáticas redundantes y colapsarlas, garantizando el mínimo set de pruebas posibles para un 100% de cobertura.

---

## Estructura del Proyecto

```text
gen-validaciones-f22/
|-- data/                       # Archivos de entrada, catálogos y salidas generadas
|   |-- casos_selenium.csv      # Archivo final exportado con los casos listos para el bot
|   |-- catalogo_codigos.txt    # Catálogo maestro de códigos del SII
|   |-- catalogo_mensajes.txt   # Catálogo maestro de mensajes de error
|   |-- catalogo_parametros.txt # Diccionario de valores anuales constantes (P08, P84, etc.)
|   |-- input_excel.txt         # Fórmulas crudas extraídas desde el Excel del SII
|   |-- mock_ruts_qa.json       # Base de datos estática de RUTs con sus Atributos y Tipos
|   |-- output_arbol.txt        # Exportación del AST para depuración manual
|   |-- output_frontend.txt     # Fórmulas normalizadas para la vista
|   |-- output_matrices_qa.json # JSON intermedio con la matriz de pruebas generada
|
|-- docs/                       # Documentación técnica y reglas de negocio maestras
|   |-- 01_arquitectura_fase1.md     # Estructura del Normalizador, Parser y Linter
|   |-- 02_reglas_negocio_f22.md     # Catálogo de validaciones, funciones SII y Universos
|   |-- 03_estrategia_qa_selenium.md # Comportamiento de Testing (Valores Límite y Matrices)
|   |-- 04_core_matematico_z3.md     # Arquitectura de la Fase 2, Inferencia y Coerción de tipos
|   |-- 05_diccionario_salida_json.md # Formato y reglas del Payload exportado para QA
|
|-- src/                        
|   |-- config/                 
|   |   |-- settings.py         # Mock de variables y switches globales (USAR_DECIMALES)
|   |
|   |-- normalizador/           # FASE 1: Motor de Sanitización, Linter y Parser 
|   |   |-- formatter.py        
|   |   |-- parser.py           
|   |
|   |-- generador/              # FASE 2: Motor Matemático y Constructor de Casos QA
|   |   |-- evaluator.py        # Traductor: Convierte AST a funciones nativas de Z3
|   |   |-- exportador_csv.py   # Módulo que transforma el JSON en CSV para Selenium
|   |   |-- solver.py           # Orquestador principal de la Fase 2 que llama al TestBuilder
|   |   |-- test_builder.py     # DIRECTOR: Orquesta las estrategias según el tipo de regla
|   |   |-- z3_core.py          # Envoltorio Z3: Administra el solver en dominio Real
|   |   |
|   |   |-- providers/          # PROVEEDORES: Inyectan el "Universo Constante e Identidad"
|   |   |   |-- param_provider.py 
|   |   |   |-- rut_provider.py   
|   |   |
|   |   |-- strategies/         # ESTRATEGIAS: Expertos en Análisis de Valores (QA Lógico)
|   |       |-- base_strategy.py       
|   |       |-- boundary_builder.py    
|   |       |-- calculation_builder.py 
|   |       |-- implication_builder.py 
|
|-- main.py                     # Orquestador del lote de Fórmulas (Fase 1)
|-- test_z3.py                  # Sandbox y orquestador de pruebas unitarias para la Fase 2
|-- README.md                  
|-- requirements.txt