import z3

class ParamProvider:
    def __init__(self, cache_parametros: dict):
        """
        Recibe el diccionario de parámetros en memoria (RAM).
        Eliminamos la lectura del archivo .txt.
        """
        self.parametros = cache_parametros

    def inyectar_en_motor(self, motor_z3):
        """
        Inyecta todos los parámetros blindados contra errores tipográficos.
        Aplica un 'Hard Constraint' para que Z3 no pueda hackear los valores.
        """
        for nombre, valor_real in self.parametros.items():
            # Si la variable simbólica ya fue creada por el AST, la bloqueamos.
            if nombre in motor_z3.variables_memoria:
                var_simbolica = motor_z3.variables_memoria[nombre]
                # CANDADO ABSOLUTO: Obligamos al solver a respetar la base de datos
                motor_z3.solver.add(var_simbolica == valor_real)