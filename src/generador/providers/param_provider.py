import z3

class ParamProvider:
    def __init__(self, cache_parametros: dict):
        """
        Recibe el diccionario de parámetros en memoria (RAM).
        """
        self.parametros = cache_parametros

    def inyectar_en_motor(self, motor_z3, ast_str_completo: str):
        """
        Escanea el texto de los ASTs y pre-bloquea los parámetros antes de que Z3 los procese.
        Aplica un 'Hard Constraint' inquebrantable.
        """
        for nombre, valor_real in self.parametros.items():
            # Radar: Si el parámetro es mencionado en alguna parte de las fórmulas...
            if nombre.upper() in ast_str_completo:
                # 1. Lo forzamos a crearse anticipadamente en la memoria de Z3
                var_simbolica = motor_z3.obtener_o_crear_variable(nombre)
                # 2. Le ponemos el candado absoluto
                motor_z3.solver.add(var_simbolica == valor_real)