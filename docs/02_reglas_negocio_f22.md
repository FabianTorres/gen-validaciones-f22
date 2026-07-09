# Dominio y Reglas de Negocio F22

Este documento define las reglas de dominio del Formulario 22, el catálogo de validaciones del SII y el comportamiento exigido para que el motor matemático (Z3) entienda el ecosistema y genere casos de prueba estructurados.

## 1. El Ecosistema de Datos (Los Tres Universos)
Antes de evaluar una fórmula, el sistema clasifica los elementos en tres universos con reglas estrictas de manipulación:

### A. Universo Modificable (Libertad Matemática)
Son los campos editables del Formulario 22 (los únicos montos que el bot de Selenium digitará en pantalla). Z3 tiene libertad absoluta para subir, bajar o anular estos valores para cuadrar la ecuación.
* **Formatos:** Códigos F22 (ej. `[123]`) y Vectores (ej. `Vx014110`).
* **Excepción:** El código `[03]` pertenece al universo de Identidad.

### B. Universo Constante (Muros Rígidos)
Valores normativos fijados por el SII cada Año Tributario (sueldos mínimos, topes de APV, reajustes). 
* **Formatos:** Parámetros (ej. `P08`, `P736`).
* **Comportamiento Z3:** Son inmutables. Z3 no puede inventarlos; los lee de un proveedor estático y los utiliza como restricciones matemáticas absolutas.

### C. Universo de Identidad (Queries de Base de Datos)
Representan la naturaleza de quien declara (ej. Trabajador, Empresa 14 D N°3). Z3 **no usa matemáticas aquí**, sino Lógica de Conjuntos.
* **Formatos:** `TIPO{[03]}`, `SUBTIPO{[03]}`, `ATRIBUTO`.
* **Comportamiento Z3:** Actúa como un filtro. Si la regla exige `ATRIBUTO = M14A`, el motor detiene la matemática, busca en la base de datos de QA un RUT real que cumpla la condición, lo extrae y lo fija de forma permanente para el caso de prueba.

---

## 2. Diccionario de Funciones del SII
El evaluador traduce estas funciones nativas del SII a lógica pura de Z3:
* `MAX{X, Y}`: Selecciona el mayor valor entre X e Y.
* `MIN{X, Y}`: Selecciona el menor valor entre X e Y.
* `ABS{X}`: Retorna el valor absoluto de X.
* `ROUND{X}`: Redondeo aritmético estándar al entero más cercano.
* `POS{X}`: Si X > 0, retorna X. Si es negativo o cero, retorna 0.
* `NEG{X}`: Si X < 0, retorna el valor absoluto `ABS(X)`. Si es positivo o cero, retorna 0.

---

## 3. Catálogo de Validaciones y Comportamiento Estructural
El motor clasifica las familias lógicas según la obligatoriedad matemática de sus ramificaciones (el `SINO`).

### A. Validaciones Autocalculadas (Tipos A y B)
* **Comportamiento:** Celdas de solo lectura (grises). El portal calcula el monto automáticamente sin alertas.
* **Estructura:** `CÓDIGO_F22 = EXPRESIÓN_MATEMÁTICA`. 
* **Familia Lógica:** Cálculo (El `SINO` es obligatorio en condicionales internos).

### B. Cotas y Límites Numéricos (Tipos C y N)
* **Comportamiento:** Topes financieros. Protegen contra el abuso de créditos o franquicias. El Tipo C bloquea el envío; el Tipo N solo advierte.
* **Estructura:** `EXPRESIÓN (>= | <= | > | <) EXPRESIÓN_O_CONDICIONAL`.
* **Familia Lógica:** Cálculo. Los parámetros suelen actuar como techos/pisos rígidos.

### C. Implicaciones Lógicas / Condicionales Cruzados (Tipos D y E)
* **Comportamiento:** Reglas excluyentes o incluyentes amarradas al RUT (ej. "Si llenas esto, estás obligado a tener este atributo y llenar esto otro"). Son bloqueantes.
* **Estructura:** `CONDICIÓN_GATILLO => CONSECUENCIA_EXIGIDA`.
* **Familia Lógica:** Cálculo (El `SINO` es obligatorio).

### D. Asignaciones de Lógica Libre (Tipo M)
* **Comportamiento:** Asistentes invisibles de información. Resumen variables temporales (`Alfa`, `Beta`) y proponen resultados o advertencias no bloqueantes al contribuyente.
* **Estructura:** Variables declaradas flotantes, seguidas de un condicional base.
* **Familia Lógica:** Acción (El `SINO` es opcional, si no ocurre la condición, no hay acción y se asume cero).