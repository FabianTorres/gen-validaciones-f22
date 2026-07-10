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

    # NOTA: Le quitamos 'rut_inyectado' de los parámetros porque ahora es automático
    def _resolver_y_formatear(self, id_val, tipo_escenario, descripcion, error_esperado=None):
        if self.motor.solver.check() == z3.sat:
            modelo = self.motor.solver.model()
            datos_selenium = {}
            
            # Recolectores de exigencias para el RUT
            atributos_req = []
            atributos_prohibidos = []
            tipo_req = None
            
            for variable_z3 in modelo:
                nombre = variable_z3.name()
                valor_crudo = modelo[variable_z3]
                
                # --- MAGIA 1: LECTURA DE IDENTIDAD ---
                if nombre.startswith("IS_ATRIBUTO_"):
                    atr = nombre.replace("IS_ATRIBUTO_", "")
                    if z3.is_true(valor_crudo): atributos_req.append(atr)
                    elif z3.is_false(valor_crudo): atributos_prohibidos.append(atr)
                    continue
                    
                if nombre == "TIPO_[03]":
                    tipo_req = valor_crudo.as_long()
                    continue

                # --- MAGIA 2: FILTRO DE INPUTS PARA SELENIUM ---
                es_codigo = nombre.startswith('[') and nombre.endswith(']')
                es_vector = nombre.startswith('Vx')
                if not (es_codigo or es_vector):
                    continue 
                
                # Conversión numérica limpia
                if z3.is_real(valor_crudo) or z3.is_algebraic_value(valor_crudo):
                    valor_limpio = float(valor_crudo.as_decimal(4).rstrip('?'))
                else:
                    valor_limpio = valor_crudo.as_long()
                    
                if not getattr(settings, 'USAR_DECIMALES', False):
                    valor_limpio = int(valor_limpio)
                    
                datos_selenium[nombre] = valor_limpio

            # Hacemos la consulta inteligente al Proveedor de RUTs
            rut_final = "DEFAULT_RUT"
            if self.rut_provider:
                rut_final = self.rut_provider.obtener_rut(atributos_req, atributos_prohibidos, tipo_req)

            return {
                "id_validacion": id_val,
                "tipo_escenario": tipo_escenario,
                "descripcion_qa": descripcion,
                "rut": rut_final,
                "inputs": datos_selenium,
                "resultado_esperado": error_esperado
            }
        else:
            return {
                "id_validacion": id_val,
                "tipo_escenario": tipo_escenario,
                "descripcion_qa": descripcion,
                "estado_interno": "INSATISFACTIBLE"
            }

    def _ejecutar_escenario_aislado(self, restricciones_extra, funcion_escenario):
        self.motor.solver.push() 
        for restriccion in restricciones_extra:
            self.motor.solver.add(restriccion)
        resultado = funcion_escenario()
        self.motor.solver.pop() 
        return resultado