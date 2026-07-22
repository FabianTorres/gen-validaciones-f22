# Diccionario de Datos: Salida JSON (QA & Selenium)

Este documento define el contrato estricto de datos (Payload) que el motor generador (Z3) exportará en el archivo `output_matrices_qa.json`. Su objetivo es guiar a los ingenieros de automatización (Selenium) y analistas de QA sobre los campos y valores exactos que pueden esperar en cada escenario.

## Estructura Base del JSON

Cada objeto dentro de la lista exportada representará un caso de prueba ejecutable con la siguiente estructura:

```json
{
    "id_validacion": "a.4.1",
    "tipo_escenario": "CALCULO_VERDADERO_MIN_IZQ",
    "descripcion_qa": "La condición se cumple y el límite MIN toma el valor del primer argumento.",
    "rut": "11.111.111-1",
    "inputs": {
        "[465]": 0,
        "[547]": 1000000
    },
    "resultado_esperado": "VERIFICAR_AUTOCALCULO"
}
```

### Reglas de Mapeo en el Objeto `inputs` (Filtros y Checkboxes)
Para garantizar que Selenium Web-Driver interactúe fluidamente con el portal sin romperse, el motor aplica dos reglas automáticas sobre la clave `inputs`:
1. **Filtro de Celdas Tangibles:** Variables auxiliares declaradas en la regla (ej. `ALFA`, `BETA`) o atributos puros (ej. `M14A`) son filtradas silenciosamente. El JSON solo emitirá celdas estrictas en formato `[XXX]` o vectores `Vx`.
2. **Mapeo Binario de Marcas (Checkboxes):** Las celdas que gráficamente son un checkbox y cuya regla de negocio valida un texto como `"X"` o `"BLANCO"`, jamás se exportarán como texto. El motor exportará el entero **`1`** (si la celda debe ir marcada) o un **`0`** (si debe ir desmarcada). Los scripts de automatización deben interpretar esto de forma binaria.

---

## Catálogo de Valores Permitidos

Para facilitar la programación de los *Asserts* en Selenium, los campos clave solo emitirán valores pertenecientes a este catálogo estricto:

### 1. `resultado_esperado` (El Assert de QA)
Indica qué reacción gráfica se debe buscar en el portal web del Formulario 22 tras digitar los inputs.

| Valor Exacto | Reacción Esperada en el Portal |
| :--- | :--- |
| **`CON_VALIDACION`** | El sistema **debe** bloquear el envío o arrojar un recuadro rojo de error. |
| **`SIN_VALIDACION`** | El sistema **no debe** arrojar errores (Happy Path o flujo ignorado). |
| **`VERIFICAR_AUTOCALCULO`** | No buscar errores. Se debe leer la celda bloqueada (gris) y verificar que coincida con los inputs generados. |

---

### 2. `tipo_escenario`
Indica la técnica de testing que el motor matemático aplicó para generar los datos.

| Familia de Regla | Valor Exacto | Descripción de la Técnica |
| :--- | :--- | :--- |
| **Cotas y Límites** | `LIMITE_EXACTO` | Prueba el límite matemático justo (Frontera exacta). |
| | `EXCEDE_LIMITE` | Prueba la frontera superior (+1 peso de diferencia). |
| | `BAJO_LIMITE` | Prueba la frontera inferior (-1 peso de diferencia). |
| **Implicaciones (=>)** | `CUMPLE_CONDICION` | El gatillo es verdadero y la consecuencia se cumple. |
| | `INCUMPLE_CONDICION` | El gatillo es verdadero, pero la consecuencia se omite (Error). |
| | `NO_APLICA` | El gatillo es falso (ej. RUT no compatible), la regla se ignora. |
| **Autocalculados** | `CALCULO_LINEAL_EXACTO` | Resolución de ecuación sin condicionales (Happy Path simple).|
| | `CALCULO_VERDADERO_SIMPLE` | El condicional (IF) principal se cumple.[cite: 4]|
| | `CALCULO_FALSO_SINO_*` | Sub-condición del IF principal es falsa, forzando la celda al valor por defecto. |
| | `CALCULO_VERDADERO_ANIDADO_*` | Un IF interno (recursivo) se cumple garantizando el flujo de la ruta superior. |
| | `CALCULO_FALSO_ANIDADO_*_SINO_*` | Un IF interno falla, forzando su rama SINO sin perder el flujo principal. |
| | `CALCULO_MIN_IZQ` / `DER` | Límite MIN toma el argumento izquierdo/derecho garantizando la ruta lógica. |
| | `CALCULO_MAX_IZQ` / `DER` | Límite MAX toma el argumento izquierdo/derecho garantizando la ruta lógica. |
| | `CALCULO_POS_MAYOR_CERO` / `MENOR_CERO` | Límite interno de POS evaluado en positivo, o negativo (forzando salida a 0). |
| | `CALCULO_NEG_MAYOR_CERO` / `MENOR_CERO` | Límite interno de NEG evaluado en positivo (forzando 0), o negativo (valor absoluto). |
| | `ABS_ENTRADA_POSITIVA` / `NEGATIVA` | Prueba el valor interno de ABS validando su correcta conversión de signo. |

