# Generador de Validaciones F22 (gen-validaciones-f22)

Motor generador de datos de prueba para certificar las validaciones del Formulario 22.

El sistema toma algoritmos matemáticos/lógicos crudos, los somete a una capa de pre-procesamiento resiliente, los normaliza mediante un analizador léxico/sintáctico libre de contexto, y prepara la estructura lógica para la posterior resolución de restricciones matemáticas, permitiendo generar matrices de casos de prueba (Positivos y Negativos) listos para pruebas automatizadas.

## Estructura del Sistema

El proyecto se divide en dos fases independientes y modulares:

1. **Normalizador (Fase 1):** Aplica una capa de sanitización inteligente sobre la entrada cruda del Excel y analiza su sintaxis de forma estricta. Alerta sobre ambigüedades lógicas o errores de escritura bajo el principio *Fail-Fast*, devolviendo un formato estructurado, jerárquico y unificado de la regla de negocio.
2. **Generador (Fase 2):** Motor matemático encargado de digerir el Árbol de Sintaxis Abstracta (AST) generado en la fase anterior para calcular valores límite y generar combinaciones de datos eficientes (*Data-Driven Testing*).

## Características Destacadas del Normalizador (Fase 1)

* **Sanitización Inteligente de Entrada:** Pre-procesamiento automático que limpia fósiles tipográficos de la fuente *Symbol* de Microsoft Office (`Þ` y `⇒` a `=>`; `¹` y `≠` a `!=`; `≥` y `³` a `>=`; `≤` y `£` a `<=`), corrige errores de teclado comunes en la redacción del SII (`.y,` / `.o,`), y elimina separadores decorativos (`___`).
* **Unificación de Variables:** Identifica y "desnuda" variables declaradas de texto o encerradas en corchetes con espacios o caracteres griegos (`[ m ]` / `[ j ]`), estandarizándolas a mayúsculas latinas puras (`M`, `J`), diferenciándolas de manera inteligente de los códigos numéricos oficiales del formulario (ej. `[750]`).
* **Soporte de Estructuras Complejas:** Capacidad recursiva para procesar árboles de decisión anidados (`SI... ENTONCES... SINO...`), validaciones de lógica libre (Tipo M) donde las declaraciones preceden a la regla, y comparaciones con condicionales del lado derecho (Tipo N).
* **Blindaje de Precedencia:** Inyección automática de paréntesis en expansiones de series de atributos o subtipos (ej. `SUBTIPO = ( 112 .O. 113 )`) para eliminar la ambigüedad en la precedencia de operadores lógicos de cara a la Fase 2.
* **Control de Errores Avanzado (Fail-Fast):** Captura excepciones del compilador (`UnexpectedCharacters`, `UnexpectedToken`, `UnexpectedEOF`) desplegando un puntero visual `^` de la falla y traduciendo los errores estructurales a lenguaje natural (ej. diagnosticando fórmulas truncadas o reglas de negocio lógicamente ambiguas).
* **Sanitización Inteligente de Entrada:** Pre-procesamiento automático que limpia fósiles tipográficos (`Þ` a `=>`, `¹` a `!=`), corrige errores de teclado comunes (`.y,` / `""x""`), transforma el lenguaje natural (`o` y `y`) a operadores booleanos, y estandariza variables entre corchetes.
* **Mutación de AST (Desugaring):** Fase intermedia silenciosa que convierte listas compactas de Excel (`TIPO = 1, 2, 3`) en compuertas matemáticas puras y expandidas (`TIPO = 1 .O. TIPO = 2...`), y convierte estados nulos (`B`) en el string explícito `"BLANCO"` para blindar a Z3 de variables huérfanas.
* **Análisis Semántico de Condicionales:** El motor diferencia entre condicionales de "Cálculo" (que exigen un `SINO` para resolver una ecuación) y condicionales de "Acción" (asignaciones directas donde el `SINO` es opcional), validando el sentido de negocio antes de la sintaxis.
* **Soporte de Estructuras Complejas:** Capacidad recursiva para procesar árboles anidados, validaciones de lógica libre (Tipo M), y protección de precedencia envolviendo series en paréntesis.
* **Control de Errores Avanzado (API Ready):** Retorna diccionarios estructurados que capturan excepciones (`UnexpectedEOF`, `UnexpectedToken`, `ValueError`), diagnosticando fórmulas truncadas y emitiendo sugerencias humanas para el Frontend (ej. *"Falta agregar Sino 0"*).
* **Arquitectura Limpia en 5 Fases:** Separación estricta de responsabilidades (*Separation of Concerns*). El Parser (Lark) lee tolerando flexibilidades humanas, un Linter Semántico inyectado en Python juzga el cumplimiento de las reglas de negocio bloqueantes, y un Formateador dibuja el resultado final.
* **Sanitización Resiliente:** Protecciones activas contra la "Tokenización Codiciosa" (agregando colchones de espacios en operadores mal digitados como `. o .`) y conversión automática de fósiles tipográficos (`Þ`, `¹`, `£`).
* **Soporte de Expresiones Matemáticas Avanzadas:** Capacidad nativa para interpretar y estructurar *Cotas Encadenadas* (`A <= B <= C`) y *Condicionales Recursivos* anidados (`SINO SI...`).
* **Mutación de AST (Desugaring):** Fase intermedia silenciosa que convierte listas compactas de Excel (`TIPO = 1, 2, 3`) en compuertas booleanas matemáticas puras expandidas, y convierte estados nulos (`B`) en el string explícito `"BLANCO"`.
* **Control de Errores Avanzado (API Ready):** Retorna diccionarios estructurados (JSON) que capturan excepciones de la gramática, diagnosticando fórmulas truncadas y emitiendo alertas de negocio precisas para el Frontend (ej. *"Las reglas Tipo C exigen obligatoriamente indicar qué ocurre si la condición es falsa"*).


