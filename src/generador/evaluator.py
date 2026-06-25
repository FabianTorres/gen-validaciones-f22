import z3
from lark import Tree, Token
from src.generador.z3_core import MotorZ3

class EvaluadorAST:
    def __init__(self, motor_z3: MotorZ3):
        self.motor = motor_z3

    def evaluar(self, nodo):
        """
        Punto de entrada principal. Recorre recursivamente el AST de Lark.
        """
        # Si es un Token (hoja del árbol, ej: "[123]", "1000", "+")
        if isinstance(nodo, Token):
            return self._evaluar_token(nodo)
            
        # Si es un Tree (rama del árbol, ej: comparacion_simple, asignacion)
        if isinstance(nodo, Tree):
            # Busca el método que se llame igual que la regla de Lark.
            # Ej: Si la regla es "comparacion_simple", llama a self._comparacion_simple
            metodo = getattr(self, f"_{nodo.data}", self._evaluar_default)
            return metodo(nodo)
            
        return nodo

    def _evaluar_default(self, nodo):
        """Fallback de seguridad si encontramos una regla que aún no hemos mapeado."""
        raise NotImplementedError(f"Falta implementar la evaluación para la regla AST: '{nodo.data}'")

    # --- 1. EVALUACION DE TOKENS (Nivel Base) ---
    def _evaluar_token(self, token):
        """Traduce el texto crudo a variables lógicas o números reales."""
        tipo = token.type
        valor = str(token)

        if tipo in ('CODIGO', 'TEXTO', 'VECTOR'):
            # Pedimos a nuestro Motor Z3 que nos de (o cree) la variable en memoria
            return self.motor.obtener_o_crear_variable(valor.upper())
            
        elif tipo == 'NUMERO':
            # Convertimos a float nativo si tiene punto, si no a entero.
            # Z3 sabra como operar estos tipos nativos con sus variables.
            return float(valor) if '.' in valor else int(valor)
            
        return valor.upper()

    # --- 2. EVALUACION DE REGLAS SINTACTICAS (Nivel Estructural) ---

    def _autocalculado(self, nodo):
        """Asignación de variable estricta de las reglas A y B"""
        izq = self.evaluar(nodo.children[0])
        der = self.evaluar(nodo.children[-1])
        return izq == der

    def _cota(self, nodo):
        """
        Resuelve reglas tipo C y N. (ej: A > B o A >= Si...)
        """
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
        """Cuando se asigna una variable dentro de un ENTONCES en validación Tipo M"""
        izq = self.evaluar(nodo.children[0])
        der = self.evaluar(nodo.children[-1])
        return izq == der
        
    def _comparacion_simple(self, nodo):
        """Resuelve operaciones relacionales simples de la capa lógica (ej. A > B)"""
        izq = self.evaluar(nodo.children[0])
        operador = self.evaluar(nodo.children[1])
        der = self.evaluar(nodo.children[2])
        
        if operador == '>':  return izq > der
        if operador == '<':  return izq < der
        if operador == '>=': return izq >= der
        if operador == '<=': return izq <= der
        if operador == '=':  return izq == der
        if operador == '!=': return izq != der
        raise ValueError(f"Operador relacional numérico desconocido: {operador}")
    
    
    def _comparacion_simple(self, nodo):
        """
        Resuelve operaciones relacionales encadenadas (ej. A > B => C)
        """
        resultado = self.evaluar(nodo.children[0])
        
        # Iteramos de a pares para soportar múltiples operadores en la misma línea
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
        """
        Resuelve sumas, restas, multiplicaciones, etc.
        (Esta regla la iremos expandiendo a medida que conectemos las matemáticas completas)
        """
        # Por ahora extraemos el primer elemento evaluado
        resultado = self.evaluar(nodo.children[0])
        
        # Iteramos de a pares (operador, valor) para ir apilando la matemática
        for i in range(1, len(nodo.children), 2):
            operador = self.evaluar(nodo.children[i])
            siguiente_valor = self.evaluar(nodo.children[i+1])
            
            if operador == '+': resultado += siguiente_valor
            elif operador == '-': resultado -= siguiente_valor
            elif operador == '*': resultado *= siguiente_valor
            elif operador == '/': resultado /= siguiente_valor
            
        return resultado

    def _agrupacion(self, nodo):
        """
        Resuelve los paréntesis (...). 
        El motor simplemente ignora el contenedor visual y evalúa el contenido interno.
        """
        # Una regla de agrupación en Lark típicamente tiene un solo hijo útil: 
        # la expresión que está adentro de los paréntesis.
        return self.evaluar(nodo.children[0])

    # --- 3. EVALUACIÓN LÓGICA Y ESTRUCTURAL ---

    def _condicion_logica(self, nodo):
        """
        Resuelve las agrupaciones de condiciones (.y. / .o.)
        """
        resultado = self.evaluar(nodo.children[0])
        
        for i in range(1, len(nodo.children), 2):
            operador = self.evaluar(nodo.children[i])
            siguiente_valor = self.evaluar(nodo.children[i+1])
            
            # Z3 usa funciones nativas And() y Or() para las compuertas lógicas
            if operador == '.O.':
                resultado = z3.Or(resultado, siguiente_valor)
            elif operador == '.Y.':
                resultado = z3.And(resultado, siguiente_valor)
                
        return resultado

    def _implicacion(self, nodo):
        """
        Traduce el condicional 'Si A => B' al motor Z3.
        """
        # La implicación en Lark tiene la condición a la izquierda y la consecuencia a la derecha
        condicion = self.evaluar(nodo.children[0])
        consecuencia = self.evaluar(nodo.children[1])
        
        # Z3 tiene Implies nativo: "Si la condición es Verdadera, la consecuencia DEBE serlo"
        return z3.Implies(condicion, consecuencia)

    def _validacion(self, nodo):
        """
        Nodo raíz del árbol. Recopila todas las reglas y variables 
        y las unifica en una sola gran restricción lógica (AND).
        """
        restricciones = []
        for hijo in nodo.children:
            restricciones.append(self.evaluar(hijo))
            
        # Todo lo que esté en la validación (regla principal + asignaciones "DONDE")
        # debe cumplirse simultáneamente, por lo que las unimos con un AND global.
        return z3.And(*restricciones)

    

    def _condicional_leading(self, nodo):
        """
        Traduce un bloque SI... ENTONCES... SINO... a una función z3.If()
        """
        # Los hijos son las ramas de decisión puras: [condicion, entonces, sino]
        condicion = self.evaluar(nodo.children[0])
        valor_entonces = self.evaluar(nodo.children[1])
        
        # Si la regla tiene un 'SINO' explícito
        if len(nodo.children) > 2:
            valor_sino = self.evaluar(nodo.children[2])
        else:
            # Si el SII no pone un SINO en una asignación matemática, 
            # el valor por defecto asimilado es 0.
            valor_sino = 0 
            
        # z3.If se encarga de bifurcar la matemática dinámicamente
        return z3.If(condicion, valor_entonces, valor_sino)