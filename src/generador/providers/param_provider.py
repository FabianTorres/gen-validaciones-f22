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
        """
        for nombre, valor in self.parametros.items():
            motor_z3.variables_memoria[nombre] = z3.RealVal(valor)