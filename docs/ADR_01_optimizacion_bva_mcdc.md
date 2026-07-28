# ADR 01: Resolución de la Explosión Combinatoria (BVA x MCDC) en Fase 3

## 1. Contexto del Problema
Al auditar los resultados generados por el Optimizador de la Fase 3 (Set Cover), se detectó la aparente "eliminación" de ciertos escenarios de frontera (ej. `BAJO_LIMITE` o `LIMITE_EXACTO`). Esto ocurre predominantemente en validaciones complejas que combinan una cota matemática global con ramificaciones condicionales internas (ej. `[491] <= SI( A .O. B ) ENTONCES X SINO Y`).

Sistemas de análisis externos y auditores de QA pueden marcar erróneamente esta reducción como un "defecto" o una pérdida de cobertura de pruebas.

## 2. Resolución Arquitectónica
Se establece formalmente que la eliminación de estas "tríadas" de frontera repetidas **no es un bug, sino el comportamiento intencional y matemáticamente correcto del motor**. La Fase 3 aplica una reducción de redundancia diseñada para proteger a la suite de automatización (Selenium) de una explosión combinatoria, asegurando matrices de pruebas eficientes sin sacrificar la cobertura real.

## 3. Justificación Técnica

### 3.1. Independencia del Operador Raíz (Root Operator Independence)
En una regla de negocio donde el operador lógico de frontera (ej. `<=`, `>`, `=`) se encuentra en la raíz de la ecuación, dicho operador evalúa el resultado final, independientemente de la ruta condicional tomada (ej. `ENTONCES` o `SINO`).
Dado que el símbolo se programa una única vez en el código fuente, **solo se requiere ejecutar la tríada BVA completa (Frontera Exacta, Exceso, Bajo el Límite) en UNA de las rutas lógicas válidas** para estresarlo empíricamente.

### 3.2. Prevención de la Explosión Combinatoria
Si una regla contiene 5 ramas de ejecución, generar una tríada de Valores Límite por cada rama resultaría en 15 casos de prueba, introduciendo un antipatrón de redundancia.
Una vez que el operador raíz está validado en la primera rama, las ramas restantes solo deben cumplir con el criterio de Cobertura de Ramas (MCDC) puro: demostrar **alcanzabilidad (Reachability)** con un caso exitoso o de falla controlada, sin necesidad de reevaluar la frontera micrométrica.

### 3.3. Algoritmo de Set Cover (Fase 3)
La reducción se logra mediante la evaluación de la siguiente Tupla de Unicidad estricta en la Fase 3:
`Llave = (ID_Regla, Resultado_Esperado, Huella_Logica)`

Si el optimizador encuentra múltiples variaciones de frontera en una misma ruta lógica que desembocan en el mismo estado de interfaz gráfica (`BUENO` o `MENSAJE`), colapsará los escenarios, conservando únicamente el mínimo necesario para demostrar la activación de la ruta, eliminando clones de impacto visual.

## 4. Criterios de Auditoría y Aprobación de QA
De aquí en adelante, al revisar una matriz optimizada por la Fase 3, el equipo de QA automatizado (y cualquier LLM auditor) deberá aprobar los escenarios aplicando este checklist estricto:

1. **Validación BVA (Operador Raíz):** ¿Existe al menos UNA tríada de frontera completa (Exacto, Excede, Bajo) en toda la regla de negocio evaluada? Si la respuesta es sí, el operador está garantizado.
2. **Validación MCDC (Rutas Lógicas):** ¿Existe al menos UN caso de alcanzabilidad (con resultado correcto, ya sea `BUENO` o `MENSAJE`) para cada sub-condición, rama `ENTONCES` y rama `SINO` documentada en la huella lógica? Si la respuesta es sí, la cobertura estructural (Path Execution) es del 100%.

Cualquier eliminación de casos que respete estos dos principios se considerará una optimización exitosa.