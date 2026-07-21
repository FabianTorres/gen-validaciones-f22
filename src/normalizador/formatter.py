from lark import exceptions, Transformer, Tree, Token
from pathlib import Path
import re
try:
    from .parser import obtener_parser
except ImportError:
    from parser import obtener_parser

# --- NUEVAS FUNCIONES DE CATÁLOGO ---
def cargar_catalogo_codigos():
    """
    Lee dinámicamente el catálogo oficial de códigos desde el archivo de texto.
    Retorna un set() con los códigos numéricos para búsquedas rápidas.
    """
    ruta_raiz = Path(__file__).parent.parent.parent
    ruta_archivo = ruta_raiz / "data" / "catalogo_codigos.txt"
    
    # El [03] (RUT) es estructural y siempre debe estar permitido
    codigos_validos = {"03"} 
    
    if ruta_archivo.exists():
        with open(ruta_archivo, "r", encoding="utf-8") as f:
            for linea in f:
                linea = linea.strip()
                if not linea or linea.startswith("CODIGO"):
                    continue
                
                partes = linea.split("|")
                if len(partes) > 0:
                    codigo_limpio = partes[0].strip()
                    if codigo_limpio:
                        codigos_validos.add(codigo_limpio)
    return codigos_validos

def validar_existencia_codigos(arbol, catalogo):
    """
    Escanea el árbol buscando Tokens de tipo 'CODIGO'.
    Si el código es numérico y no está en el catálogo, levanta un error.
    """
    codigos_faltantes = set()
    
    def buscar_codigos(nodo):
        if isinstance(nodo, Token):
            if nodo.type == 'CODIGO':
                cod_limpio = str(nodo.value).replace('[', '').replace(']', '').strip()
                # Solo validamos si es numérico (ignoramos variables como "ALFA")
                if cod_limpio.isdigit() and cod_limpio not in catalogo:
                    codigos_faltantes.add(cod_limpio)
        elif isinstance(nodo, Tree):
            for hijo in nodo.children:
                buscar_codigos(hijo)
                
    buscar_codigos(arbol)
    
    if codigos_faltantes:
        raise ValueError(f"CODIGOS_DESCONOCIDOS|{', '.join(codigos_faltantes)}")

def cargar_catalogo_parametros():
    """Lee dinámicamente el catálogo oficial de parámetros permitidos."""
    ruta_raiz = Path(__file__).parent.parent.parent
    ruta_archivo = ruta_raiz / "data" / "catalogo_parametros.txt"
    
    parametros_validos = set()
    if ruta_archivo.exists():
        with open(ruta_archivo, "r", encoding="utf-8") as f:
            for linea in f:
                linea = linea.strip()
                if not linea or linea.startswith("PARAMETRO"):
                    continue
                
                partes = linea.split("|")
                if len(partes) > 0:
                    param_limpio = partes[0].strip().upper()
                    if param_limpio:
                        parametros_validos.add(param_limpio)
    return parametros_validos

def validar_existencia_parametros(arbol, catalogo):
    """
    Escanea el árbol buscando Tokens de tipo 'PARAMETRO'.
    Si el parámetro no está en el catálogo, levanta un error para el Frontend.
    """
    parametros_faltantes = set()
    
    def buscar_parametros(nodo):
        if isinstance(nodo, Token):
            if nodo.type == 'PARAMETRO':
                param_limpio = str(nodo.value).upper().strip()
                if param_limpio not in catalogo:
                    parametros_faltantes.add(param_limpio)
        elif isinstance(nodo, Tree):
            for hijo in nodo.children:
                buscar_parametros(hijo)
                
    buscar_parametros(arbol)
    
    if parametros_faltantes:
        raise ValueError(f"PARAMETROS_DESCONOCIDOS|{', '.join(parametros_faltantes)}")

