# Estrategia de Generación de Casos QA (Fase 2 - Z3)

Este documento define la metodología exacta de diseño de casos de prueba (Test Design Techniques) que el motor Z3 debe replicar automáticamente para alimentar al bot de Selenium en el F22.

## 1. Validaciones Autocalculadas con Funciones (Tipos A y B)
**Técnicas aplicadas:** Partición de Equivalencia y MC/DC (Modified Condition/Decision Coverage).

### Ejemplo de Negocio: `[494] = MIN{ P08 * [547] ; P42 } ; si [465] = 0 .y. TIPO{[03]}=1`
El motor Z3 debe desglosar las reglas que contienen topes (MIN/MAX) y compuertas lógicas (AND/OR) en los siguientes escenarios obligatorios:

* **Caso 1 (Frontera de Tope / Techo):**
  * *Acción Z3:* Forzar que el cálculo interno (`P08 * [547]`) supere el parámetro `P42`.
  * *Resultado esperado:* El código `[494]` debe ser igual al tope `P42`.
* **Caso 2 (Cálculo Real / Bajo el Techo):**
  * *Acción Z3:* Forzar que el cálculo interno sea menor al tope `P42`.
  * *Resultado esperado:* El código `[494]` asume el valor exacto del cálculo.
* **Caso 3 (Quiebre de Condición de Valor - Flujo Negativo):**
  * *Acción Z3:* Forzar la ruptura del gatillo matemático inyectando `[465] > 0`.
  * *Resultado esperado:* La fórmula se anula, ejecutando el `SINO 0` implícito (`[494] = 0`).
* **Caso 4 (Quiebre de Condición de Identidad - Flujo Negativo):**
  * *Acción Z3:* Buscar un RUT en la base de datos cuyo `TIPO` sea distinto de `1`.
  * *Resultado esperado:* La validación colapsa desde la base, arrojando `[494] = 0`.

*(Nota para OR lógicos: Si el gatillo usa `.O.` en lugar de `.Y.`, Z3 debe iterar un caso positivo independiente por cada variable verdadera para garantizar la cobertura total).*

## 2. Validaciones de Cotas y Límites (Tipos C y N)
**Técnicas aplicadas:** Análisis de Valores Límite (Boundary Value Analysis).

### Ejemplo de Negocio: `[1639] <= SI ( TIPO([03]) = 1 ) ENTONCES ROUND( [1608] * 0.5 ) SINO 0`
El motor Z3 no evalúa si la regla "es correcta", sino que genera los datos para comprobar que el portal del SII aplique el límite correctamente. Debe iterar 4 escenarios:

* **Caso 1 (El Límite Exacto / Frontera Positiva):**
  * *Acción Z3:* Resuelve la ecuación reemplazando el operador original por un igual (`[1639] == ROUND(...)`). 
  * *Objetivo QA:* Comprobar que el sistema soporta el valor límite exacto sin arrojar error.
* **Caso 2 (Zona Segura / Happy Path):**
  * *Acción Z3:* Resuelve reemplazando con un operador de holgura (`[1639] < ROUND(...)`).
* **Caso 3 (Gatillo Falso / Comprobación de SINO):**
  * *Acción Z3:* Fuerza un RUT de Tipo distinto a 1. El lado derecho se vuelve `0`. Para que no arroje error, Z3 fuerza `[1639] = 0`.
* **Caso 4 (El Quiebre / Frontera Negativa - CASO DE RECHAZO):**
  * *Acción Z3:* Inyecta datos que rompan matemáticamente el límite invirtiendo el operador (`[1639] > ROUND(...)`).
  * *Objetivo QA:* Entregar estos datos a Selenium para certificar que **sí aparezca** el cuadro de error rojo en la web.