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

    def _resolver_y_formatear(self, id_val, tipo_escenario, descripcion, error_esperado=None, codigo_objetivo=None, condicion_verificadora=None, ast_tree=None):
        if self.motor.solver.check() == z3.sat:
            modelo = self.motor.solver.model()
            datos_selenium = {}
            valor_objetivo = 0 

            atributos_req = []
            atributos_prohibidos = []
            tipo_req = None
            subtipo_req = None
            
            for variable_z3 in modelo:
                # Ignoro funciones fantasma de la arquitectura interna de Z3
                if variable_z3.arity() > 0:
                    continue

                nombre = variable_z3.name()
                valor_crudo = modelo[variable_z3]
                
                # Proceso las banderas lógicas de identidad del contribuyente
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

                # Filtro variables transaccionales que simulan inputs del frontend
                es_codigo = nombre.startswith('[') and nombre.endswith(']') and any(c.isdigit() for c in nombre)
                es_vector = nombre.startswith('Vx')
                
                if not (es_codigo or es_vector):
                    continue 
                
                # Extraigo el valor de forma segura truncando o convirtiendo a flotante según configuración
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

            # Aplico la doble pasada para asegurar que el truncamiento decimal en Python no altera la premisa lógica original
            if condicion_verificadora is not None and error_esperado is not None:
                sustituciones = []
                for variable_z3 in modelo:
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

            # Genero la huella lógica en base al modelo resuelto sin alterar la estructura del caso
            huella_logica = {}
            if ast_tree:
                huella_logica = self._calcular_huella_logica(modelo, ast_tree)

            rut_final = "DEFAULT_RUT"
            if self.rut_provider:
                rut_final = self.rut_provider.obtener_rut(atributos_req, atributos_prohibidos, tipo_req, subtipo_req)

            resultado_json = {
                "id_validacion": id_val,
                "tipo_escenario": tipo_escenario,
                "descripcion_qa": descripcion,
                "rut": rut_final,
                "inputs": datos_selenium,
                "resultado_esperado": error_esperado,
                "huella_logica": huella_logica
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

    def _calcular_huella_logica(self, modelo, ast_tree):
        """
        Intérprete jerárquico (Lazy Evaluator) del AST.
        Simula la ejecución en tiempo de ejecución inyectando el modelo de Z3,
        aplicando cortocircuitos reales y respetando las ramas de control (SINO).
        """
        huella = {}
        contadores = {'CONDICION': 0, 'MIN': 0, 'MAX': 0, 'POS': 0, 'NEG': 0, 'ABS': 0, 'IF': 0, 'AND': 0, 'OR': 0}

        def visitar(nodo, forzar_skip=False):
            if not hasattr(nodo, 'data'):
                return None

            # 1. EVALUACIÓN CONDICIONAL ESTÁNDAR (SI... ENTONCES... SINO)
            if nodo.data == 'condicional':
                contadores['IF'] += 1
                id_if = contadores['IF']
                
                # Evaluamos la condición lógica
                res_cond = visitar(nodo.children[0], forzar_skip)
                
                if forzar_skip:
                    huella[f"IF_{id_if}"] = "SKIPPED"
                else:
                    huella[f"IF_{id_if}"] = "TRUE" if res_cond else "FALSE"
                
                # Lógica de saltos (Lazy Evaluation)
                skip_entonces = forzar_skip or (not res_cond)
                skip_sino = forzar_skip or bool(res_cond)
                
                # La rama [1] es siempre el ENTONCES, la [2] es el SINO (si existe)
                if len(nodo.children) > 1:
                    visitar(nodo.children[1], skip_entonces)
                if len(nodo.children) > 2:
                    visitar(nodo.children[2], skip_sino)
                    
                return res_cond

            # 2. EVALUACIÓN DE CASOS INVERTIDOS (EXPRESION SI CONDICION)
            elif nodo.data == 'caso_trailing':
                contadores['IF'] += 1
                id_if = contadores['IF']
                
                # En un trailing, la condición lógica está al final (hijo [-1])
                res_cond = visitar(nodo.children[-1], forzar_skip)
                
                if forzar_skip:
                    huella[f"IF_{id_if}"] = "SKIPPED"
                else:
                    huella[f"IF_{id_if}"] = "TRUE" if res_cond else "FALSE"
                    
                skip_expresion = forzar_skip or (not res_cond)
                
                # La expresión matemática a ejecutar está al principio (hijo [0])
                visitar(nodo.children[0], skip_expresion)
                return res_cond

            # 3. CONTENEDOR MULTIPLE DE TRAILINGS (Switch-case)
            elif nodo.data == 'casos_trailing':
                skip_restantes = forzar_skip
                for hijo in nodo.children:
                    if getattr(hijo, 'data', '') == 'caso_trailing':
                        res = visitar(hijo, skip_restantes)
                        if res:  # Si un caso se cumple, los demás se cortocircuitan
                            skip_restantes = True
                    elif getattr(hijo, 'data', '') == 'caso_default':
                        visitar(hijo.children[-1], skip_restantes)
                return None

            # 4. OPERADORES LÓGICOS CON CORTOCIRCUITO (AND / OR)
            elif nodo.data == 'condicion_logica':
                resultado_compuesto = None
                skip_restante = forzar_skip
                operador_actual = None

                for hijo in nodo.children:
                    if not hasattr(hijo, 'data'): 
                        token_str = str(hijo).strip().lower()
                        if token_str in ('.y.', 'y'):
                            operador_actual = 'AND'
                            contadores['AND'] += 1
                            if resultado_compuesto is False: skip_restante = True
                            huella[f"AND_{contadores['AND']}"] = "CORTOCIRCUITO" if skip_restante else "EVALUADO"
                        elif token_str in ('.o.', 'o'):
                            operador_actual = 'OR'
                            contadores['OR'] += 1
                            if resultado_compuesto is True: skip_restante = True
                            huella[f"OR_{contadores['OR']}"] = "CORTOCIRCUITO" if skip_restante else "EVALUADO"
                        continue

                    res_hijo = visitar(hijo, skip_restante)
                    
                    if resultado_compuesto is None:
                        resultado_compuesto = res_hijo
                    elif not skip_restante:
                        if operador_actual == 'AND': resultado_compuesto = resultado_compuesto and res_hijo
                        elif operador_actual == 'OR': resultado_compuesto = resultado_compuesto or res_hijo

                return resultado_compuesto

            # 5. COMPARACIONES ATÓMICAS (HOJAS)
            elif nodo.data.startswith('comparacion'):
                contadores['CONDICION'] += 1
                id_comp = contadores['CONDICION']

                # --- CORRECCIÓN: RECURSIÓN PREVIA ---
                # Antes de evaluar si la condición es verdadera o falsa, se obliga 
                # al visitante a revisar los componentes internos por si el desarrollador 
                # escondió un MIN, MAX, POS, NEG o ABS dentro de la pregunta lógica.
                if hasattr(nodo, 'children'):
                    for hijo in nodo.children:
                        visitar(hijo, forzar_skip)
                
                if forzar_skip:
                    huella[f"CONDICION_{id_comp}"] = "SKIPPED"
                    return False
                    
                try:
                    z3_expr = self.evaluador.evaluar(nodo)
                    res_z3 = modelo.evaluate(z3_expr, model_completion=True)
                    es_verdadero = z3.is_true(res_z3)
                    huella[f"CONDICION_{id_comp}"] = "TRUE" if es_verdadero else "FALSE"
                    return es_verdadero
                except Exception:
                    huella[f"CONDICION_{id_comp}"] = "ERR_EVAL"
                    return False

            # 6. FUNCIONES MATEMÁTICAS Y DIRECTAS (MIN, MAX, POS, NEG, ABS)
            elif nodo.data in ('funcion_matematica', 'funcion_directa'):
                try:
                    nombre_func = str(nodo.children[0]).upper()
                    
                    if nodo.data == 'funcion_matematica':
                        args_limpios = [h for h in nodo.children[2].children if str(h) != ';']
                    else:
                        args_limpios = [nodo.children[1]]
                        
                    if nombre_func in ('MIN', 'MAX', 'POS', 'NEG', 'ABS'):
                        contadores[nombre_func] += 1
                        id_func = f"{nombre_func}_{contadores[nombre_func]}"
                        
                        if forzar_skip:
                            huella[id_func] = "SKIPPED"
                        else:
                            if nombre_func in ('MIN', 'MAX') and len(args_limpios) >= 2:
                                val1 = self._extraer_valor_real(modelo.evaluate(self.evaluador.evaluar(args_limpios[0]), model_completion=True))
                                val2 = self._extraer_valor_real(modelo.evaluate(self.evaluador.evaluar(args_limpios[1]), model_completion=True))
                                gana = "ARG1" if (val1 <= val2 if nombre_func == 'MIN' else val1 >= val2) else "ARG2"
                                huella[id_func] = gana
                                
                            elif nombre_func in ('POS', 'ABS'):
                                val = self._extraer_valor_real(modelo.evaluate(self.evaluador.evaluar(args_limpios[0]), model_completion=True))
                                huella[id_func] = ">0" if val > 0 else "<=0"
                                
                            elif nombre_func == 'NEG':
                                val = self._extraer_valor_real(modelo.evaluate(self.evaluador.evaluar(args_limpios[0]), model_completion=True))
                                huella[id_func] = "<0" if val < 0 else ">=0"
                except Exception:
                    pass
                    
                # Se obliga al visitante a entrar en los argumentos de la función 
                # para descubrir funciones anidadas (ej. POS dentro de MIN).
                if nodo.data == 'funcion_matematica' and len(nodo.children) > 2:
                    visitar(nodo.children[2], forzar_skip)
                elif nodo.data == 'funcion_directa' and len(nodo.children) > 1:
                    visitar(nodo.children[1], forzar_skip)
                    
                return None

            # 7. PROPAGACIÓN DE BOOLEANOS (Para atravesar paréntesis y envoltorios)
            else:
                resultado_propagado = None
                if hasattr(nodo, 'children'):
                    for hijo in nodo.children:
                        res_hijo = visitar(hijo, forzar_skip)
                        # Propagamos hacia arriba el primer resultado lógico que encontremos en las entrañas
                        if res_hijo is not None and resultado_propagado is None:
                            resultado_propagado = res_hijo
                return resultado_propagado

        # Ejecución
        visitar(ast_tree)
        return huella

    def _extraer_valor_real(self, z3_val):
        """
        Convierte de forma segura los tipos de datos abstractos de Z3 a primitivas de Python.
        """
        if z3.is_rational_value(z3_val): 
            return float(z3_val.as_fraction())
        if z3.is_int(z3_val): 
            return z3_val.as_long()
        if z3.is_real(z3_val) or z3.is_algebraic_value(z3_val): 
            return float(z3_val.as_decimal(4).rstrip('?'))
        return 0

    def _encontrar_nodos_tipo(self, arbol, tipo_data):
        """
        Recorre el AST recursivamente buscando coincidencias por el identificador del nodo.
        """
        encontrados = []
        if hasattr(arbol, 'data'):
            if arbol.data == tipo_data:
                encontrados.append(arbol)
            for hijo in arbol.children:
                if hasattr(hijo, 'data') or hasattr(hijo, 'value'):
                    encontrados.extend(self._encontrar_nodos_tipo(hijo, tipo_data))
        return encontrados