class GeneradorTextoNormalizado(Transformer):
    def __init__(self, id_val=""):
        super().__init__()
        self.id_val = id_val  # Guardamos el contexto (ej. "n.2")

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

    # Formateador para las Implicaciones de Coherencia Logica
    def implicacion(self, args):
        # La tupla ahora es [condicion_logica, IMPLICA, consecuencia_implicacion]
        condicion_previa = str(args[0])
        requisito = str(args[2])
        return f"SI SE CUMPLE CONDICION:\n{self._indentar(condicion_previa)}\n=> ENTONCES ES REQUISITO OBLIGATORIO:\n{self._indentar(requisito)}"
    
    def validacion_libre(self, args):
        # Simplemente devuelve la estructura de la condicion flotante
        return str(args[0])

    def declaracion_variable(self, args):
        # args solo trae 2 elementos: [nombre, expresion].
        nombre = str(args[0])
        val = str(args[1])
        if "\n" in val or "SI " in val:
            texto = f"{nombre} =\n{self._indentar(val)}"
        else:
            texto = f"{nombre} = {val}"
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

    def condicional(self, args):
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
        # El string "atributo" se devora, nos quedan [RELACIONAL_NUMERICO, rango_valores]
        operador = str(args[0])
        valores = str(args[1])
        return f"ATRIBUTO {operador} {valores}"
        
    def comparacion_simple(self, args):
        return " ".join(str(a) for a in args)

    def autocalculado(self, args):
        # args solo trae 2 elementos: [CODIGO, valor_asignado]. El "=" es devorado por Lark.
        codigo = str(args[0])
        val = str(args[1])
        if "\n" in val or "SI " in val:
            return f"{codigo} =\n{self._indentar(val)}"
        return f"{codigo} = {val}"

    def cota(self, args):
        izq = str(args[0])
        rel = str(args[1])
        der = str(args[2])
        if "\n" in der or "SI " in der:
            return f"{izq} {rel}\n{self._indentar(der)}"
        return f"{izq} {rel} {der}"

    def asignacion_en_condicional(self, args):
        # args solo trae 2 elementos: [nombre, valor_asignado].
        return f"{args[0]} = {args[1]}"
        
    def RELACIONAL_NUMERICO(self, token):
        val = str(token)
        return val

    def IMPLICA(self, token):
        return "=>"

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
    def VARIABLE_CORCHETE(self, token):
        # Quita corchetes y espacios, y lo pasa a mayúscula (ej. "[ e ]" -> "E")
        return str(token)[1:-1].strip().upper()

    def CODIGO(self, token):
        # Como la gramática ahora garantiza que solo entran números, 
        # solo limpiamos espacios basura que vengan del Excel.
        interior = str(token)[1:-1].strip()
        return f"[{interior}]"

    def MARCA_CHECK(self, token):
        # Fuerza que cualquier marca de verificación se estandarice visualmente a "X"
        return '"X"'

    def VECTOR(self, token):
        num = str(token).upper().replace('VX01', '').replace('VX', '')
        return f"Vx01{num.zfill(4)}"
        
    def FUNCION(self, token):
        return str(token).upper()

    def FUNCION_RUT(self, token):
        return str(token).upper()

    def LOGICO(self, token):
        val = str(token).upper()
        # Estandarizamos las conjunciones solitarias al formato matemático
        if val == 'Y': return '.Y.'
        if val == 'O': return '.O.'
        return val
        
    def TEXTO(self, token):
        val = str(token).upper()
        # Si el texto es una B solitaria, la estandarizamos como el estado BLANCO
        if val == 'B':
            return '"BLANCO"'
        return val
        
    def FORMATO_FECHA(self, token):
        return str(token).upper()

