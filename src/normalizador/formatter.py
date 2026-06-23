from lark import exceptions, Transformer
import re
try:
    from .parser import obtener_parser
except ImportError:
    from parser import obtener_parser

class GeneradorTextoNormalizado(Transformer):
    def _indentar(self, texto):
        return "\n".join("  " + linea for linea in texto.split("\n"))

    def validacion(self, args):
        # Separamos la regla principal de las declaraciones de variables
        reglas = [str(a) for a in args if not (isinstance(a, tuple) and a[0] == "var")]
        vars_decl = [a[1] for a in args if isinstance(a, tuple) and a[0] == "var"]
        
        # Unimos las reglas principales
        res = "\n\n".join(reglas)
        
        # Inyectamos todas las variables al final
        for v in vars_decl:
            res += f"\nDONDE {v}"
        return res

    def asignacion(self, args):
        val = str(args[2])
        if "\n" in val or "SI " in val:
            return f"{args[0]} {args[1]}\n{self._indentar(val)}"
        return f"{args[0]} {args[1]} {val}"

    # Formateador para las Implicaciones de Coherencia Logica
    def implicacion(self, args):
        condicion_previa = str(args[0])
        requisito = str(args[1])
        return f"SI SE CUMPLE CONDICION:\n{self._indentar(condicion_previa)}\n=> ENTONCES ES REQUISITO OBLIGATORIO:\n{self._indentar(requisito)}"

    def validacion_libre(self, args):
        # Simplemente devuelve la estructura de la condicion flotante
        return str(args[0])

    def declaracion_variable(self, args):
        val = str(args[2])
        if "\n" in val or "SI " in val:
            texto = f"{args[0]} {args[1]}\n{self._indentar(val)}"
        else:
            texto = f"{args[0]} {args[1]} {val}"
        # Devolvemos una tupla para que el metodo "validacion" sepa que esto es una variable
        return ("var", texto)

    def valor_asignado(self, args):
        return " ".join(str(a) for a in args if a)

    def casos_trailing(self, args):
        return "\n".join(str(a) for a in args)

    def caso_trailing(self, args):
        expresion = args[0]
        condicion = args[-1]
        return f"SI {condicion} ENTONCES {expresion}"

    def caso_default(self, args):
        valor = next(a for a in args if getattr(a, 'type', '') != 'SEPARADOR')
        return f"SINO {valor}"

    def condicional_leading(self, args):
        res = f"SI {args[0]}\nENTONCES {args[1]}"
        if len(args) == 3:
            sino_val = str(args[2])
            if sino_val.startswith("SI"):
                res += f"\nSINO\n{self._indentar(sino_val)}"
            else:
                res += f"\nSINO {sino_val}"
        return res

    def condicional_implicacion(self, args):
        res = f"SI {args[0]}\nENTONCES {args[1]}"
        if len(args) == 3:
            sino_val = str(args[2])
            if sino_val.startswith("SI"):
                res += f"\nSINO\n{self._indentar(sino_val)}"
            else:
                res += f"\nSINO {sino_val}"
        return res

    def condicion_logica(self, args):
        return " ".join(str(a) for a in args)

    def sub_condicion(self, args):
        if len(args) == 3:
            return f"( {args[1]} )"
        return args[0]

    def comparacion(self, args):
        return " ".join(str(a) for a in args)
        
    def comparacion_atributo(self, args):
        return f"ATRIBUTO = {args[0]}"
        
    def comparacion_simple(self, args):
        return " ".join(str(a) for a in args)

    def comparacion_condicional(self, args):
        izq = str(args[0])
        rel = str(args[1])
        cond = str(args[2])
        # Indentamos el bloque condicional para que la jerarquía visual sea perfecta
        return f"{izq} {rel}\n{self._indentar(cond)}"

    def rango_valores(self, args):
        if len(args) == 3:
            return str(args[1])
        return str(args[0])

    def serie_numeros(self, args):
        res = []
        for a in args:
            val = str(a).upper()
            if val == ',' or val == ';':
                res.append('.O.')
            else:
                res.append(val)
                
        resultado_unido = " ".join(res)

        if ".O." in resultado_unido or ".Y." in resultado_unido:
            return f"( {resultado_unido} )"
            
        return resultado_unido

    def expresion(self, args):
        return " ".join(str(a) for a in args)

    def agrupacion(self, args):
        return f"( {args[1]} )"

    def funcion_matematica(self, args):
        func = str(args[0]).upper()
        args_list = str(args[2])
        if func == "ROUND" and ";" not in args_list:
            args_list += " ; 0"
        return f"{func}( {args_list} )"

    def funcion_directa(self, args):
        func = str(args[0]).upper()
        elemento = str(args[1])
        if func == "ROUND":
            return f"{func}( {elemento} ; 0 )"
        return f"{func}( {elemento} )"

    def funcion_rut(self, args):
        func = args[0]
        codigo = args[2]
        return f"{func}( {codigo} )"

    def lista_argumentos(self, args):
        elementos = [str(arg) for arg in args if getattr(arg, 'type', '') != 'SEPARADOR']
        return " ; ".join(elementos)

    # --- TOKENS ---
    def CODIGO(self, token):
        # Extrae el interior, quita espacios y pasa a mayúscula
        interior = str(token)[1:-1].strip().upper()
        
        # Si es un número puro (ej. "750"), mantiene los corchetes
        if interior.isdigit():
            return f"[{interior}]"
            
        # Si contiene letras (ej. "M" o "J"), es variable en memoria y va sin corchetes
        return f"{interior}"

    def VECTOR(self, token):
        num = str(token).upper().replace('VX01', '').replace('VX', '')
        return f"Vx01{num.zfill(4)}"
        
    def FUNCION(self, token):
        return str(token).upper()

    def FUNCION_RUT(self, token):
        return str(token).upper()

    def LOGICO(self, token):
        return str(token).upper()
        
    def TEXTO(self, token):
        return str(token).upper()
        
    def FORMATO_FECHA(self, token):
        return str(token).upper()
        
    def RELACIONAL(self, token):
        val = str(token)
        if val == "=>": return ">="
        if val == "=<": return "<="
        if val == "£": return "<="
        if val == "≤": return "<="
        if val == "≥": return ">="
        if val == "≠": return "!="
        return val

