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
            subtipo_req = None
            
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
                    # EXTRACCIÓN SEGURA: A prueba de fracciones Z3
                    if z3.is_rational_value(valor_crudo):
                        tipo_req = int(valor_crudo.as_fraction())
                    elif z3.is_int(valor_crudo):
                        tipo_req = valor_crudo.as_long()
                    else:
                        tipo_req = 1 # Fallback seguro
                    continue

                # --- NUEVA LECTURA PARA SUBTIPO ---
                if nombre == "SUBTIPO_[03]":
                    if z3.is_rational_value(valor_crudo):
                        subtipo_req = int(valor_crudo.as_fraction())
                    elif z3.is_int(valor_crudo):
                        subtipo_req = valor_crudo.as_long()
                    else:
                        subtipo_req = 112 # Fallback seguro
                    continue

                # --- MAGIA 2: FILTRO DE INPUTS PARA SELENIUM ---
                # Este condicional bloquea variables auxiliares abstractas como ALFA o BETA
                # asegurando que solo celdas [XXX] o vectores Vx lleguen al JSON final.
                es_codigo = nombre.startswith('[') and nombre.endswith(']')
                es_vector = nombre.startswith('Vx')
                
                if not (es_codigo or es_vector):
                    continue 
                
                # --- EXTRACCIÓN SEGURA: Prevención de Z3Exception ---
                if z3.is_rational_value(valor_crudo):
                    # Transforma la fracción C++ en un objeto Fraction nativo de Python
                    fraccion_py = valor_crudo.as_fraction()
                    valor_limpio = int(fraccion_py) if not getattr(settings, 'USAR_DECIMALES', False) else float(fraccion_py)
                elif z3.is_real(valor_crudo) or z3.is_algebraic_value(valor_crudo):
                    val_flotante = float(valor_crudo.as_decimal(4).rstrip('?'))
                    valor_limpio = int(val_flotante) if not getattr(settings, 'USAR_DECIMALES', False) else val_flotante
                elif z3.is_int(valor_crudo):
                    valor_limpio = valor_crudo.as_long()
                else:
                    valor_limpio = 0
                    
                datos_selenium[nombre] = valor_limpio

            # Hacemos la consulta inteligente al Proveedor de RUTs
            rut_final = "DEFAULT_RUT"
            if self.rut_provider:
                # NUEVO: Inyectamos el subtipo_req en la búsqueda
                rut_final = self.rut_provider.obtener_rut(atributos_req, atributos_prohibidos, tipo_req, subtipo_req)

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