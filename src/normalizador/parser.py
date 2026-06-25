from lark import Lark

GRAMATICA_F22 = r"""
// --- REGLAS SINTACTICAS (PARSER) ---
?start: validacion

// La validación ahora es un bloque que acepta reglas y variables en cualquier orden
validacion: componente_validacion+

?componente_validacion: regla_principal
                      | declaracion_variable

// --- JERARQUÍA ESTRICTA DE REGLAS DE NEGOCIO ---
?regla_principal: autocalculado       // Tipos A y B
                | implicacion         // Tipos D y E
                | cota                // Tipos C y N
                | validacion_libre    // Tipo M (Reglas sin código a la izquierda)

// 1. Tipos A y B: Autocalculados (Asignación estricta a un Código F22)
autocalculado: CODIGO "=" valor_asignado

// 2. Tipos D y E: Implicaciones lógicas (Flecha => separa proposiciones)
implicacion: "si"i? condicion_logica IMPLICA consecuencia_implicacion

?consecuencia_implicacion: condicion_logica
                         | condicional_implicacion

// SINO ESTRICTO (Para cálculos lógicos en D y E)
condicional_implicacion: "si"i condicion_logica (";"|",")? "entonces"i? (condicion_logica | expresion) ("sino"i | "si"i "no"i) (condicion_logica | expresion)

// 3. Tipos C y N: Cotas lógicas numéricas
// Aquí usamos condicional_calculo que exige SINO estrictamente
cota: expresion RELACIONAL_NUMERICO (condicional_cota | expresion | casos_trailing)

// 4. Tipo M: Lógica libre (Condicionales que ejecutan igualdades al final)
// Aquí usamos condicional_accion donde el SINO es opcional
validacion_libre: condicional_accion
                | casos_trailing

// Declaración de variables internas auxiliares (Siempre con "=")
declaracion_variable: (TEXTO | CODIGO) "=" expresion

// --- CONTENEDORES CONDICIONALES ---
?valor_asignado: casos_trailing
               | condicional_calculo
               | expresion

casos_trailing: caso_trailing+ caso_default?
caso_trailing: expresion SEPARADOR? "si"i condicion_logica
caso_default: SEPARADOR? ("sino"i | "si"i "no"i) valor_asignado
            | valor_asignado SEPARADOR? ("si"i "no"i | "sino"i)

// SINO ESTRICTO (Para calcular valores matemáticos)
condicional_calculo: "si"i condicion_logica (";"|",")? "entonces"i? expresion ("sino"i | "si"i "no"i) expresion

// SINO OPCIONAL (Para ejecutar acciones y asignaciones Tipo M)
condicional_accion: "si"i condicion_logica (";"|",")? "entonces"i? asignacion_interna (("sino"i | "si"i "no"i) asignacion_interna)?

// SINO FLEXIBLE (Exclusivo para evaluar cotas con contexto)
condicional_cota: "si"i condicion_logica (";"|",")? "entonces"i? expresion (("sino"i | "si"i "no"i) expresion)?

?asignacion_interna: valor_asignado
                   | (TEXTO | CODIGO) "=" valor_asignado -> asignacion_en_condicional

// --- CAPA LOGICA (Booleanos) ---
?condicion_logica: sub_condicion (LOGICO sub_condicion)*

?sub_condicion: comparacion
              | SIMBOLO_APERTURA condicion_logica SIMBOLO_CIERRE

// --- CAPA DE COMPARACION (Relacional Numérica) ---
?comparacion: funcion_rut RELACIONAL_NUMERICO rango_valores -> comparacion_funcion
            | "atributo"i RELACIONAL_NUMERICO rango_valores -> comparacion_atributo
            | "$" expresion -> comparacion_existencia
            | expresion RELACIONAL_NUMERICO expresion -> comparacion_simple

rango_valores: serie_numeros | SIMBOLO_APERTURA serie_numeros SIMBOLO_CIERRE
serie_numeros: (NUMERO | FORMATO_FECHA | TEXTO) ((LOGICO | SEPARADOR) (NUMERO | FORMATO_FECHA | TEXTO))*

// --- CAPA MATEMÁTICA (Numérica) ---
?expresion: termino (MATEMATICO termino)*

?termino: elemento
        | funcion_matematica
        | funcion_directa
        | funcion_rut
        | agrupacion

agrupacion: SIMBOLO_APERTURA expresion SIMBOLO_CIERRE
funcion_matematica: FUNCION SIMBOLO_APERTURA lista_argumentos SIMBOLO_CIERRE
funcion_directa: FUNCION elemento
funcion_rut: FUNCION_RUT SIMBOLO_APERTURA CODIGO SIMBOLO_CIERRE
lista_argumentos: expresion (SEPARADOR expresion)*

?elemento: CODIGO | PARAMETRO | VECTOR | FORMATO_FECHA | NUMERO | MARCA_CHECK | TEXTO 

// --- REGLAS LEXICAS (TOKENS) ---
CODIGO: /\[[^\]]+\]/
PARAMETRO: "P" NUMBER
VECTOR: "Vx" NUMBER | "Vx01" NUMBER
NUMERO: NUMBER
MARCA_CHECK: /["']*[xX]["']*/
FORMATO_FECHA: /[0-9]{1,2}\/[a-zA-Z0-9_]+/
TEXTO: /(?!(si|sino|entonces|y|o)\b)([a-zA-Z_][a-zA-Z0-9_]*|[0-9]+[a-zA-Z_][a-zA-Z0-9_]*)/i

// Separación de operadores por naturaleza
LOGICO: ".y."i | ".o."i | /\b[yo]\b/i
RELACIONAL_NUMERICO: ">=" | "<=" | ">" | "<" | "=" | "!="
IMPLICA: "=>"
MATEMATICO: "+" | "-" | "*" | "/"

FUNCION: "MIN" | "MAX" | "POS" | "NEG" | "ROUND" | "ABS"
FUNCION_RUT: "SUBTIPO"i | "ATRIBUTO"i | "TIPO"i | "MES"i

SIMBOLO_APERTURA: "{" | "("
SIMBOLO_CIERRE: "}" | ")"
SEPARADOR: ";" | ","

%import common.WS
%import common.NUMBER
%ignore WS
"""

def obtener_parser():
    return Lark(GRAMATICA_F22, start='start', parser='earley')