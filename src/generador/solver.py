import traceback
from src.generador.z3_core import MotorZ3
from src.generador.evaluator import EvaluadorAST
from src.generador.strategies.calculation_builder import CalculationBuilder
from src.generador.strategies.boundary_builder import BoundaryBuilder

class GeneradorCasos:
    def __init__(self, param_provider=None, rut_provider=None):
        self.motor = MotorZ3()
        self.evaluador = EvaluadorAST(self.motor)
        self.param_provider = param_provider
        self.rut_provider = rut_provider
        
        # Instanciamos ambas estrategias bajo el patrón Strategy
        self.calc_builder = CalculationBuilder(self.evaluador, self.motor, self.param_provider, self.rut_provider)
        self.bound_builder = BoundaryBuilder(self.evaluador, self.motor, self.param_provider, self.rut_provider)

    def resolver_validacion(self, ast_tree, id_val):
        """
        Enrutador Arquitectónico: Deriva el Árbol AST a la estrategia correcta
        dependiendo del tipo de validación (A/B vs C).
        """
        try:
            # Si el ID empieza con 'c.', usamos la estrategia de límites (Cotas y Mensajes)
            if id_val.lower().startswith('c.'):
                return self.bound_builder.generar_casos(ast_tree, id_val)
            # De lo contrario, usamos la estrategia de cálculos y MCDC (Reglas A y B)
            else:
                return self.calc_builder.generar_casos(ast_tree, id_val)
                
        except Exception as e:
            traceback.print_exc()
            return [{"id_validacion": id_val, "error": f"Error interno en generador: {str(e)}"}]