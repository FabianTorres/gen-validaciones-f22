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

    def _resolver_y_formatear(self, id_val, tipo_escenario, descripcion, error_esperado=None, codigo_objetivo=None, condicion_verificadora=None):
        if self.motor.solver.check() == z3.sat:
            modelo = self.motor.solver.model()
            datos_selenium = {}
            valor_objetivo = 0 

            atributos_req = []
            atributos_prohibidos = []
            tipo_req = None
            subtipo_req = None
            
            for variable_z3 in modelo:
                # --- PARCHE DE ARQUITECTURA: Ignorar funciones fantasma de Z3 (como /0 o funciones no interpretadas) ---
                if variable_z3.arity() > 0:
                    continue

                nombre = variable_z3.name()
                valor_crudo = modelo[variable_z3]
                
                # --- MAGIA 1: LECTURA DE IDENTIDAD ---
                if nombre.startswith("IS_ATRIBUTO_"):
                    atr = nombre.replace("IS_ATRIBUTO_", "")
                    if z3.is_true(valor_crudo): atributos_req.append(atr)
                    elif z3.is_false(valor_crudo): atributos_prohibidos.append(atr)
                    continue
                    
                if nombre == "TIPO_[03]":
                    if z3.is_rational_value(valor_crudo): tipo_req = int(valor_crudo.as_fraction())
                    elif z3.is_int(valor_crudo): tipo_req = valor_crudo.as_long()
                    else: tipo_req = 1 
                    continue

                if nombre == "SUBTIPO_[03]":
                    if z3.is_rational_value(valor_crudo): subtipo_req = int(valor_crudo.as_fraction())
                    elif z3.is_int(valor_crudo): subtipo_req = valor_crudo.as_long()
                    else: subtipo_req = 111 
                    continue

                # --- MAGIA 2: FILTRO DE INPUTS PARA SELENIUM ---
                es_codigo = nombre.startswith('[') and nombre.endswith(']') and any(c.isdigit() for c in nombre)
                es_vector = nombre.startswith('Vx')
                
                if not (es_codigo or es_vector):
                    continue 
                
                # --- EXTRACCIÓN SEGURA ---
                if z3.is_rational_value(valor_crudo):
                    fraccion_py = valor_crudo.as_fraction()
                    valor_limpio = int(fraccion_py) if not getattr(settings, 'USAR_DECIMALES', False) else float(fraccion_py)
                elif z3.is_real(valor_crudo) or z3.is_algebraic_value(valor_crudo):
                    val_flotante = float(valor_crudo.as_decimal(4).rstrip('?'))
                    valor_limpio = int(val_flotante) if not getattr(settings, 'USAR_DECIMALES', False) else val_flotante
                elif z3.is_int(valor_crudo):
                    valor_limpio = valor_crudo.as_long()
                else:
                    valor_limpio = 0
                    
                if codigo_objetivo and nombre == codigo_objetivo:
                    valor_objetivo = valor_limpio
                else:
                    datos_selenium[nombre] = valor_limpio

            # --- MAGIA 3: VERIFICACIÓN POST-REDONDEO (LA DOBLE PASADA) ---
            if condicion_verificadora is not None and error_esperado is not None:
                sustituciones = []
                for variable_z3 in modelo:
                    # Aplicamos el mismo escudo aquí para la sustitución
                    if variable_z3.arity() > 0:
                        continue
                        
                    nombre = variable_z3.name()
                    if nombre in datos_selenium:
                        sustituciones.append((variable_z3(), z3.RealVal(datos_selenium[nombre])))
                    elif codigo_objetivo and nombre == codigo_objetivo:
                        sustituciones.append((variable_z3(), z3.RealVal(valor_objetivo)))
                    else:
                        sustituciones.append((variable_z3(), modelo[variable_z3]))
                        
                condicion_evaluada = z3.simplify(z3.substitute(condicion_verificadora, *sustituciones))
                
                if z3.is_true(condicion_evaluada):
                    resultado_real_redondeado = "BUENO"
                elif z3.is_false(condicion_evaluada):
                    resultado_real_redondeado = "MENSAJE"
                else:
                    resultado_real_redondeado = error_esperado
                    
                if error_esperado != resultado_real_redondeado:
                    error_esperado = resultado_real_redondeado
                    descripcion += f" [Auto-Corregido: El truncamiento decimal altera el resultado en UI a {error_esperado}]"

            rut_final = "DEFAULT_RUT"
            if self.rut_provider:
                rut_final = self.rut_provider.obtener_rut(atributos_req, atributos_prohibidos, tipo_req, subtipo_req)

            resultado_json = {
                "id_validacion": id_val,
                "tipo_escenario": tipo_escenario,
                "descripcion_qa": descripcion,
                "rut": rut_final,
                "inputs": datos_selenium,
                "resultado_esperado": error_esperado
            }

            if codigo_objetivo:
                resultado_json["objetivo"] = {
                    "codigo": codigo_objetivo,
                    "valor": valor_objetivo
                }

            return resultado_json
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