## Estructura del Proyecto

```text
gen-validaciones-f22/
|-- data/                       # Archivos de entrada, salida y fuentes de datos mockeadas
|   |-- input_excel.txt         # Fórmulas crudas extraídas desde el Excel del SII
|   |-- output_arbol.txt        # Exportación del AST para depuración
|   |-- output_frontend.txt     # Fórmulas normalizadas para la vista
|   |-- mock_parametros.json    # Diccionario de valores anuales constantes (P08, P84, etc.)
|   |-- mock_ruts_qa.json       # Base de datos de RUTs con sus Atributos y Tipos
|
|-- docs/                       # Documentación técnica y reglas de negocio maestras
|   |-- 01_arquitectura_fase1.md     # Estructura del Normalizador, Parser y Linter
|   |-- 02_reglas_negocio_f22.md     # Catálogo de validaciones, funciones SII y Universos
|   |-- 03_estrategia_qa_selenium.md # Comportamiento de Testing (Valores Límite y Matrices)
|   |-- 04_core_matematico_z3.md     # Arquitectura de la Fase 2, Inferencia y Coerción de tipos
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
|   |   |-- evaluator.py        # Traductor: Convierte AST a funciones nativas de Z3.
|   |   |-- z3_core.py          # Envoltorio Z3: Administra el solver en dominio Real.
|   |   |-- test_builder.py     # DIRECTOR: Orquesta las estrategias según el tipo de regla.
|   |   |
|   |   |-- providers/          # PROVEEDORES: Inyectan el "Universo Constante e Identidad"
|   |   |   |-- param_provider.py 
|   |   |   |-- rut_provider.py   
|   |   |
|   |   |-- strategies/         # ESTRATEGIAS: Expertos en Análisis de Valores (QA Lógico)
|   |       |-- base_strategy.py       
|   |       |-- calculation_builder.py 
|   |       |-- boundary_builder.py    
|   |       |-- implication_builder.py 
|
|-- main.py                     # Orquestador del lote de Fórmulas (Fase 1)
|-- test_z3.py                  # Sandbox y orquestador de pruebas unitarias para la Fase 2
|-- README.md                   
|-- requirements.txt
```

## Stack Tecnologico
* **Lenguaje:** Python 3.x
* **Librerias principales:**
- **lark** *(v1.3.1)*  
  Analizador léxico y sintáctico (Parser Earley).

- **z3-solver**  
  Solucionador de Teoremas y Satisfacibilidad Modular (SMT) para la Fase 2.

- **pandas**  
  Estructuración, análisis y exportación de las matrices de casos de prueba.