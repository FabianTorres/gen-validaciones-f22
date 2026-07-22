# Estrategia de Generación de Casos QA (Selenium)

Este documento define la metodología exacta de diseño de casos de prueba (Test Design Techniques) que el motor Z3 replica automáticamente para generar matrices de datos listas para la automatización con Selenium.

## 1. Objetivo de la Generación
El sistema no busca solo "resolver" una ecuación matemática, sino estresar el portal del SII simulando el comportamiento humano. Cada caso generado entrega un *Payload* estructurado que indica a Selenium qué datos digitar y qué comportamiento (Asserción) esperar de la interfaz gráfica.

## 2. Matrices por Tipo de Regla (Comportamiento QA)

### A. Validaciones Autocalculadas (Tipos A y B)
* **Técnica:** Partición de Equivalencia y MC/DC.
* **Comportamiento:** Z3 inventa datos válidos para las variables independientes, toma los parámetros reales, y despeja el resultado exacto. 
* **Acción Selenium:** Digitar los inputs y validar mediante un *Assert* que la celda bloqueada (gris) en el portal arroje exactamente el monto calculado por Z3. No hay mensajes de error esperados.

### B. Validaciones de Cotas y Límites (Tipos C y N)
* **Técnica:** Análisis de Valores Límite (Boundary Value Analysis).
* **Comportamiento:** El experto de fronteras (`BoundaryBuilder`) genera siempre 3 escenarios forzados:
  1. **Frontera Exacta (Happy Path):** Fuerza el límite estricto (`Lado Izq == Lado Der`). Pasa sin errores.
  2. **Frontera Superior (+1 peso):** Fuerza la ruptura por exceso (`Lado Izq == Lado Der + 1`). En reglas de máximo (`<=`), esto **debe** gatillar el cuadro rojo de error en el SII.
  3. **Frontera Inferior (-1 peso):** Fuerza el límite inferior (`Lado Izq == Lado Der - 1`). 
* **Acción Selenium:** Validar que el portal se bloquee (o advierta) únicamente en el caso que excede el límite matemático.

### C. Implicaciones y Condicionales Cruzados (Tipos D y E)
* **Técnica:** Tablas de Verdad (Decision Table Testing).
* **Comportamiento:** El experto lógico (`ImplicationBuilder`) ataca las reglas `CONDICION => CONSECUENCIA` con 3 escenarios:
  1. **Caso Cumple (Éxito):** La condición es Verdadera y la consecuencia es Verdadera.
  2. **Caso Negativo (Falla Esperada):** La condición es Verdadera, pero se fuerza a que la consecuencia sea Falsa (dejando un campo en 0). **Debe** gatillar error de bloqueo en el SII.
  3. **Caso Omisión (Ignorado):** La condición es Falsa (ej. Inyectando un RUT de otra categoría). El sistema no exige nada.
* **Acción Selenium:** Digitar el RUT específico inyectado, probar las variables y leer si la alerta se dispara cuando se rompe la consecuencia.

### D. Asignaciones de Lógica Libre (Tipo M)
* **Comportamiento:** Z3 aplica rígidamente las funciones matemáticas del negocio (ej. usar `POS` para convertir saldos negativos en cero de forma silenciosa) y asegura que las variables dependientes (`Alfa`, `Beta`) cuadren matemáticamente con la propuesta que el SII mostrará al final del formulario.

### Deduplicación Algorítmica en Caliente (Hot Deduplication)
Debido al fenómeno de "Atracción de Semilla" (donde Z3, al buscar el camino de menor resistencia para alcanzar la semilla de generación, puede superponer un caso de flujo general MCDC con un caso de frontera matemática específica), el orquestador implementa una capa de purificación final.

Antes de exportar el JSON para Selenium, el sistema captura la huella inmutable de los diccionarios de entrada de cada caso (`tuple(sorted(c["inputs"].items()))`). Si la huella de un nuevo escenario es 100% idéntica a una ya procesada en la misma regla de negocio, el caso redundante se bloquea y se elimina silenciosamente. Esto garantiza matrices de QA compactas, eficientes y libres de desgaste en la automatización web.

## Gestión de Inputs e Inyección de Datos

La generación de datos de prueba (payloads) para el bot de Selenium cuenta con mecanismos estrictos de idempotencia y sanitización para asegurar que las pruebas automatizadas sean reproducibles y libres de falsos positivos en la UI.

### 1. Inyección de Datos Deterministas (Idempotencia)
Para garantizar la reproducibilidad absoluta de los casos de prueba, el generador utiliza un enfoque 100% determinista en la asignación de RUTs, abandonando cualquier método aleatorio.
* **Catálogo Estático Ordenado:** El proveedor de datos (`RutProvider`) lee un catálogo de pruebas predefinido (`mock_ruts_qa.json`) y lo "inmoviliza" en memoria, ordenándolo por RUT. 
* **Asignación Condicional Fija:** Al requerir un RUT, el sistema evalúa las restricciones matemáticas impuestas por la regla (TIPO, SUBTIPO, Atributos Prohibidos/Requeridos) y siempre devuelve la *primera coincidencia* del arreglo inmovilizado.
* **Beneficio QA (Reducción de Clones):** Al ser determinista, dos caminos lógicos que exigen las mismas condiciones recibirán exactamente el mismo RUT. Esto permite que el filtro deduplicador de la Fase 2 intercepte la tupla idéntica `(RUT + Inputs)` y elimine escenarios redundantes, manteniendo el set de pruebas al mínimo estricto necesario.

### 2. El "Doble Candado" para Sanitización de Celdas
Dado que Z3 genera un modelo matemático complejo que incluye tanto celdas del formulario (ej. `[104]`) como variables internas de estado (ej. `E`, `IS_ATRIBUTO_M14A`), se diseñó un filtro de "doble candado" en la clase `BaseStrategy` para evitar que el bot intente digitar variables abstractas en el formulario del SII.

Para que una variable sea considerada una "celda digitable" y se exporte al bloque `"inputs"` del JSON, debe cumplir simultáneamente dos condiciones inquebrantables:
1. **Firma Estructural:** Comenzar con `[` y terminar con `]`.
2. **Firma Numérica:** Contener al menos un dígito numérico en su interior (evaluado mediante `any(c.isdigit() for c in nombre)`).

Cualquier variable abstracta transitoria (como `[ e ]` o variables booleanas autogeneradas) rebota contra este filtro y permanece de forma invisible en el backend matemático, logrando un payload limpio.