---

### 3. `descripcion_qa`
Glosas humanas estandarizadas que acompañan a cada `tipo_escenario` para dar contexto de negocio al tester o al log de ejecución.

* **Para Cotas y Límites:**
  * `"El valor ingresado es exactamente igual al límite matemático de la regla."`
  * `"El valor ingresado supera el tope permitido de la regla por 1 peso."`
  * `"El valor ingresado se mantiene justo por debajo del límite de la regla."`
* **Para Implicaciones:**
  * `"El contribuyente cumple la condición inicial y también satisface la exigencia final de la regla."`
  * `"Se fuerza un error: El contribuyente cumple la condición inicial, pero se omite llenar la exigencia final obligatoria."`
  * `"La regla no aplica para este caso (ej. atributos de RUT distintos). El sistema no debería exigir nada adicional."`
* **Para Autocalculados y Lógica Libre:**
  * `"Se resuelve la ecuación matemática lineal de forma exacta sin ramificaciones."`
  * `"La condición principal se cumple (Rama ENTONCES)."`[cite: 4]
  * `"La sub-condición X del IF principal falla, mientras las demás se cumplen. Se fuerza la celda al valor por defecto (Sino)."`
  * `"La condición ANIDADA_X se cumple (Rama ENTONCES alcanzada)."`
  * Lógicas de límites `MIN` / `MAX`: *"El límite toma el valor izquierdo/derecho garantizando su ruta de ejecución."*
  * Lógicas de control de signo `POS` / `NEG` / `ABS`: *"El valor interno es positivo/negativo, forzando su ruta correcta, conversión o valor absoluto."*

---

## Filtrado de Exportación: Variables Visibles vs. Variables de Estado

El diccionario `"inputs"` dentro del JSON exportado **no es un volcado crudo de la memoria de Z3**. Está estrictamente filtrado para garantizar compatibilidad directa con los payloads que consume el bot de automatización en Selenium (interfaz de usuario).

Z3 evalúa decenas de restricciones matemáticas invisibles (ej. booleanos, parámetros de cruce, condiciones de RUT), pero el exportador (`BaseStrategy`) aplica un mecanismo de "Doble Candado" para sanitizar el output.

**Regla de Exclusión:**
Las siguientes variables son tratadas como *Variables de Estado* en el backend matemático y jamás aparecerán en el bloque `"inputs"` del JSON:
* Declaraciones condicionales o variables auxiliares (ej. `E`, `ALFA`, `[ e ]`).
* Compuertas lógicas de atributos de negocio (ej. `IS_ATRIBUTO_M14A`).
* Funciones vinculadas a la identidad del contribuyente (ej. `TIPO_[03]`, `SUBTIPO_[03]`).

**Regla de Inclusión (Doble Candado):**
Para que una variable sea considerada una "celda" y exportada a `"inputs"`, debe cumplir de forma simultánea:
1. **Identidad Estructural:** Su nombre comienza con un corchete de apertura `[` y finaliza con un corchete de cierre `]`.
2. **Identidad Numérica:** Su interior contiene obligatoriamente al menos un carácter numérico (dígito), descartando falsos positivos originados por variables abstractas. (Excepción: Identificadores de vectores como `Vx`).

Esto asegura que el JSON final contenga únicamente códigos tributarios que existen físicamente en los formularios del portal del SII.


## Excepciones y Casos de Error

Si el Excel del SII contiene una regla que es matemáticamente imposible o contradictoria (ej. `[100] > 5 .Y. [100] < 2`), el motor matemático abortará la generación de inputs y devolverá este objeto especial de diagnóstico:

```json
{
    "id_validacion": "c.99.1",
    "estado_interno": "INSATISFACTIBLE",
    "detalle": "Contradicción matemática. Revisar si la regla es lógicamente posible."
}
```