class DesenrolladorAST(Transformer):
    """
    Fase Intermedia: Bajar el Azúcar Sintáctico (Desugaring).
    Convierte 'TIPO([03]) = 2, 3' estructuralmente en 'TIPO([03]) = 2 .O. TIPO([03]) = 3'.
    Garantiza que el frontend y Z3 reciban lógica booleana estricta.
    """
    def comparacion_funcion(self, args):
        izq_tree = args[0]
        rel_token = args[1]
        rango_tree = args[2]
        
        # Extraemos la serie de números
        serie = rango_tree.children[0] if len(rango_tree.children) == 1 else rango_tree.children[1]
        
        condiciones = []
        operadores = []
        
        for child in serie.children:
            if isinstance(child, Token) and child.type in ('LOGICO', 'SEPARADOR'):
                op = '.O.' if child.type == 'SEPARADOR' or child.value in (',', ';') else str(child.value).upper()
                operadores.append(Token('LOGICO', op))
            else:
                # Armamos una comparación individual: TIPO([03]) = 2
                comp_tree = Tree('comparacion_simple', [izq_tree, rel_token, child])
                condiciones.append(comp_tree)
        
        # Si no había comas, devolvemos la condición simple intacta
        if len(condiciones) == 1:
            return condiciones[0]
            
        # Si había comas, armamos el tren de ORs (.O.)
        hijos_logica = []
        for i in range(len(condiciones)):
            hijos_logica.append(Tree('sub_condicion', [condiciones[i]]))
            if i < len(operadores):
                hijos_logica.append(operadores[i])
                
        cond_logica = Tree('condicion_logica', hijos_logica)
        # Envolvemos todo en paréntesis ( A .O. B ) para cuidar la precedencia matemática
        return Tree('sub_condicion', [Token('SIMBOLO_APERTURA', '('), cond_logica, Token('SIMBOLO_CIERRE', ')')])

    def comparacion_atributo(self, args):
        rel_token = args[0]
        rango_tree = args[1]
        
        serie = rango_tree.children[0] if len(rango_tree.children) == 1 else rango_tree.children[1]
        
        condiciones = []
        operadores = []
        
        for child in serie.children:
            if isinstance(child, Token) and child.type in ('LOGICO', 'SEPARADOR'):
                op = '.O.' if child.type == 'SEPARADOR' or child.value in (',', ';') else str(child.value).upper()
                operadores.append(Token('LOGICO', op))
            else:
                rango_singular = Tree('rango_valores', [Tree('serie_numeros', [child])])
                comp_tree = Tree('comparacion_atributo', [rel_token, rango_singular])
                condiciones.append(comp_tree)
        
        if len(condiciones) == 1:
            return condiciones[0]
            
        hijos_logica = []
        for i in range(len(condiciones)):
            hijos_logica.append(Tree('sub_condicion', [condiciones[i]]))
            if i < len(operadores):
                hijos_logica.append(operadores[i])
                
        cond_logica = Tree('condicion_logica', hijos_logica)
        return Tree('sub_condicion', [Token('SIMBOLO_APERTURA', '('), cond_logica, Token('SIMBOLO_CIERRE', ')')])

def chequear_balance(texto):
    """Algoritmo de pila para encontrar la posición exacta de un desbalance."""
    pila = []
    pares = {')': '(', '}': '{', ']': '['}
    nombres = {'(': 'paréntesis', '{': 'llave', '[': 'corchete'}
    
    for i, char in enumerate(texto):
        if char in '({[':
            pila.append((char, i))
        elif char in ')}]':
            if not pila:
                return False, i, f"Se cerró un(a) {nombres[pares[char]]} de más."
            tope, _ = pila.pop()
            if tope != pares[char]:
                return False, i, f"Se esperaba cerrar un(a) {nombres[tope]}, pero se encontró '{char}'."
                
    if pila:
        char, i = pila[0]
        return False, i, f"Quedó un(a) {nombres[char]} abierto sin cerrar."
        
    return True, -1, ""

def generar_contexto_error(texto, indice):
    """Genera un string visual apuntando al error, igual que Lark."""
    inicio = max(0, indice - 20)
    fin = min(len(texto), indice + 20)
    fragmento = texto[inicio:fin]
    apuntador = " " * (indice - inicio) + "^"
    return f"{fragmento}\n{apuntador}"

class LinterSemantico(Transformer):
    """
    Juez de Reglas de Negocio. Recorre el AST y evalúa contextualmente
    si la sintaxis cumple con la normativa del SII según el ID.
    """
    def __init__(self, id_val=""):
        super().__init__()
        self.id_val = id_val

    def condicional(self, args):
        # Si el condicional no tiene SINO (menos de 3 argumentos)
        if len(args) < 3:
            tipo = self.id_val.strip().split('.')[0].lower() if self.id_val else ""
            # Si es un Cálculo (Cota, o Implicación D/E), es bloqueante.
            if tipo in ['c', 'd', 'e']:
                raise ValueError("SINO_FALTANTE_ESTRICTO")
        # Retorna el árbol intacto para no dañar la estructura
        return Tree('condicional', args)    

