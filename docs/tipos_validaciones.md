# Catálogo de Reglas de Negocio - Formulario 22 (SII)

Este documento actúa como el contrato de diseño oficial para el comportamiento sintáctico (Fase 1) y matemático (Fase 2) del proyecto `gen-validaciones-f22`.

## 1. Validaciones Autocalculadas (Tipos A y B)
* **Comportamiento en Formulario:** Son campos de solo lectura (`Read-Only`). El sistema calcula automáticamente el valor en base a una fórmula matemática. No generan mensajes de alerta al usuario porque el usuario no puede digitar en ellos.
* **Estructura Sintáctica:** `CÓDIGO_F22 = EXPRESIÓN_MATEMÁTICA` o árboles condicionales directos.
* **Objetivo de Prueba (Fase 2):** Verificar que el valor del código final coincida exactamente con el despeje de la ecuación matemática.

## 2. Validaciones de Cotas Lógicas (Tipo C)
* **Comportamiento en Formulario:** Son evaluaciones de límites financieros bloqueantes. Si la combinación de códigos de la izquierda no respeta el umbral impuesto por la derecha, el formulario se congela y despliega un error en pantalla.
* **Estructura Sintáctica:** `EXPRESIÓN_MATEMÁTICA (>= | <= | > | <) EXPRESIÓN_O_CONDICIONAL`
* **Objetivo de Prueba (Fase 2):** Generar escenarios en la frontera exacta del límite (Frontera Positiva) y escenarios inmediatamente fuera del límite (Frontera Negativa) para forzar la activación del mensaje de bloqueo.

## 3. Validaciones Incluyentes y Excluyentes (Tipos D y E)
* **Comportamiento en Formulario:** Son implicaciones lógicas estrictas y bloqueantes. Si se cumple una condición inicial en un código (normalmente que sea mayor a 0), se activa la obligación absoluta de cumplir una segunda condición o restricción en otros códigos del formulario.
* **Estructura Sintáctica:** `CONDICIÓN_BOOLEANA => CONSECUENCIA_O_CONDICIONAL`
* **Objetivo de Prueba (Fase 2):** * *Caso Positivo:* Provocar que la condición izquierda sea verdadera y la derecha también lo sea.
    * *Caso Negativo:* Forzar el escenario de quiebre donde la condición izquierda se cumple, pero la consecuencia derecha se viola, activando el linter del SII.

## 4. Validaciones de Lógica Libre No Bloqueante (Tipo M)
* **Comportamiento en Formulario:** Permiten al usuario continuar con el envío del F22, pero despliegan una advertencia o propuesta visual informativa. Su estructura interna suele declarar variables auxiliares arriba de la regla para simplificar la lectura de la condición principal al final.
* **Estructura Sintáctica:** Una serie de asignaciones libres seguidas de una consecuencia condicional final (ej. `VARIABLE = EXPRESIÓN ... ENTONCES VARIABLE_A = VARIABLE_B`).
* **Objetivo de Prueba (Fase 2):** Satisfacer la igualdad de las variables declaradas bajo los escenarios lógicos previstos por el negocio.

## 5. Validaciones de Cotas No Bloqueantes (Tipo N)
* **Comportamiento en Formulario:** Funcionan con la misma estructura matemática de límites que las validaciones Tipo C (Cotas), pero lanzan mensajes informativos o de advertencia que no impiden el envío del formulario.
* **Estructura Sintáctica:** `EXPRESIÓN_MATEMÁTICA (>= | <=) CONDICIONAL_COMPLETO`
* **Objetivo de Prueba (Fase 2):** Resolver las ecuaciones considerando las variantes lógicas del condicional del extremo derecho para hallar los vectores de prueba límite.