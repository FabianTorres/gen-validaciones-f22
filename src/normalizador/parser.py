from lark import Lark

GRAMATICA_F22 = r"""
// --- REGLAS SINTACTICAS (PARSER) ---
?start: validacion

// La validación ahora es un bloque que acepta reglas y variables en cualquier orden
validacion: componente_validacion+

?componente_validacion: regla_principal
                      | declaracion_variable

?regla_principal: asignacion
                | implicacion
                | validacion_libre

asignacion: CODIGO RELACIONAL valor_asignado

implicacion: "si"i? condicion_logica "=>" consecuencia_implicacion

?consecuencia_implicacion: condicion_logica
                         | condicional_implicacion

condicional_implicacion: "si"i condicion_logica (";"|",")? "entonces"i? condicion_logica ("sino"i condicion_logica)?

// NUEVA REGLA: Para validaciones que no asignan a un código, sino que son reglas lógicas flotantes
validacion_libre: condicional_leading
                | comparacion

// Le damos prioridad (.2) para que atrape siempre las asignaciones de variables como "Suma ="
declaracion_variable: (TEXTO | CODIGO) "=" expresion

?valor_asignado: casos_trailing
               | condicional_leading
               | comparacion   // NUEVO: Permite que el valor asignado sea una comparación (ej: suma = alfa)
               | expresion

casos_trailing: caso_trailing+ caso_default?

caso_trailing: expresion SEPARADOR? "si"i condicion_logica

caso_default: SEPARADOR? ("sino"i | "si"i "no"i) valor_asignado
            | valor_asignado SEPARADOR? ("si"i "no"i | "sino"i)

condicional_leading: "si"i condicion_logica (";"|",")? "entonces"i? valor_asignado ("sino"i valor_asignado)?

?condicion_logica: sub_condicion (LOGICO sub_condicion)*

?sub_condicion: comparacion
              | SIMBOLO_APERTURA condicion_logica SIMBOLO_CIERRE

// Se flexibiliza la comparación de atributos para aceptar series completas (.o. / .y. / comas)
?comparacion: funcion_rut RELACIONAL rango_valores
            | "atributo"i "=" rango_valores -> comparacion_atributo
            | "$" expresion -> comparacion_existencia
            | expresion (RELACIONAL expresion)* RELACIONAL condicional_leading -> comparacion_condicional
            | expresion (RELACIONAL expresion)+ -> comparacion_simple

rango_valores: serie_numeros | SIMBOLO_APERTURA serie_numeros SIMBOLO_CIERRE

serie_numeros: (NUMERO | FORMATO_FECHA | TEXTO) ((LOGICO | SEPARADOR) (NUMERO | FORMATO_FECHA | TEXTO))*

?expresion: termino (MATEMATICO termino)*

?termino: elemento
        | funcion_matematica
        | funcion_directa
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
TEXTO: /(?i)(?!(si|sino|entonces)\b)([a-zA-Z_][a-zA-Z0-9_]*|[0-9]+[a-zA-Z_][a-zA-Z0-9_]*)/

LOGICO: ".y."i | ".o."i
RELACIONAL: ">=" | "<=" | ">" | "<" | "=" | "!=" | "=>" | "=<" | "£" | "≤" | "≥" | "≠"
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