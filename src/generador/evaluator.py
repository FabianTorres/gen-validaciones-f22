import z3
from lark import Tree, Token
from src.generador.z3_core import MotorZ3

class EvaluadorAST:
    def __init__(self, motor_z3: MotorZ3):
        self.motor = motor_z3

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

    # --- 1. EVALUACION DE TOKENS (Gatekeeper Estricto) ---
    def _evaluar_token(self, token):
        tipo = token.type
        valor = str(token)

        if tipo in ('CODIGO', 'VECTOR', 'PARAMETRO'):
            nombre_limpio = valor.replace('[', '').replace(']', '').upper()
            return self.motor.obtener_o_crear_variable(f"[{nombre_limpio}]" if tipo == 'CODIGO' else nombre_limpio)
            
        elif tipo == 'NUMERO':
            return float(valor) if '.' in valor else int(valor)
            
        elif tipo == 'TEXTO':
            if valor.upper() in ('"BLANCO"', 'BLANCO'):
                return 0
            return self.motor.obtener_o_crear_variable(valor.upper())
            
        elif tipo in (
            'MATEMATICO', 'RELACIONAL_NUMERICO', 'LOGICO', 'IMPLICA', 
            'SEPARADOR', 'SIMBOLO_APERTURA', 'SIMBOLO_CIERRE', 
            'FUNCION', 'FUNCION_RUT', 'MARCA_CHECK', 'FORMATO_FECHA'
        ):
            return valor.upper()
            
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
        
    def _sub_condicion(self, nodo):
        return self.evaluar(nodo.children[0])

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

    def _agrupacion(self, nodo):
        return self.evaluar(nodo.children[1]) # Índice corregido
        
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
        func = self.evaluar(nodo.children[0])
        param = self.evaluar(nodo.children[2]) # Índice corregido
        return self.motor.obtener_o_crear_variable(f"{func}_{param}")

    def _funcion_matematica(self, nodo):
        func = self.evaluar(nodo.children[0])
        argumentos = self.evaluar(nodo.children[2]) # Índice corregido
        
        if func == 'MIN':
            min_val = argumentos[0]
            for arg in argumentos[1:]:
                min_val = z3.If(arg < min_val, arg, min_val)
            return min_val
        elif func == 'MAX':
            max_val = argumentos[0]
            for arg in argumentos[1:]:
                max_val = z3.If(arg > max_val, arg, max_val)
            return max_val
        elif func == 'ROUND':
            return argumentos[0]
        elif func == 'POS':
            return z3.If(argumentos[0] > 0, argumentos[0], 0)
            
        return argumentos[0]
        
    def _lista_argumentos(self, nodo):
        return [self.evaluar(hijo) for hijo in nodo.children]