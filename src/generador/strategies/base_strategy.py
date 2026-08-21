from abc import ABC, abstractmethod
import z3

class BaseStrategy(ABC):
    def __init__(self, evaluador, motor_z3, param_provider, rut_provider, config_motor=None, asts_dependencias=None):
        self.evaluador = evaluador
        self.motor = motor_z3
        self.param_provider = param_provider
        self.rut_provider = rut_provider
        self.config_motor = config_motor or {}
        self.asts_dependencias = asts_dependencias or []

    @abstractmethod
    def generar_casos(self, ast_tree, id_val):
        pass

    def _resolver_y_formatear(self, id_val, tipo_escenario, descripcion, error_esperado=None, codigo_objetivo=None, condicion_verificadora=None, ast_tree=None):
        if self.motor.solver.check() == z3.sat:
            modelo = self.motor.solver.model()

            datos_selenium = {}
            datos_vectores = {} 
            datos_parametros = {}
            datos_parametros_anteriores = {}
            valor_objetivo = 0 

            atributos_req = []
            atributos_prohibidos = []
            tipo_req = None
            subtipo_req = None

            # --- Invocamos la configuración de decimales ---
            usar_decimales = self.config_motor.get("usar_decimales", False)

            # Convertimos el AST a string para filtrar solo los parámetros usados
            ast_string = str(ast_tree).upper() if ast_tree else ""

            ast_string_principal = str(ast_tree).upper() if ast_tree else ""
            
            # SOLUCIÓN: Iteramos sobre variables_memoria en lugar de 'modelo'.
            # Z3 a veces oculta variables constantes del 'modelo', pero nuestra memoria no.
            for nombre, var_z3 in self.motor.variables_memoria.items():
                
                # Forzamos a Z3 a darnos el valor final de esta variable
                valor_crudo = modelo.evaluate(var_z3, model_completion=True)
                
                if nombre.startswith("IS_ATRIBUTO_"):
                    atr = nombre.replace("IS_ATRIBUTO_", "")
                    
                    # Como ahora sí es un Booleano nativo de Z3, usamos las funciones lógicas
                    if z3.is_true(valor_crudo): 
                        atributos_req.append(atr)
                    elif z3.is_false(valor_crudo): 
                        atributos_prohibidos.append(atr)
                    continue

                if nombre == "TIPO_[03]":
                    val_extraido = self._extraer_valor_real(valor_crudo)
                    tipo_req = int(val_extraido)  # Tolerancia Cero con Z3
                    continue

                if nombre == "SUBTIPO_[03]":
                    val_extraido = self._extraer_valor_real(valor_crudo)
                    subtipo_req = int(val_extraido)  # Tolerancia Cero con Z3
                    continue

                es_codigo = nombre.startswith('[') and nombre.endswith(']') and any(c.isdigit() for c in nombre)
                es_vector = nombre.startswith('VX') 
                es_parametro = nombre.startswith('P') and nombre[1:].isdigit() 
                
                if not (es_codigo or es_vector or es_parametro):
                    continue 
                
                # 1. Extraemos el valor matemático exacto 
                if z3.is_rational_value(valor_crudo):
                    val_exacto = float(valor_crudo.as_fraction())
                elif z3.is_real(valor_crudo) or z3.is_algebraic_value(valor_crudo):
                    val_exacto = float(valor_crudo.as_decimal(6).rstrip('?'))
                elif z3.is_int(valor_crudo):
                    val_exacto = float(valor_crudo.as_long())
                else:
                    val_exacto = 0.0
                    
                # 2. Aplicamos la regla de negocio de redondeo
                if es_parametro:
                    # BLINDAJE: Los parámetros conservan siempre su naturaleza original.
                    valor_limpio = int(val_exacto) if val_exacto.is_integer() else val_exacto
                else:
                    # ---> FIX REDONDEO TRIBUTARIO <---
                    # Z3 calcula libremente en Reales (ej. 12517561.8).
                    # Si no usamos decimales, aplicamos Round Half Up en lugar de truncar ciegamente con int()
                    if usar_decimales:
                        valor_limpio = val_exacto
                    else:
                        valor_limpio = int(val_exacto + 0.5) if val_exacto >= 0 else int(val_exacto - 0.5)
                    
                if codigo_objetivo and nombre == codigo_objetivo:
                    valor_objetivo = valor_limpio
                elif es_vector:
                    datos_vectores[nombre] = valor_limpio
                elif es_parametro:
                    if nombre.upper() in ast_string_principal:
                        datos_parametros[nombre] = valor_limpio
                    else:
                        # Todo parámetro que venga inyectado de a.2, a.3, etc., se va al debug
                        datos_parametros_anteriores[nombre] = valor_limpio
                elif es_codigo:
                    # ---> FIX SPARSITY VISUAL: Limpieza inteligente del JSON <---
                    es_principal = nombre in getattr(self.motor, 'vars_principales', set())
                    
                    # Ocultamos los ceros absolutos SOLO si provienen de dependencias inyectadas.
                    # Mantenemos los ceros de las variables principales (ej. [465]=0) para que QA vea el contexto.
                    if valor_limpio == 0 and not es_principal:
                        continue
                        
                    datos_selenium[nombre] = valor_limpio

            # Consolidamos el AST principal y sus dependencias en una sola lista
            todos_los_asts = [ast_tree] + self.asts_dependencias

            # ---> INICIO BLOQUE SHIFT-LEFT: CLASIFICACIÓN Y LIMPIEZA QUIRÚRGICA <---
            editables_originales = {}
            autocalculados_originales = {}
            editables_inyectados = {}
            inputs_selenium = {}
            
            # Solo analizaremos los ASTs que sobrevivieron al filtro cascada para el RUT
            asts_activos = []
            
            if ast_tree:
                asts_activos.append(ast_tree)
                # 1. Variables de la regla principal
                vars_principal = self._obtener_variables_activas(modelo, ast_tree)
                if codigo_objetivo:
                    vars_principal.add(codigo_objetivo)
                    
                # 2. Variables de las dependencias inyectadas (Filtro en Cascada)
                vars_totales = set(vars_principal)
                hubo_cambios = True
                while hubo_cambios:
                    hubo_cambios = False
                    for ast_dep in self.asts_dependencias:
                        if not ast_dep: continue
                        
                        # Identificamos a quién le pertenece este árbol de dependencia
                        cod_target = None
                        # FIX: El nodo raíz es 'validacion', usamos el buscador para hallar 'autocalculado'
                        nodos_auto = self._encontrar_nodos_tipo(ast_dep, 'autocalculado')
                        if nodos_auto:
                            cod_bruto = str(nodos_auto[0].children[0]).replace('[', '').replace(']', '').strip()
                            cod_target = f"[{cod_bruto}]"
                            
                        # Solo activamos la rama de la dependencia si la celda objetivo realmente sobrevivió
                        if cod_target and cod_target in vars_totales:
                            if ast_dep not in asts_activos:
                                asts_activos.append(ast_dep)
                                
                            nuevas_vars = self._obtener_variables_activas(modelo, ast_dep)
                            if not nuevas_vars.issubset(vars_totales):
                                vars_totales.update(nuevas_vars)
                                hubo_cambios = True
                
                vars_inyectadas = vars_totales - vars_principal
                variables_activas = vars_totales
                
                datos_selenium = {k: v for k, v in datos_selenium.items() if k in variables_activas}
                datos_vectores = {k: v for k, v in datos_vectores.items() if k in variables_activas}
                datos_parametros = {k: v for k, v in datos_parametros.items() if k in variables_activas}

                # 4. Clasificamos los datos_selenium según el requerimiento de QA
                for clave, valor in datos_selenium.items():
                    cod_limpio = clave.replace('[', '').replace(']', '')
                    es_auto = self.motor.catalogo_signos.get(cod_limpio, {}).get("autocalculado", False)
                    
                    if clave in vars_principal:
                        if es_auto:
                            autocalculados_originales[clave] = valor
                        else:
                            editables_originales[clave] = valor
                            inputs_selenium[clave] = valor # Selenium solo digita editables
                    elif clave in vars_inyectadas:
                        if es_auto:
                            # Prevenimos "fantasmas" agrupando dependencias autocalculadas aquí
                            autocalculados_originales[clave] = valor
                        else:
                            editables_inyectados[clave] = valor
                            inputs_selenium[clave] = valor # Selenium también digita inyecciones
                            
            # Análisis de requerimientos reales de RUT basados SOLO en los ASTs que sobrevivieron ---
            usa_tipo = False
            usa_subtipo = False
            for ast_actual in asts_activos:
                if ast_actual:
                    nodos_rut = self._encontrar_nodos_tipo(ast_actual, 'funcion_rut')
                    for n in nodos_rut:
                        if hasattr(n, 'children') and len(n.children) > 0:
                            func_name = str(n.children[0]).upper()
                            if func_name == 'TIPO': usa_tipo = True
                            if func_name == 'SUBTIPO': usa_subtipo = True

            # Construimos el perfil filtrando las invenciones de Z3
            perfil_rut = {
                "tipo": tipo_req if usa_tipo and tipo_req is not None else "CUALQUIERA",
                "subtipo": subtipo_req if usa_subtipo and subtipo_req is not None else "CUALQUIERA",
                "atributos_requeridos": atributos_req,
                "atributos_prohibidos": atributos_prohibidos
            }
            
            # Si el perfil no exige absolutamente nada, lo simplificamos
            if not usa_tipo and not usa_subtipo and not atributos_req and not atributos_prohibidos:
                perfil_rut = "CUALQUIER_RUT"
            # ---> FIN BLOQUE SHIFT-LEFT <---

            if condicion_verificadora is not None and error_esperado is not None:
                sustituciones = []
                for variable_z3 in modelo:
                    if variable_z3.arity() > 0: continue
                    nombre = variable_z3.name()
                    
                    if nombre in datos_selenium:
                        sustituciones.append((variable_z3(), z3.RealVal(datos_selenium[nombre])))
                    elif nombre in datos_vectores:
                        sustituciones.append((variable_z3(), z3.RealVal(datos_vectores[nombre])))
                    elif codigo_objetivo and nombre == codigo_objetivo:
                        sustituciones.append((variable_z3(), z3.RealVal(valor_objetivo)))
                    else:
                        sustituciones.append((variable_z3(), modelo[variable_z3]))
                        
                condicion_evaluada = z3.simplify(z3.substitute(condicion_verificadora, *sustituciones))
                
                if z3.is_true(condicion_evaluada): resultado_real_redondeado = "BUENO"
                elif z3.is_false(condicion_evaluada): resultado_real_redondeado = "MENSAJE"
                else: resultado_real_redondeado = error_esperado
                    
                if error_esperado != resultado_real_redondeado:
                    error_esperado = resultado_real_redondeado
                    descripcion += f" [Auto-Corregido: El truncamiento decimal altera el resultado en UI a {error_esperado}]"

            huella_logica = {}
            if ast_tree:
                huella_logica = self._calcular_huella_logica(modelo, ast_tree)
                
            # Sello artificial para Cotas (BVA) y Cálculos Exactos
            if "LINEAL" in tipo_escenario:
                if "LIMITE_EXACTO" in tipo_escenario: huella_logica["BVA_RAIZ"] = "EXACTO"
                elif "EXCEDE_LIMITE" in tipo_escenario: huella_logica["BVA_RAIZ"] = "EXCESO"
                elif "BAJO_LIMITE" in tipo_escenario: huella_logica["BVA_RAIZ"] = "BAJO"
                elif tipo_escenario == "CALCULO_LINEAL_EXACTO": huella_logica["CALCULO_RAIZ"] = "POSITIVO"
                
            # Sello artificial para nuestro nuevo ataque matemático
            if tipo_escenario == "CALCULO_RESULTADO_NEGATIVO":
                huella_logica["CALCULO_RAIZ"] = "NEGATIVO"

            # Huella lógica para escenarios de cálculo en límites
            if "EN_EL_LIMITE" in tipo_escenario: 
                huella_logica["ZONA_LIMITE"] = "EXACTO"
            elif "BAJO_EL_LIMITE" in tipo_escenario: 
                huella_logica["ZONA_LIMITE"] = "INFERIOR"
            elif "SOBRE_EL_LIMITE" in tipo_escenario: 
                huella_logica["ZONA_LIMITE"] = "SUPERIOR"

            rut_final = "DEFAULT_RUT"
            mensaje_error_rut = None
            estado_final = "ENRIQUECIDO"

            if self.rut_provider:
                rut_final = self.rut_provider.obtener_rut(atributos_req, atributos_prohibidos, tipo_req, subtipo_req)
                
                # --- NUEVO ENFOQUE FAIL-SOFT ---
                if rut_final == "SIN_RUT_VALIDO":
                    rut_final = "FALTA_RUT"
                    estado_final = "ERROR_RUT"
                    mensaje_error_rut = (
                        f"❌ BLOQUEO: No hay RUTs disponibles.\n"
                        f"Detalle: La validación requiere un contribuyente con Tipo: {tipo_req or 'Cualquiera'}, "
                        f"Subtipo: {subtipo_req or 'Cualquiera'}, Atributos Requeridos: {atributos_req}, Prohibidos: {atributos_prohibidos}.\n"
                        f"Sugerencia: Agrega un RUT que cumpla estas condiciones en el Catálogo."
                    )

            resultado_json = {
                "id_validacion": id_val,
                "tipo_escenario": tipo_escenario,
                "descripcion_qa": descripcion,
                "rut": rut_final,
                "inputs_matematicos": datos_selenium,
                "inputs": inputs_selenium,
                "detalle_inputs": {
                    "editables_originales": editables_originales,
                    "autocalculados_originales": autocalculados_originales,
                    "editables_inyectados": editables_inyectados
                },
                "vectores": datos_vectores,
                "parametros": datos_parametros,
                "parametros_anteriores": datos_parametros_anteriores,
                "resultado_esperado": error_esperado,
                "huella_logica": huella_logica,
                "estado_interno": estado_final # <--- AHORA USA EL ESTADO DINÁMICO
            }

            # Inyectamos el error solo si existe, para que el Frontend lo pinte de rojo
            if mensaje_error_rut:
                resultado_json["error"] = mensaje_error_rut

            # Restricción solicitada: Solo inyectar en las validaciones N y M
            if id_val.lower().startswith(('n.', 'm.')):
                resultado_json["perfil_rut_requerido"] = perfil_rut

            if codigo_objetivo:
                resultado_json["objetivo"] = {"codigo": codigo_objetivo, "valor": valor_objetivo}

            return resultado_json
        else:
            return {"id_validacion": id_val, "tipo_escenario": tipo_escenario, "descripcion_qa": descripcion, "estado_interno": "INSATISFACTIBLE"}

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
                                
                            elif nombre_func in ('POS', 'NEG', 'ABS'):
                                val = self._extraer_valor_real(modelo.evaluate(self.evaluador.evaluar(args_limpios[0]), model_completion=True))
                                if val > 0:
                                    huella[id_func] = ">0"
                                elif val < 0:
                                    huella[id_func] = "<0"
                                else:
                                    huella[id_func] = "=0"
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

    # =================================================================
    # COMENTADO POR SEGURIDAD HASTA VALIDAR EL ANTI-MASKING
    # =================================================================
    """
    def _obtener_variables_activas(self, modelo, ast_tree):
        """"""
        Intérprete perezoso especializado en recolección de variables activas.
        Ignora las ramas de condicionales que evalúan como falso en el modelo de Z3.
        """"""
        variables = set()

        def procesar_token_como_variable(token_str):
            limpio = token_str.strip().upper().replace('"', '')
            if limpio:
                if limpio.isdigit(): 
                    variables.add(f"[{limpio}]")
                elif limpio.startswith('[') and limpio.endswith(']'):
                    variables.add(limpio)
                elif limpio.startswith('P') and limpio[1:].isdigit(): 
                    variables.add(limpio)
                elif limpio.startswith('VX'): 
                    variables.add(limpio)

        def visitar(nodo, forzar_skip=False):
            if not hasattr(nodo, 'data'):
                if not forzar_skip: 
                    procesar_token_como_variable(str(nodo))
                return None

            if nodo.data == 'condicional':
                res_cond = self._evaluar_condicion_z3(nodo.children[0], modelo)
                visitar(nodo.children[0], forzar_skip)
                skip_entonces = forzar_skip or not res_cond
                skip_sino = forzar_skip or res_cond
                
                if len(nodo.children) > 1: visitar(nodo.children[1], skip_entonces)
                if len(nodo.children) > 2: visitar(nodo.children[2], skip_sino)
                return

            elif nodo.data == 'caso_trailing':
                res_cond = self._evaluar_condicion_z3(nodo.children[-1], modelo)
                visitar(nodo.children[-1], forzar_skip)
                skip_expr = forzar_skip or not res_cond
                visitar(nodo.children[0], skip_expr)
                return

            elif nodo.data == 'casos_trailing':
                skip_restantes = forzar_skip
                for hijo in nodo.children:
                    if getattr(hijo, 'data', '') == 'caso_trailing':
                        res_cond = self._evaluar_condicion_z3(hijo.children[-1], modelo)
                        visitar(hijo, skip_restantes)
                        if res_cond and not skip_restantes: skip_restantes = True
                    elif getattr(hijo, 'data', '') == 'caso_default':
                        visitar(hijo.children[-1], skip_restantes)
                return

            elif nodo.data == 'condicion_logica':
                resultado_compuesto = None
                skip = forzar_skip
                op = None
                for hijo in nodo.children:
                    if not hasattr(hijo, 'data'):
                        t = str(hijo).strip().lower()
                        if t in ('.y.', 'y'): 
                            op = 'AND'
                            skip = skip or (resultado_compuesto is False)
                        elif t in ('.o.', 'o'): 
                            op = 'OR'
                            skip = skip or (resultado_compuesto is True)
                        continue
                        
                    res_hijo = self._evaluar_condicion_z3(hijo, modelo)
                    visitar(hijo, skip)
                    
                    if resultado_compuesto is None: 
                        resultado_compuesto = res_hijo
                    elif not skip:
                        if op == 'AND': resultado_compuesto = resultado_compuesto and res_hijo
                        elif op == 'OR': resultado_compuesto = resultado_compuesto or res_hijo
                return

            # Propagación genérica si no es un nodo de control
            for hijo in getattr(nodo, 'children', []): 
                visitar(hijo, forzar_skip)

        visitar(ast_tree)
        return variables

    def _evaluar_condicion_z3(self, nodo, modelo):
        """"""
        Evalúa un nodo lógico directamente contra el modelo actual para decidir
        si el recolector de variables debe entrar a la rama o ignorarla.
        """"""
        try:
            expr = self.evaluador.evaluar(nodo)
            res = modelo.evaluate(expr, model_completion=True)
            return z3.is_true(res)
        except Exception:
            return False
    """

    def _obtener_variables_activas(self, modelo, ast_tree):
        """
        Recolector Incondicional (Anti-Masking).
        Extrae TODAS las variables presentes en el AST, sin importar si su
        rama fue activada o no por Z3. Esto garantiza que Selenium reciba 
        los inputs necesarios para probar las ramas muertas (Falsos Positivos).
        """
        variables = set()

        def procesar_token_como_variable(token_str):
            limpio = token_str.strip().upper().replace('"', '')
            if limpio:
                if limpio.isdigit(): 
                    variables.add(f"[{limpio}]")
                elif limpio.startswith('[') and limpio.endswith(']'):
                    variables.add(limpio)
                elif limpio.startswith('P') and limpio[1:].isdigit(): 
                    variables.add(limpio)
                elif limpio.startswith('VX'): 
                    variables.add(limpio)

        def visitar(nodo):
            if not hasattr(nodo, 'data'):
                procesar_token_como_variable(str(nodo))
                return
            for hijo in getattr(nodo, 'children', []): 
                visitar(hijo)

        visitar(ast_tree)
        return variables