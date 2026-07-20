import z3
from lark import Tree, Token
from src.generador.z3_core import MotorZ3

class EvaluadorAST:
    def __init__(self, motor_z3: MotorZ3):
        self.motor = motor_z3

    # def evaluar(self, nodo):
    #     # Inicializamos el nivel de sangría para que se vea como un árbol en consola
    #     self.nivel_debug = getattr(self, 'nivel_debug', 0)
    #     sangria = "  " * self.nivel_debug
        
    #     if isinstance(nodo, Token):
    #         # 1. Ejecutamos la conversión normal
    #         resultado = self._evaluar_token(nodo)
            
    #         # 2. EL ESPÍA: Imprimimos qué entregó Lark y qué devolvió la Fase 2
    #         print(f"{sangria}LARK [Token: {nodo.type}] '{nodo.value}' ---> FASE 2: {type(resultado)} ({resultado})")
    #         return resultado
            
    #     if isinstance(nodo, Tree):
    #         print(f"{sangria}ENTRANDO NODO: {nodo.data}")
    #         self.nivel_debug += 1
            
    #         metodo = getattr(self, f"_{nodo.data}", self._evaluar_default)
    #         try:
    #             resultado = metodo(nodo)
    #         except Exception as e:
    #             # Si explota, sabremos exactamente en qué nodo ocurrió
    #             print(f"{sangria}💥 EXPLOSIÓN MATEMÁTICA EN EL NODO: {nodo.data} 💥")
    #             self.nivel_debug -= 1
    #             raise e
                
    #         self.nivel_debug -= 1
    #         return resultado
            
    #     return nodo

    def evaluar(self, nodo):
        """Punto de entrada principal. Recorre recursivamente el AST de Lark."""
        if isinstance(nodo, Token):
            return self._evaluar_token(nodo)
            
        if isinstance(nodo, Tree):
            metodo = getattr(self, f"_{nodo.data}", self._evaluar_default)
            return metodo(nodo)
            
        return nodo

    def _evaluar_default(self, nodo):
        raise NotImplementedError(f"Falta implementar la evaluación en Z3 para la regla AST: '{nodo.data}'")

    # --- 1. EVALUACION DE TOKENS
    def _evaluar_token(self, token):
        tipo = token.type
        valor = str(token)

        # 1. Limpieza absoluta inicial
        valor_limpio = valor.replace('"', '').strip().upper()

        # 2. ESCUDO INTERCEPTOR DE CONSTANTES Y PARAMETROS
        if valor_limpio == 'X':
            return 1
        if valor_limpio == 'BLANCO':
            return 0

        # 3. EVALUACIÓN ESTÁNDAR
        if tipo in ('CODIGO', 'VECTOR', 'PARAMETRO'):
            nombre_var = f"[{valor_limpio}]" if tipo == 'CODIGO' and not valor_limpio.startswith('[') else valor_limpio
            return self.motor.obtener_o_crear_variable(nombre_var)
            
        elif tipo == 'NUMERO':
            return float(valor) if '.' in valor else int(valor)
            
        elif tipo == 'TEXTO':
            # Textos libres que no son X ni BLANCO se vuelven variables (ej: "ALFA")
            return self.motor.obtener_o_crear_variable(valor_limpio)
            
        # 4. OPERADORES (Los únicos que tienen permitido retornar strings puros)
        elif tipo in (
            'MATEMATICO', 'RELACIONAL_NUMERICO', 'LOGICO', 'IMPLICA', 
            'SEPARADOR', 'SIMBOLO_APERTURA', 'SIMBOLO_CIERRE', 
            'FUNCION', 'FUNCION_RUT', 'MARCA_CHECK', 'FORMATO_FECHA'
        ):
            return valor_limpio
            
        # 5. FALLBACK DE SEGURIDAD
        if valor_limpio.isalnum():
             return self.motor.obtener_o_crear_variable(valor_limpio)
            
        raise ValueError(f"Token no reconocido por el Evaluador Z3: {tipo} -> {valor}")

    # --- 2. REGLAS PRINCIPALES DE NEGOCIO ---
    
    def _validacion(self, nodo):
        restricciones = [self.evaluar(h) for h in nodo.children]
        return z3.And(*restricciones)

    def _autocalculado(self, nodo):
        izq = self.evaluar(nodo.children[0])
        der = self.evaluar(nodo.children[-1])
        return izq == der

    def _cota(self, nodo):
        izq = self.evaluar(nodo.children[0])
        operador = self.evaluar(nodo.children[1])
        der = self.evaluar(nodo.children[2])

        if operador == '>':  return izq > der
        if operador == '<':  return izq < der
        if operador == '>=': return izq >= der
        if operador == '<=': return izq <= der
        if operador == '=':  return izq == der
        if operador == '!=': return izq != der
        raise ValueError(f"Operador de cota desconocido: {operador}")

    def _implicacion(self, nodo):
        condicion = self.evaluar(nodo.children[0])
        consecuencia = self.evaluar(nodo.children[2]) # Índice corregido para saltar la flecha
        return z3.Implies(condicion, consecuencia)
        
    def _validacion_libre(self, nodo):
        return self.evaluar(nodo.children[0])

    def _declaracion_variable(self, nodo):
        izq = self.evaluar(nodo.children[0])
        der = self.evaluar(nodo.children[-1])
        return izq == der

    # --- 3. ESTRUCTURAS LOGICAS Y CONDICIONALES ---

    def _condicional(self, nodo):
        """Inferencia Dinámica del SINO 0"""
        condicion = self.evaluar(nodo.children[0])
        valor_entonces = self.evaluar(nodo.children[1])
        valor_sino = self.evaluar(nodo.children[2]) if len(nodo.children) > 2 else 0
            
        es_logico = z3.is_bool(valor_entonces)
        
        if es_logico:
            if isinstance(valor_sino, (int, float)) and valor_sino == 0:
                valor_sino = z3.BoolVal(True)
            
        return z3.If(condicion, valor_entonces, valor_sino)

    def _condicion_logica(self, nodo):
        resultado = self.evaluar(nodo.children[0])
        for i in range(1, len(nodo.children), 2):
            operador = self.evaluar(nodo.children[i])
            siguiente = self.evaluar(nodo.children[i+1])
            if operador == '.O.': resultado = z3.Or(resultado, siguiente)
            elif operador == '.Y.': resultado = z3.And(resultado, siguiente)
        return resultado
        

    def _casos_trailing(self, nodo):
        """
        Maneja estructuras condicionales en cascada.
        Asume un 'Sino 0' implícito al final si ninguna condición se cumple.
        """
        resultado = 0  # El Sino 0 por defecto
        # Recorremos en reversa para armar los If anidados desde adentro hacia afuera
        for hijo in reversed(nodo.children):
            condicion, valor = self.evaluar(hijo)
            resultado = z3.If(condicion, valor, resultado)
        return resultado

    def _caso_trailing(self, nodo):
        """
        Retorna la tupla (condicion, valor).
        El AST muestra que el valor está primero y la condición al final.
        """
        valor = self.evaluar(nodo.children[0])
        condicion = self.evaluar(nodo.children[-1])
        return condicion, valor

    # --- 4. COMPARACIONES Y MATEMÁTICAS ---
    
    def _comparacion_simple(self, nodo):
        resultado = self.evaluar(nodo.children[0])
        restricciones_encadenadas = []
        valor_actual = resultado
        
        for i in range(1, len(nodo.children), 2):
            operador = self.evaluar(nodo.children[i])
            siguiente = self.evaluar(nodo.children[i+1])
            
            if operador == '>':  restricciones_encadenadas.append(valor_actual > siguiente)
            elif operador == '<':  restricciones_encadenadas.append(valor_actual < siguiente)
            elif operador == '>=': restricciones_encadenadas.append(valor_actual >= siguiente)
            elif operador == '<=': restricciones_encadenadas.append(valor_actual <= siguiente)
            elif operador == '=':  restricciones_encadenadas.append(valor_actual == siguiente)
            elif operador == '!=': restricciones_encadenadas.append(valor_actual != siguiente)
            
            valor_actual = siguiente
            
        if len(restricciones_encadenadas) == 1:
            return restricciones_encadenadas[0]
        return z3.And(*restricciones_encadenadas)

    def _comparacion_atributo(self, nodo):
        """Maneja reglas como: Atributo = M14A. No usa matemáticas, usa lógica Pura."""
        operador = self.evaluar(nodo.children[0])
        
        # Extraemos el texto literal ('M14A') saltando la evaluación matemática
        def obtener_texto(n):
            if hasattr(n, 'children'): return obtener_texto(n.children[0])
            return str(n).replace('"', '').upper()
            
        valor_der = obtener_texto(nodo.children[1])
        
        # Creamos una compuerta lógica (True/False), NO una variable numérica.
        var_identidad = z3.Bool(f"IS_ATRIBUTO_{valor_der}")
        
        if operador == '=': return var_identidad
        if operador == '!=': return z3.Not(var_identidad)
        raise ValueError(f"Operador no soportado para atributos: {operador}")
        
    def _comparacion_funcion(self, nodo):
        """Maneja reglas como: TIPO([03]) = 1"""
        func_val = self.evaluar(nodo.children[0])
        operador = self.evaluar(nodo.children[1])
        der = self.evaluar(nodo.children[2])
        if operador == '=': return func_val == der
        if operador == '!=': return func_val != der
        raise ValueError("Operador no soportado para funcion")

    def _comparacion_existencia(self, nodo):
        """Maneja reglas como: $ [123]"""
        return self.evaluar(nodo.children[0]) > 0

    def _expresion(self, nodo):
        resultado = self.evaluar(nodo.children[0])
        for i in range(1, len(nodo.children), 2):
            operador = self.evaluar(nodo.children[i])
            siguiente = self.evaluar(nodo.children[i+1])
            if operador == '+': resultado += siguiente
            elif operador == '-': resultado -= siguiente
            elif operador == '*': resultado *= siguiente
            elif operador == '/': resultado /= siguiente
        return resultado

        
    def _rango_valores(self, nodo):
        return self.evaluar(nodo.children[0])
        
    def _serie_numeros(self, nodo):
        return self.evaluar(nodo.children[0])

    def _asignacion_en_condicional(self, nodo):
        izq = self.evaluar(nodo.children[0])
        der = self.evaluar(nodo.children[1])
        return izq == der

    def _funcion_directa(self, nodo):
        func = self.evaluar(nodo.children[0])
        val = self.evaluar(nodo.children[1])
        
        if func == 'POS': return z3.If(val > 0, val, 0)
        elif func == 'NEG': return z3.If(val < 0, -val, 0)
        elif func == 'ABS': return z3.If(val < 0, -val, val)
        return val

    def _funcion_rut(self, nodo):
        func = self.evaluar(nodo.children[0]) # Será 'TIPO' o 'SUBTIPO'
        param = str(nodo.children[2]).upper()
        
        var_func = self.motor.obtener_o_crear_variable(f"{func}_{param}")
        
        # Restricciones de Dominio Dinámicas
        if func == 'TIPO':
            self.motor.solver.add(var_func >= 1, var_func <= 8) # Ampliado para cubrir del 1 al 8
        elif func == 'SUBTIPO':
            self.motor.solver.add(var_func >= 1) # Los subtipos pueden ser 112, 113, 411, etc.
            
        return var_func

    def _funcion_matematica(self, nodo):
        nombre_func = str(nodo.children[0]).upper()
        
        args_node = nodo.children[2]
        args_limpios = [h for h in args_node.children if str(h) != ';']
        
        if nombre_func == 'POS':
            arg = self.evaluar(args_limpios[0])
            return z3.If(arg > 0, arg, 0)
            
        elif nombre_func == 'NEG':
            arg = self.evaluar(args_limpios[0])
            # Si es negativo (< 0), retornamos su valor absoluto (-arg). Si no, 0.
            return z3.If(arg < 0, -arg, 0)

        elif nombre_func == 'ABS':
            arg = self.evaluar(args_limpios[0])
            # Si es negativo, retorna -arg (para hacerlo positivo). Si no, retorna el mismo valor.
            return z3.If(arg < 0, -arg, arg)
            
        elif nombre_func == 'MIN':
            arg1 = self.evaluar(args_limpios[0])
            arg2 = self.evaluar(args_limpios[1])
            return z3.If(arg1 < arg2, arg1, arg2)
            
        elif nombre_func == 'MAX':
            arg1 = self.evaluar(args_limpios[0])
            arg2 = self.evaluar(args_limpios[1])
            return z3.If(arg1 > arg2, arg1, arg2)
        
        elif nombre_func == 'ROUND':
            # Mantenemos tu lógica original adaptada a la nueva estructura
            return self.evaluar(args_limpios[0])
            
        # Si llega una función que Z3 aún no conoce, avisamos claramente:
        raise ValueError(f"Función matemática no soportada o no implementada en Z3: {nombre_func}")

    def _sub_condicion(self, nodo):
        """
        Filtra dinámicamente los símbolos de apertura y cierre.
        Toma el nodo lógico real sin importar su posición en el AST.
        """
        # ESCUDO AMPLIADO: Ignora paréntesis, llaves y corchetes estructurales
        basura_estructural = ['(', ')', '{', '}', '[', ']']
        hijos_reales = [h for h in nodo.children if str(h) not in basura_estructural]
        
        if hijos_reales:
            return self.evaluar(hijos_reales[0])
        return None

    def _agrupacion(self, nodo):
        """
        Filtra dinámicamente los símbolos de una agrupación matemática.
        """
        basura_estructural = ['(', ')', '{', '}', '[', ']']
        hijos_reales = [h for h in nodo.children if str(h) not in basura_estructural]
        
        if hijos_reales:
            return self.evaluar(hijos_reales[0])
        return None
        
    def _lista_argumentos(self, nodo):
        """Evalúa los argumentos de una función omitiendo los separadores (;)"""
        argumentos_limpios = []
        for hijo in nodo.children:
            val = self.evaluar(hijo)
            # Ignoramos el separador para que Z3 solo reciba las variables/números
            if isinstance(val, str) and val == ';':
                continue
            argumentos_limpios.append(val)
        return argumentos_limpios