def normalizar_y_validar(texto_crudo, id_val=""):
    """
    API READY: Ahora retorna un diccionario con estructura estándar para el Frontend.
    """
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
    texto_limpio = texto_limpio.replace(',y.', '.y.').replace(',Y.', '.y.')
    texto_limpio = texto_limpio.replace(',o.', '.o.').replace(',O.', '.o.')
    texto_limpio = texto_limpio.replace('""', '"')
    texto_limpio = re.sub(r'\.\s*([yYoO])\s*\.', r' .\1. ', texto_limpio)
    
    # 1. Validación de Balance con posición exacta
    balanceado, indice_error, msg_desbalance = chequear_balance(texto_limpio)
    if not balanceado:
        contexto = generar_contexto_error(texto_limpio, indice_error)
        return {
            "estado": "ERROR",
            "tipo_error": "DESBALANCE_SIMBOLOS",
            "mensaje": f"❌ BLOQUEO: Error de apertura/cierre.\nDetalle: {msg_desbalance}\n\n{contexto}",
            "arbol": None
        }

    # 2. Análisis Sintáctico (Lark)
    try:
        # FASE 1: El Parser lee el texto crudo (Sin juzgar)
        arbol_crudo = parser.parse(texto_limpio)
        
        # FASE 2: Desenrollado de azúcar sintáctico
        arbol_desenrollado = DesenrolladorAST().transform(arbol_crudo)
        
        # FASE 3: Sanitización de Estados Nulos
        def sanitizar_ast(arbol):
            for i, hijo in enumerate(arbol.children):
                if isinstance(hijo, Tree):
                    sanitizar_ast(hijo)
                elif isinstance(hijo, Token) and hijo.type == 'TEXTO' and hijo.value.upper() == 'B':
                    arbol.children[i] = Token('TEXTO', 'BLANCO')
        sanitizar_ast(arbol_desenrollado)
        
        # ---> NUEVA BARRERA: Validar contra el Catálogo <---
        catalogo_vigente = cargar_catalogo_codigos()
        validar_existencia_codigos(arbol_desenrollado, catalogo_vigente)

        catalogo_params = cargar_catalogo_parametros()
        validar_existencia_parametros(arbol_desenrollado, catalogo_params)
        
        # FASE 4: Linter Semántico (El Juez levanta error si falta un SINO obligatorio)
        LinterSemantico(id_val).transform(arbol_desenrollado)
        
        # FASE 5: Formateador Visual (El Pintor solo dibuja lo que sobrevivió al juez)
        texto_formateado = GeneradorTextoNormalizado(id_val).transform(arbol_desenrollado)

        return {
            "estado": "EXITO",
            "texto_formateado": texto_formateado,
            "arbol": arbol_desenrollado 
        }

    # ATRAMPAMOS EL VEREDICTO DEL JUEZ Y LA BARRERA DE CÓDIGOS
    except (ValueError, exceptions.VisitError) as e:
        error_msg = str(e)
        if isinstance(e, exceptions.VisitError):
            error_msg = str(e.orig_exc)
            
        # ---> NUEVA CAPTURA DE ERROR PARA EL FRONTEND <---
        if error_msg.startswith("CODIGOS_DESCONOCIDOS|"):
            faltantes = error_msg.split('|')[1]
            return {
                "estado": "ERROR",
                "tipo_error": "CODIGO_NO_CATALOGADO",
                "mensaje": f"❌ BLOQUEO: Códigos no reconocidos.\nDetalle: La fórmula contiene códigos que no existen en el Catálogo Oficial del F22: [{faltantes}].\nSugerencia: Revisa si hay un error de tipeo en el Excel.",
                "arbol": None
            }

        if error_msg.startswith("PARAMETROS_DESCONOCIDOS|"):
            faltantes = error_msg.split('|')[1]
            return {
                "estado": "ERROR",
                "tipo_error": "PARAMETRO_NO_CATALOGADO",
                "mensaje": f"❌ BLOQUEO: Parámetros no reconocidos.\nDetalle: La fórmula contiene parámetros que no existen en el Catálogo Oficial del F22: [{faltantes}].\nSugerencia: Revisa si hay un error de tipeo en el Excel.",
                "arbol": None
            }
            
        if error_msg == "SINO_FALTANTE_ESTRICTO":
            return {
                "estado": "ERROR",
                "tipo_error": "SINO_FALTANTE",
                "mensaje": "❌ BLOQUEO: Condicional incompleto.\nDetalle: Las reglas de validación bloqueantes (Tipos C, D y E) exigen obligatoriamente indicar qué ocurre si la condición es falsa.\nSugerencia: Agrega 'Sino 0' al final de tu fórmula.",
                "arbol": None
            }
        raise e

    except exceptions.UnexpectedEOF as e:
        esperados = ", ".join(e.expected) if hasattr(e, 'expected') and e.expected else ""
        
        # Interceptamos si la máquina se estrelló porque esperaba un SINO
        if "SINO" in esperados.upper() or "SI" in esperados.upper():
            return {
                "estado": "ERROR",
                "tipo_error": "SINO_FALTANTE",
                "mensaje": "❌ BLOQUEO: Condicional incompleto.\nDetalle: Toda regla que inicie con un 'SI', debe indicar qué ocurre cuando la condición es falsa.\nSugerencia: Agrega 'Sino 0' al final de tu fórmula si no hay otra condición.",
                "arbol": None
            }
            
        mensaje_error = (
            "❌ BLOQUEO: Fin de fórmula inesperado (Incompleta).\n"
            "Detalle: La validación termina de forma abrupta y la regla quedó abierta.\n"
            f"Pista del sistema: Se esperaba encontrar -> {esperados}"
        )
        return {
            "estado": "ERROR",
            "tipo_error": "FORMULA_INCOMPLETA",
            "mensaje": mensaje_error,
            "arbol": None
        }
        
    except exceptions.UnexpectedCharacters as e:
        contexto = e.get_context(texto_limpio)
        return {
            "estado": "ERROR",
            "tipo_error": "CARACTER_INVALIDO",
            "mensaje": f"❌ BLOQUEO: Carácter inválido o palabra mal escrita.\nDetalle: El sistema no reconoce el símbolo apuntado por la flecha.\n\n{contexto}",
            "arbol": None
        }
        
    except exceptions.UnexpectedToken as e:
        contexto = e.get_context(texto_limpio)
        esperados_lista = [str(x) for x in e.expected]
        
        # Doble validación: Si puso otra palabra en lugar del SINO esperado
        if any("SINO" in esp.upper() or "SI" in esp.upper() for esp in esperados_lista):
            return {
                "estado": "ERROR",
                "tipo_error": "SINO_FALTANTE",
                "mensaje": "❌ BLOQUEO: Condicional incompleto.\nDetalle: Toda regla que inicie con un 'SI', debe indicar qué ocurre cuando la condición es falsa.\nSugerencia: Asegúrate de usar 'Sino' o 'Sino 0' para cerrar la regla.",
                "arbol": None
            }

        traduccion_errores = {
            "SEPARADOR": "Falta un punto y coma ';' o coma ',' separando los argumentos.",
            "FUNCION": "Problema con la función. Se esperaba MIN, MAX, POS, NEG, ROUND o ABS.",
            "CODIGO": "Se esperaba un Código F22 entre corchetes (ej. [123]).",
            "RELACIONAL_NUMERICO": "Falta un operador matemático de comparación (=, >, <, >=, <=).",
            "IMPLICA": "Se esperaba una flecha de implicación (=>).",
            "MATEMATICO": "Problema matemático. Se esperaba un signo (+, -, *, /).",
            "LOGICO": "Falta un conector lógico (.Y. o .O.).",
            "NUMERO": "Se esperaba un número.",
            "TEXTO": "Se esperaba una palabra clave válida."
        }
        
        mensajes_especificos = [traduccion_errores[esp] for esp in e.expected if esp in traduccion_errores]
        
        if mensajes_especificos:
            detalle = "Problema detectado: " + " O bien, ".join(list(set(mensajes_especificos)))
        else:
            detalle = f"Error de estructura. El sistema esperaba encontrar: {', '.join(e.expected)}"

        return {
            "estado": "ERROR",
            "tipo_error": "ERROR_SINTAXIS",
            "mensaje": f"❌ BLOQUEO: Error de Sintaxis.\nDetalle: {detalle}\n\n{contexto}",
            "arbol": None
        }