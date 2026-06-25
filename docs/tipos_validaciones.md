# Catálogo de Reglas de Negocio - Formulario 22 (SII)

Este documento actúa como el contrato de diseño oficial para el comportamiento sintáctico (Fase 1) y matemático (Fase 2) del proyecto `gen-validaciones-f22`.

## Estructura de Condicionales por Regla de Negocio
El Parser clasifica los `SI` en dos familias estructurales, definiendo si la rama `SINO` es matemáticamente obligatoria:

| Familia Lógica | Tipos Soportados | Naturaleza del IF | Obligatoriedad del SINO |
| :--- | :--- | :--- | :--- |
| **Cálculo** | A, B, C, D, E | Devuelve un valor o proposición para evaluar. | **Obligatorio** (Si falta, arroja error `SINO_FALTANTE`). |
| **Acción** | M, N | Ejecuta una asignación (`Suma = X`). | **Opcional** (Si es falso, se asume que no hay acción). |

---

## 1. Validaciones Autocalculadas (Tipos A y B)
* **Comportamiento en Formulario:** Son campos de solo lectura (`Read-Only`). El sistema calcula automáticamente el valor en base a una fórmula matemática. No generan mensajes de alerta al usuario.
* **Estructura Sintáctica:** `CÓDIGO_F22 = EXPRESIÓN_MATEMÁTICA` o árboles condicionales directos.
* **Objetivo de Prueba (Fase 2):** Verificar que el valor del código final coincida exactamente con el despeje de la ecuación.

## 2. Validaciones de Cotas Lógicas (Tipo C)
* **Comportamiento en Formulario:** Evaluaciones de límites financieros bloqueantes. 
* **Estructura Sintáctica:** `EXPRESIÓN_MATEMÁTICA (>= | <= | > | <) EXPRESIÓN_O_CONDICIONAL_CALCULO`
* **Objetivo de Prueba (Fase 2):** Generar escenarios de Frontera Positiva y Frontera Negativa.

## 3. Validaciones Incluyentes y Excluyentes (Tipos D y E)
* **Comportamiento en Formulario:** Implicaciones lógicas estrictas y bloqueantes.
* **Estructura Sintáctica:** `CONDICIÓN_BOOLEANA => CONSECUENCIA_O_CONDICIONAL_CALCULO`
* **Objetivo de Prueba (Fase 2):** Provocar la verdad de la condición izquierda y el quiebre de la derecha.

## 4. Validaciones de Lógica Libre No Bloqueante (Tipo M)
* **Comportamiento en Formulario:** Despliegan una advertencia o propuesta visual informativa sin bloquear. Su estructura interna suele declarar variables auxiliares arriba de la regla principal.
* **Estructura Sintáctica:** Asignaciones libres seguidas de un `CONDICIONAL_ACCION` final.
* **Objetivo de Prueba (Fase 2):** Satisfacer la igualdad de las variables declaradas bajo escenarios previstos.

## 5. Validaciones de Cotas No Bloqueantes (Tipo N)
* **Comportamiento en Formulario:** Límites numéricos que lanzan advertencias no bloqueantes.
* **Estructura Sintáctica:** `EXPRESIÓN_MATEMÁTICA (>= | <=) CONDICIONAL_ACCION`
* **Objetivo de Prueba (Fase 2):** Resolver ecuaciones considerando las variantes lógicas del extremo derecho.