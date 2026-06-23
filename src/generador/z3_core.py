import z3
from src.config import settings

class MotorZ3:
    def __init__(self):
        self.solver = z3.Optimize()
        self.variables_memoria = {}
        self._configurar_semilla_base()

    def _configurar_semilla_base(self):
        """
        Define el valor objetivo que el motor intentará usar como pivote,
        respetando estrictamente el tipado definido en settings.py.
        """
        if settings.USAR_DECIMALES:
            self.semilla_objetivo = float(settings.SEMILLA_GENERACION)
        else:
            self.semilla_objetivo = int(settings.SEMILLA_GENERACION)

    def obtener_o_crear_variable(self, nombre_var):
        """
        Instancia la variable (el input del caso de prueba) respetando la 
        naturaleza de los datos configurada para la corrida.
        """
        if nombre_var not in self.variables_memoria:
            if settings.USAR_DECIMALES:
                self.variables_memoria[nombre_var] = z3.Real(nombre_var)
            else:
                self.variables_memoria[nombre_var] = z3.Int(nombre_var)
                
            # Soft Constraint: Le pedimos al motor que los valores generados 
            # se acerquen a nuestra semilla para evitar trivialidades (0, 1)
            # sin importar si es Int o Real.
            self.solver.add_soft(self.variables_memoria[nombre_var] == self.semilla_objetivo)
            
        return self.variables_memoria[nombre_var]

    def resolver_y_obtener_modelo(self):
        """
        Ejecuta la evaluación matemática y devuelve el diccionario con los casos.
        """
        if self.solver.check() == z3.sat:
            return self.solver.model()
        return None