def normalizar_y_validar(texto_crudo):
    parser = obtener_parser()
    
    texto_limpio = texto_crudo.replace('\xa0', ' ').replace('\u200b', '').replace('\t', ' ')
    texto_limpio = texto_limpio.replace('}]', ']}')
    texto_limpio = texto_limpio.replace('Þ', '=>').replace('⇒', '=>')
    texto_limpio = texto_limpio.replace('¹', '!=').replace('≠', '!=')
    texto_limpio = texto_limpio.replace('≥', '>=').replace('≤', '<=')
    texto_limpio = texto_limpio.replace('³', '>=').replace('£', '<=')
    texto_limpio = re.sub(r'_{2,}', ' ', texto_limpio)
    texto_limpio = texto_limpio.replace('.y,', '.y.').replace('.Y,', '.y.')
    texto_limpio = texto_limpio.replace('.o,', '.o.').replace('.O,', '.o.')
    
    if texto_limpio.count('(') != texto_limpio.count(')'):
        return False, "❌ BLOQUEO: Desbalance de paréntesis."
    if texto_limpio.count('{') != texto_limpio.count('}'):
        return False, "❌ BLOQUEO: Desbalance de llaves."
    if texto_limpio.count('[') != texto_limpio.count(']'):
        return False, "❌ BLOQUEO: Desbalance de corchetes."

    try:
        arbol = parser.parse(texto_limpio)
        texto_formateado = GeneradorTextoNormalizado().transform(arbol)
        return True, texto_formateado

    except exceptions.UnexpectedEOF as e:
        # Intentamos extraer qué esperaba la máquina para dar una pista extra
        esperados = ", ".join(e.expected) if hasattr(e, 'expected') and e.expected else "elementos adicionales"
        
        mensaje_error = (
            "❌ BLOQUEO: Fin de fórmula inesperado (Incompleta).\n\n"
            "Detalle: La validación termina de forma abrupta y la regla quedó abierta. "
            "Esto suele ocurrir por dos motivos:\n"
            "1. La fórmula está cortada literalmente (ej. termina en un signo matemático o lógico).\n"
            "2. Falta asignar explícitamente el resultado a un código F22 al final de un condicional.\n\n"
            f"Pista del sistema: Se esperaba encontrar -> {esperados}"
        )
        return False, mensaje_error
    except exceptions.UnexpectedCharacters as e:
        contexto = e.get_context(texto_limpio)
        return False, f"❌ BLOQUEO: Carácter inválido o palabra mal escrita.\n\n{contexto}Detalle: El sistema no reconoce el símbolo o palabra apuntada por la flecha."
        
    except exceptions.UnexpectedToken as e:
        contexto = e.get_context(texto_limpio)
        traduccion_errores = {
            "SEPARADOR": "Falta un punto y coma ';' o coma ',' separando los argumentos.",
            "FUNCION": "Problema con la función. Se esperaba MIN, MAX, POS, NEG o ROUND.",
            "CODIGO": "Se esperaba un Código F22 entre corchetes (ej. [123]).",
            "RELACIONAL": "Falta un operador de comparación (=, >, <, >=, <=).",
            "MATEMATICO": "Problema matemático. Se esperaba un signo (+, -, *, /).",
            "LOGICO": "Falta un conector lógico (.Y. o .O.).",
            "NUMERO": "Se esperaba un número.",
            "PALABRA_CLAVE": "Se esperaba una palabra clave (SI, SINO, ENTONCES)."
        }
        
        mensajes_especificos = []
        for esperado in e.expected:
            if esperado in traduccion_errores:
                mensajes_especificos.append(traduccion_errores[esperado])
                
        if mensajes_especificos:
            motivos = list(set(mensajes_especificos))
            detalle = "Problema detectado: " + " O bien, ".join(motivos)
        else:
            esperados_crudos = ", ".join(e.expected)
            detalle = f"Error de estructura. El sistema esperaba encontrar: {esperados_crudos}"

        return False, f"❌ BLOQUEO: Error de Sintaxis.\n\n{contexto}Detalle: {detalle}"