from abc import ABC, abstractmethod
import z3
from src.config import settings

class BaseStrategy(ABC):
    def __init__(self, evaluador, motor_z3, param_provider, rut_provider):
        self.evaluador = evaluador
        self.motor = motor_z3
        self.param_provider = param_provider
        self.rut_provider = rut_provider

    @abstractmethod
    def generar_casos(self, ast_tree, id_val):
        pass

    def _resolver_y_formatear(self, id_val, tipo_escenario, descripcion, rut_inyectado, error_esperado=None):
        if self.motor.solver.check() == z3.sat:
            modelo = self.motor.solver.model()
            datos_selenium = {}
            
            for variable_z3 in modelo:
                nombre = variable_z3.name()
                valor_crudo = modelo[variable_z3]
                
                # Conversión nativa
                if z3.is_real(valor_crudo) or z3.is_algebraic_value(valor_crudo):
                    valor_limpio = float(valor_crudo.as_decimal(4).rstrip('?'))
                else:
                    valor_limpio = valor_crudo.as_long()
                    
                # MAGIA AQUÍ: Forzamos el casteo a Entero si settings lo exige
                if not getattr(settings, 'USAR_DECIMALES', False):
                    valor_limpio = int(valor_limpio)
                    
                datos_selenium[nombre] = valor_limpio

            return {
                "id_validacion": id_val,
                "tipo_escenario": tipo_escenario,
                "descripcion_qa": descripcion,
                "rut_inyectado": rut_inyectado,
                "inputs_selenium": datos_selenium,
                "resultado_esperado": error_esperado if error_esperado else "SIN_VALIDACION"
            }
        else:
            return {
                "id_validacion": id_val,
                "tipo_escenario": tipo_escenario,
                "descripcion_qa": descripcion,
                "estado_interno": "INSATISFACTIBLE",
                "detalle": "Contradicción matemática. Revisar si la regla es lógicamente posible."
            }

    def _ejecutar_escenario_aislado(self, restricciones_extra, funcion_escenario):
        self.motor.solver.push() 
        for restriccion in restricciones_extra:
            self.motor.solver.add(restriccion)
            
        resultado = funcion_escenario()
        
        self.motor.solver.pop() 
        return resultado