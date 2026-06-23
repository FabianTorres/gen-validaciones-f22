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

## Estructura del Proyecto

```text
gen-validaciones-f22/
|-- data/                       # Archivos de entrada y salida (Simulación de Frontend)
|   |-- input_excel.txt         # Fórmulas crudas extraídas desde el Excel del SII
|   |-- output_frontend.txt     # Fórmulas normalizadas, indentadas y estructuradas
|
|-- docs/                       # Documentación técnica y bitácoras de estado
|   |-- contexto_actual.md      # Estado y alcance de la gramática del proyecto
|
|-- src/                        
|   |-- config/                 
|   |   |-- settings.py         # Mock de variables anuales y configuración (Fase 2)
|   |-- normalizador/           # FASE 1: Motor de Sanitización, Linter y Parser
|   |   |-- parser.py           # Gramática formal del F22 basada en la librería Lark
|   |   |-- formatter.py        # Capa de sanitización inteligente y Pretty-Printer AST
|   |-- generador/              # FASE 2: Motor Matemático (Resolución de Restricciones)
|   |   |-- solver.py           # Integración con el motor lógico
|
|-- main.py                     # Orquestador y ejecutor de pruebas por lotes
|-- requirements.txt            # Dependencias del entorno virtual

## Stack Tecnologico
* **Lenguaje:** Python 3.x
* **Librerias principales:**
- **lark** *(v1.3.1)*  
  Analizador léxico y sintáctico (Parser Earley).

- **z3-solver**  
  Solucionador de Teoremas y Satisfacibilidad Modular (SMT) para la Fase 2.

- **pandas**  
  Estructuración, análisis y exportación de las matrices de casos de prueba.