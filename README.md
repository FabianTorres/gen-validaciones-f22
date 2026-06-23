# Generador de Validaciones F22 (gen-validaciones-f22)

Motor generador de datos de prueba (Test Data Generator) para certificar las validaciones manuales del Formulario 22 (Operacion Renta - SII). 

El sistema toma algoritmos matematicos/logicos crudos, los normaliza mediante un analizador lexico/sintactico, y utiliza resolucion de restricciones matemáticas para generar matrices de casos de prueba (Positivos y Negativos) listos para ser consumidos en pruebas automatizadas.

## Estructura del Sistema

El proyecto se divide en dos fases independientes:
1. **Normalizador (Fase 1):** Valida la sintaxis cruda, alerta sobre errores bajo el principio "Fail-Fast" y devuelve una estructura parseada y estandarizada.
2. **Generador (Fase 2):** Motor matematico que calcula los valores limite y genera las combinaciones de datos (Data-Driven Testing).

## Estructura del Proyecto

gen-validaciones-f22/
|-- data/                       # Archivos de entrada y salida simulando el frontend
|   |-- input_excel.txt         # Formulas crudas copiadas por el usuario
|   |-- output_frontend.txt     # Formulas normalizadas resultantes
|
|-- docs/                       # Documentacion y bitacoras de estado
|   |-- contexto_actual.md      
|
|-- src/                        
|   |-- config/                 
|   |   |-- settings.py         # Mock de variables anuales (Fase 2)
|   |-- normalizador/           # FASE 1: Linter, Parser y Formatter
|   |   |-- parser.py           # Arbol de Sintaxis Abstracta (AST) usando lark
|   |   |-- formatter.py        # Validacion Fail-Fast y Pretty-Printer
|   |-- generador/              # FASE 2: Motor Matematico (En pausa)
|   |   |-- solver.py           
|
|-- main.py                     # Orquestador principal de pruebas
|-- requirements.txt            # 


## Stack Tecnologico
* **Lenguaje:** Python 3.x
* **Librerias principales:** `lark` (Parser), `z3-solver` (Solucionador Matematico), `pandas` (Estructuracion de salida).