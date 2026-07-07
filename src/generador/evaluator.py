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

    # --- 1. EVALUACION DE TOKENS (Nivel Base) ---
    def _evaluar_token(self, token):
        tipo = token.type
        valor = str(token)

        if tipo in ('CODIGO', 'TEXTO', 'VECTOR'):
            # Interceptamos la sanitización de estados nulos de la Fase 1
            if valor.upper() == '"BLANCO"':
                # Matemáticamente, para el SII, comparar contra BLANCO es comparar contra vacío/0
                return 0
            # Pedimos a Z3 que instancie o recupere la variable en memoria
            return self.motor.obtener_o_crear_variable(valor.replace('"', '').upper())
            
        elif tipo == 'NUMERO':
            return float(valor) if '.' in valor else int(valor)
            
        return valor.upper()

    # --- 2. REGLAS PRINCIPALES DE NEGOCIO ---
    
    def _validacion(self, nodo):
        """Nodo raíz. Unifica todas las reglas en un gran AND."""
        restricciones = [self.evaluar(h) for h in nodo.children]
        return z3.And(*restricciones)

    def _autocalculado(self, nodo):
        """Asignación estricta de las reglas A y B (CÓDIGO = FÓRMULA)"""
        izq = self.evaluar(nodo.children[0])
        der = self.evaluar(nodo.children[-1])
        return izq == der

    def _cota(self, nodo):
        """Resuelve reglas tipo C y N (A >= B)"""
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
        """Reglas D y E (Condición => Consecuencia)"""
        condicion = self.evaluar(nodo.children[0])
        consecuencia = self.evaluar(nodo.children[1])
        return z3.Implies(condicion, consecuencia)
        
    def _validacion_libre(self, nodo):
        """Reglas M (Asignaciones flotantes sin código inicial)"""
        return self.evaluar(nodo.children[0])

    def _declaracion_variable(self, nodo):
        """Variables auxiliares (DONDE ALFA = X)"""
        izq = self.evaluar(nodo.children[0])
        der = self.evaluar(nodo.children[-1])
        return izq == der

    # --- 3. ESTRUCTURAS LOGICAS Y CONDICIONALES ---

    def _condicional(self, nodo):
        """
        Traduce SI... ENTONCES... SINO... aplicando INFERENCIA DINÁMICA DE TIPOS
        para resolver el problema del "Sino 0".
        """
        condicion = self.evaluar(nodo.children[0])
        valor_entonces = self.evaluar(nodo.children[1])
        
        # Extraemos el valor del SINO (o asumimos 0 si no existe)
        valor_sino = self.evaluar(nodo.children[2]) if len(nodo.children) > 2 else 0
            
        # MAGIA DE LA FASE 2: Inferencia de Tipos Semántica (Z3)
        es_logico = z3.is_bool(valor_entonces)
        
        if es_logico:
            # Caso B (Lógico): El ENTONCES es una ecuación (Verdadero/Falso).
            # Si el SINO es 0 matematicamente, chocará. Lo transmutamos a z3.BoolVal(True)
            if isinstance(valor_sino, (int, float)) and valor_sino == 0:
                valor_sino = z3.BoolVal(True)
        else:
            # Caso A (Matemático): El ENTONCES es un número. 
            # Si no hay SINO, Z3 asume que vale 0 (vacío) por defecto en matemáticas.
            pass 
            
        return z3.If(condicion, valor_entonces, valor_sino)

    def _condicion_logica(self, nodo):
        """Agrupaciones de condiciones (.y. / .o.)"""
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
        """Soporta comparaciones normales y encadenadas (A <= B <= C)"""
        resultado = self.evaluar(nodo.children[0])
        
        # Generamos un tren de And() para resolver múltiples condiciones
        # (A <= B <= C) se convierte en And(A <= B, B <= C)
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
        # Mapea dinámicamente "Atributo = M14A" como variable en memoria de Z3
        var_atributo = self.motor.obtener_o_crear_variable("ATRIBUTO")
        operador = self.evaluar(nodo.children[0])
        der = self.evaluar(nodo.children[1])
        
        if operador == '=': return var_atributo == der
        if operador == '!=': return var_atributo != der
        raise ValueError(f"Operador no soportado para atributos: {operador}")

    def _expresion(self, nodo):
        """Sumas, restas, multiplicaciones, etc."""
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
        return self.evaluar(nodo.children[0])
        
    def _rango_valores(self, nodo):
        return self.evaluar(nodo.children[0])
        
    def _serie_numeros(self, nodo):
        # En la capa matemática, si la serie ya pasó por el desugaring, 
        # esto normalmente solo debería retornar el primer elemento si quedó singular.
        return self.evaluar(nodo.children[0])

    def _asignacion_en_condicional(self, nodo):
        izq = self.evaluar(nodo.children[0])
        der = self.evaluar(nodo.children[1])
        return izq == der

    def _funcion_directa(self, nodo):
        # Ej: POS[123] o NEG[123]
        func = self.evaluar(nodo.children[0])
        val = self.evaluar(nodo.children[1])
        
        if func == 'POS': 
            return z3.If(val > 0, val, 0)
        elif func == 'NEG':
            return z3.If(val < 0, val, 0)
        elif func == 'ABS':
            return z3.If(val < 0, -val, val)
        return val

    def _funcion_rut(self, nodo):
        # Ej: TIPO([03]) -> Lo mapeamos como una variable conjunta TIPO_[03]
        func = self.evaluar(nodo.children[0])
        param = self.evaluar(nodo.children[1])
        return self.motor.obtener_o_crear_variable(f"{func}_{param}")

    def _funcion_matematica(self, nodo):
        # Ej: MIN(A; B; C)
        func = self.evaluar(nodo.children[0])
        argumentos = self.evaluar(nodo.children[1]) # Viene como lista
        
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
            # Z3 trabaja con racionales nativos, el redondeo final se aplicará 
            # en el solver a la hora de extraer los casos de prueba.
            return argumentos[0]
            
        elif func == 'POS':
            return z3.If(argumentos[0] > 0, argumentos[0], 0)
            
        return argumentos[0]
        
    def _lista_argumentos(self, nodo):
        return [self.evaluar(hijo) for hijo in nodo.children]