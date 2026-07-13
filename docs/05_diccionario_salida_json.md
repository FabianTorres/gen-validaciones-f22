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
| **Autocalculados** | `CALCULO_LINEAL_EXACTO` | Resolución de ecuación sin condicionales (Happy Path simple). |
| | `CALCULO_VERDADERO_SIMPLE` | El condicional (IF) se cumple, sin límites MIN/MAX involucrados. |
| | `CALCULO_VERDADERO_MIN_IZQ` | El condicional se cumple y domina el argumento izquierdo del MIN. |
| | `CALCULO_VERDADERO_MIN_DER` | El condicional se cumple y domina el argumento derecho del MIN. |
| | `CALCULO_VERDADERO_MAX_IZQ` | El condicional se cumple y domina el argumento izquierdo del MAX. |
| | `CALCULO_VERDADERO_MAX_DER` | El condicional se cumple y domina el argumento derecho del MAX. |
| | `CALCULO_FALSO_SINO` | La condición es falsa, forzando la celda al valor por defecto (Sino). |

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
  * `"Se resuelve la ecuación matemática lineal de forma exacta."`
  * `"La condición del IF se cumple y se calcula el monto directo."`
  * `"La condición se cumple y el límite MIN toma el valor del primer argumento (izquierdo)."`
  * `"La condición se cumple y el límite MIN se topa con el segundo argumento (derecho)."`
  * `"La condición se cumple y el límite MAX toma el valor del primer argumento (izquierdo)."`
  * `"La condición se cumple y el límite MAX se topa con el segundo argumento (derecho)."`
  * `"La condición no se cumple, forzando la celda a su valor por defecto (ej. Sino 0)."`

---

## Excepciones y Casos de Error

Si el Excel del SII contiene una regla que es matemáticamente imposible o contradictoria (ej. `[100] > 5 .Y. [100] < 2`), el motor matemático abortará la generación de inputs y devolverá este objeto especial de diagnóstico:

```json
{
    "id_validacion": "c.99.1",
    "estado_interno": "INSATISFACTIBLE",
    "detalle": "Contradicción matemática. Revisar si la regla es lógicamente posible."
}
```