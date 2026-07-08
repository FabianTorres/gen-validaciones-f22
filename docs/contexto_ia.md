El Ecosistema de Datos (Los "Ladrillos" del F22)
Antes de evaluar una fórmula, el sistema clasifica los elementos en tres universos estrictos:
El Universo Modificable (Códigos [XXX] y Vectores Vx01XXXX):
Concepto de Negocio: Son los campos editables del Formulario 22. Son los únicos montos que tu bot de Selenium va a digitar en la pantalla.
Rol de Z3: Tienen "libertad de movimiento". El motor matemático jugará con estos valores subiéndolos, bajándolos o poniéndolos en cero para forzar que la fórmula se cumpla o se rompa.
El Universo Constante (Parámetros PXXX, ej. P08, P174):
Concepto de Negocio: Son valores normativos fijados por el SII cada Año Tributario (sueldos mínimos, topes de APV, porcentajes de impuestos, fechas de vencimiento).
Rol de Z3: Son inmutables. Si una regla dice [123] <= P08, Z3 no puede inventar el valor de P08. Debe ir a consultar el archivo estático de parámetros, extraer su valor (ej. 1500000) y usarlo como una pared rígida (constante) en su ecuación. Z3 se verá forzado a que [123] nunca supere ese millón y medio.
El Universo de Identidad (Código [03], TIPO, SUBTIPO y ATRIBUTO):
Concepto de Negocio: Representan quién está declarando (ej. si es una empresa 14 D N°3, un trabajador dependiente, etc.).
Rol de Z3: Z3 no usa matemáticas aquí, usa Lógica de Conjuntos (Queries). Si la ecuación exige Atributo = 14D1 .Y. TIPO = 2, el motor no inventa un RUT; detiene su matemática, va al "Archivo de RUTs" predefinido por QA, filtra los que cumplan esa condición exacta, extrae ese RUT, y lo fija en el campo [03] para el caso de prueba.
Comportamiento del Negocio por Tipo de Validación
A continuación, cómo interactúan estos universos dependiendo del tipo de regla que se esté evaluando en QA:
A. Validaciones Tipo A y B (Autocalculadas)
Contexto de Negocio: Son celdas bloqueadas (grises) en el portal del SII. El contribuyente no puede digitar nada; el portal calcula el monto automáticamente.
El Rol de los Parámetros: Suelen usar parámetros como multiplicadores fijos (ej. [100] = [200] * P15).
Generación de QA: Z3 tomará el valor del Parámetro, inventará un valor para [200], y calculará el valor matemático exacto para [100]. El caso de prueba solo le dirá a Selenium: "Digita el valor en [200] y haz un Assert de que la celda [100] arrojó exactamente este otro valor".
B. Validaciones Tipo C y N (Cotas / Límites de Rango)
Contexto de Negocio: Son los topes financieros. Protegen contra franquicias mal usadas o créditos excesivos (Tipo C bloquea, Tipo N advierte).
El Rol de los Parámetros: Aquí los parámetros actúan como "Techos" o "Pisos". (ej. [123] <= MAX{[124]; P50}). El SII establece que no puedes reclamar un monto mayor al parámetro P50, a menos que tu código [124] sea aún mayor.
Generación de QA: Para certificar esto, el motor debe generar datos "caminando sobre la línea".
Happy Path: Z3 asigna a [123] un valor exactamente igual al Parámetro (Frontera Positiva).
Negative Path: Z3 asigna a [123] el valor del Parámetro + 1 peso (Frontera Negativa), lo que debe gatillar el error exacto en pantalla para que Selenium lo valide.
C. Validaciones Tipo D y E (Implicaciones Lógicas Bloqueantes)
Contexto de Negocio: Son las reglas de "Si llenas esto, estás obligado a llenar esto otro". Generalmente amarradas a la naturaleza del RUT.
El Rol del RUT y Atributos: Son el gatillo principal. Ej: [893] > 0 => Si Atributo = M14A; entonces [844] > 0 Sino 0.
Generación de QA:
Paso 1: Z3 escoge un RUT del archivo que sí tenga el atributo M14A para el código [03].
Paso 2: Z3 fuerza un monto > 0 en [893].
Paso 3: En el caso Positivo, asigna dinero a [844]. En el Negativo, lo deja en 0 para forzar el bloqueo en el portal.
Caso de Frontera: Z3 puede probar el Sino 0 yendo a buscar un RUT que NO sea M14A, demostrando que al llenar [893] no salta el error exigiendo [844].
D. Validaciones Tipo M (Asignaciones de Lógica Libre)
Contexto de Negocio: Son asistentes invisibles del SII. Recopilan variables largas, las resumen (ej. Alfa = [1] + [2]...) y al final proponen si el contribuyente debería haber pagado algo distinto.
El Rol de las Funciones (POS, NEG, ROUND): Aquí es donde abundan las reglas de "si es negativo, arrástralo como positivo para otra línea" (POS/NEG).
Generación de QA: Z3 calculará las condiciones de Alfa y Beta aplicando rígidamente las funciones del negocio (haciendo que los negativos se vuelvan 0 por culpa del POS, por ejemplo), y asegurará que las variables dependientes que se ingresen cuadren matemáticamente con esa advertencia final.