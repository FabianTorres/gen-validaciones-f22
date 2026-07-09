import z3
from src.config import settings

class MotorZ3:
    def __init__(self):
        self.solver = z3.Optimize()
        self.variables_memoria = {}
        self._configurar_semilla_base()

    def _configurar_semilla_base(self):
        """
        Convertimos la semilla a float para mantener la 
        compatibilidad absoluta con el dominio Real.
        """
        self.semilla_objetivo = float(settings.SEMILLA_GENERACION)

    def obtener_o_crear_variable(self, nombre_var):
        """
        ¡LA CLAVE DEL ÉXITO! 
        Todo se instancia como z3.Real() para evitar 'parser error'
        al multiplicar códigos con parámetros decimales (ej. P84 = 1.05).
        """
        if nombre_var not in self.variables_memoria:
            var_z3 = z3.Real(nombre_var)
            self.variables_memoria[nombre_var] = var_z3
            
            # Le pedimos al motor que se acerque a la semilla
            self.solver.add_soft(var_z3 == self.semilla_objetivo)
            
        return self.variables_memoria[nombre_var]

    def resolver_y_obtener_modelo(self):
        """Ejecuta la evaluación matemática."""
        if self.solver.check() == z3.sat:
            return self.solver.model()
        return None