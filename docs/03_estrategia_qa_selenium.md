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