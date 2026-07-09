# Arquitectura del Normalizador (Fase 1)

El Normalizador es la capa de pre-procesamiento del motor. Su objetivo es tomar la sintaxis cruda, ambigua y propensa a errores humanos proveniente del Excel del SII, y transformarla en un Árbol de Sintaxis Abstracta (AST) estandarizado, jerárquico y validado, listo para el consumo de motores lógicos.

El sistema implementa una **Arquitectura Limpia (Separation of Concerns)** dividiendo el procesamiento en 5 fases estrictas para evitar mezclar la validación sintáctica (gramática) con la validación semántica (reglas de negocio).

## Fase 1: Capa de Sanitización Inteligente (Pre-procesamiento)
Actúa antes del Parser, operando directamente sobre el texto plano para limpiar la entrada humana:
* **Conversión de Fósiles Tipográficos:** Mapea y corrige caracteres residuales de la fuente *Symbol* de Microsoft Office (ej. flechas `Þ`, `⇒` a `=>`; símbolos `¹`, `≠`, `≥`, `£` a operadores estándar `!=`, `>=`, `<=`).
* **Prevención de Tokenización Codiciosa:** Inyecta "colchones" de espacios estratégicos (ej. transforma `218. o .` a `218 .o. `) para evitar que el motor confunda puntos de separación textual con números decimales flotantes.

## Fase 2: Análisis Sintáctico Universal (Parser Lark)
El analizador léxico y sintáctico lee el texto basándose en la gramática libre de contexto, sin aplicar juicios de negocio.
* Soporta de forma nativa **Condicionales Recursivos** anidados (`SINO SI...`).
* Soporta **Cotas Encadenadas** continuas matemáticas (`A <= B <= C`).
* Define un único nodo `condicional` universal donde la rama `SINO` es *sintácticamente* opcional (dejando la rigurosidad para la Fase 4).

## Fase 3: Mutación del AST y Desugaring (Fase Intermedia)
Intervención quirúrgica y silenciosa sobre el árbol en memoria para simplificar la carga cognitiva del motor Z3 en la Fase 2:
* **Expansión de Compuertas Booleanas:** Desenreda asignaciones múltiples compactas (ej. `TIPO = 1, 2, 3`) convirtiéndolas en compuertas lógicas puras y expandidas (`TIPO = 1 .O. TIPO = 2 .O. TIPO = 3`).
* **Sanitización de Estados Nulos:** Muta el token aislado `B` al string explícito `"BLANCO"`, blindando al sistema de variables huérfanas o mal tipadas.

## Fase 4: Linter Semántico (Juez de Negocios)
Un `Transformer` de Lark que evalúa el contexto de la regla leyendo su identificador (`id_val`) y aplicando la normativa tributaria:
* **Validaciones Bloqueantes (Tipos C, D, E):** Exige estrictamente la existencia de una rama `SINO` para evitar callejones sin salida matemáticos. Si falta, interrumpe el flujo (*Fail-Fast*) y levanta un error controlado (`SINO_FALTANTE_ESTRICTO`).
* **Validaciones Informativas (Tipos M, N):** Permite el paso de condicionales de asignación o "Acción" sin rama `SINO`.

## Fase 5: Formateador Visual (Pretty-Printer)
Toma el AST validado por el Linter y reconstruye la fórmula en un texto estándar, con indentación limpia y estructura jerárquica (`SI / ENTONCES / SINO`), generando el output final destinado a la interfaz de usuario (Frontend).