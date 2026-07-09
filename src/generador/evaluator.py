import z3
from lark import Tree, Token
from src.generador.z3_core import MotorZ3

class EvaluadorAST:
    def __init__(self, motor_z3: MotorZ3):
        self.motor = motor_z3

    def evaluar(self, nodo):
        """Punto de entrada principal. Recorre recursivamente el AST."""
        if isinstance(nodo, Token):
            return self._evaluar_token(nodo)
        if isinstance(nodo, Tree):
            metodo = getattr(self, f"_{nodo.data}", self._evaluar_default)
            return metodo(nodo)
        return nodo

    def _evaluar_default(self, nodo):
        raise NotImplementedError(f"Falta implementar la evaluación para la regla AST: '{nodo.data}'")

    # --- 1. EVALUACION DE TOKENS (Gatekeeper Estricto) ---
    def _evaluar_token(self, token):
        tipo = token.type
        valor = str(token)

        # 1. Variables y Constantes (Universos Z3)
        if tipo in ('CODIGO', 'VECTOR', 'PARAMETRO'):
            nombre_limpio = valor.replace('[', '').replace(']', '').upper()
            # Devolvemos el código con corchetes, pero los vectores y parámetros limpios
            return self.motor.obtener_o_crear_variable(f"[{nombre_limpio}]" if tipo == 'CODIGO' else nombre_limpio)
            
        # 2. Tipos Numéricos Nativos
        elif tipo == 'NUMERO':
            return float(valor) if '.' in valor else int(valor)
            
        # 3. Tratamiento especial de Nulos/Blancos (Se asumen 0 para Z3)
        elif tipo == 'TEXTO':
            if valor.upper() in ('"BLANCO"', 'BLANCO'):
                return 0
            return self.motor.obtener_o_crear_variable(valor.upper())
            
        # 4. Operadores, Símbolos y Funciones (Pasan en texto plano para enrutar el AST)
        elif tipo in (
            'MATEMATICO', 'RELACIONAL_NUMERICO', 'LOGICO', 'IMPLICA', 
            'SEPARADOR', 'SIMBOLO_APERTURA', 'SIMBOLO_CIERRE', 
            'FUNCION', 'FUNCION_RUT', 'MARCA_CHECK', 'FORMATO_FECHA'
        ):
            return valor.upper()
            
        # Si llega algo que no está en la gramática, bloqueamos antes de que Z3 lo lea
        raise ValueError(f"Token no reconocido por el Evaluador Z3: {tipo} -> {valor}")

    # --- 2. EVALUACION DE REGLAS SINTACTICAS ---
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

    def _asignacion_en_condicional(self, nodo):
        izq = self.evaluar(nodo.children[0])
        der = self.evaluar(nodo.children[-1])
        return izq == der
        
    def _comparacion_simple(self, nodo):
        resultado = self.evaluar(nodo.children[0])
        for i in range(1, len(nodo.children), 2):
            operador = self.evaluar(nodo.children[i])
            siguiente = self.evaluar(nodo.children[i+1])
            
            if operador == '>':  resultado = resultado > siguiente
            elif operador == '<':  resultado = resultado < siguiente
            elif operador == '>=': resultado = resultado >= siguiente
            elif operador == '<=': resultado = resultado <= siguiente
            elif operador == '=':  resultado = resultado == siguiente
            elif operador == '!=': resultado = resultado != siguiente
            elif operador == '=>': resultado = z3.Implies(resultado, siguiente)
            else: raise ValueError(f"Operador relacional desconocido: {operador}")
        return resultado

    def _expresion(self, nodo):
        resultado = self.evaluar(nodo.children[0])
        for i in range(1, len(nodo.children), 2):
            operador = self.evaluar(nodo.children[i])
            siguiente_valor = self.evaluar(nodo.children[i+1])
            
            if operador == '+': resultado += siguiente_valor
            elif operador == '-': resultado -= siguiente_valor
            elif operador == '*': resultado *= siguiente_valor
            elif operador == '/': resultado /= siguiente_valor
        return resultado

    def _agrupacion(self, nodo):
        # nodo.children[0] es '(', nodo.children[1] es la expresión, nodo.children[2] es ')'
        return self.evaluar(nodo.children[1])

    # --- 3. EVALUACIÓN LÓGICA Y ESTRUCTURAL ---
    def _condicion_logica(self, nodo):
        resultado = self.evaluar(nodo.children[0])
        for i in range(1, len(nodo.children), 2):
            operador = self.evaluar(nodo.children[i])
            siguiente_valor = self.evaluar(nodo.children[i+1])
            
            if operador == '.O.':
                resultado = z3.Or(resultado, siguiente_valor)
            elif operador == '.Y.':
                resultado = z3.And(resultado, siguiente_valor)
        return resultado

    def _implicacion(self, nodo):
        condicion = self.evaluar(nodo.children[0])
        consecuencia = self.evaluar(nodo.children[1])
        return z3.Implies(condicion, consecuencia)

    def _validacion(self, nodo):
        restricciones = [self.evaluar(hijo) for hijo in nodo.children]
        return z3.And(*restricciones)

    def _condicional_leading(self, nodo):
        condicion = self.evaluar(nodo.children[0])
        valor_entonces = self.evaluar(nodo.children[1])
        valor_sino = self.evaluar(nodo.children[2]) if len(nodo.children) > 2 else 0 
        return z3.If(condicion, valor_entonces, valor_sino)

    def _funcion_matematica(self, nodo):
        # Grammar: FUNCION SIMBOLO_APERTURA lista_argumentos SIMBOLO_CIERRE
        # children[0]: FUNCION, children[1]: '(', children[2]: lista, children[3]: ')'
        func = self.evaluar(nodo.children[0])
        argumentos = self.evaluar(nodo.children[2]) # <--- Antes era 1, ahora es 2
        
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

    def _funcion_rut(self, nodo):
        # Grammar: FUNCION_RUT SIMBOLO_APERTURA CODIGO SIMBOLO_CIERRE
        # children[0]: FUNCION_RUT, children[1]: '(', children[2]: CODIGO, children[3]: ')'
        func = self.evaluar(nodo.children[0])
        param = self.evaluar(nodo.children[2]) # <--- Antes era 1, ahora es 2
        return self.motor.obtener_o_crear_variable(f"{func}_{param}")