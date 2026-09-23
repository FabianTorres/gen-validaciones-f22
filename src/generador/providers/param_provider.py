import re
import z3


class ParamProvider:
    def __init__(self, cache_parametros: dict):
        """
        Recibe el diccionario de parámetros en memoria (RAM).
        """
        self.parametros = cache_parametros
        self.no_pinneados = []

    def inyectar_en_motor(self, motor_z3, ast_str_completo: str):
        """
        Escanea el texto de los ASTs y pre-bloquea los parámetros antes de que Z3 los procese.
        Aplica un 'Hard Constraint' inquebrantable.
        """
        pinneados = set()
        for nombre, valor_real in self.parametros.items():
            # Radar: Si el parámetro es mencionado en alguna parte de las fórmulas...
            if nombre.upper() in ast_str_completo:
                # 1. Lo forzamos a crearse anticipadamente en la memoria de Z3
                var_simbolica = motor_z3.obtener_o_crear_variable(nombre)
                # 2. Le ponemos el candado absoluto
                motor_z3.agregar_restriccion_base(var_simbolica == valor_real)
                pinneados.add(nombre.upper())

        # --- GUARD PASIVO -------------------------------------------------
        # Red de seguridad: toda variable con forma de parametro (P\d+) que
        # haya quedado en memoria sin su candado de catalogo es un parametro
        # que Z3 resolveria como variable libre (bug a.220 con P647).
        self.no_pinneados = sorted(
            n
            for n in motor_z3.variables_memoria
            if re.fullmatch(r"P\d+", n.upper()) and n.upper() not in pinneados
        )
        if self.no_pinneados:
            print(
                f"⚠️ [PARAM GUARD] Parámetros usados pero NO pineados: {self.no_pinneados}"
            )
