import z3
import itertools
from src.generador.strategies.base_strategy import BaseStrategy

class ImplicationBuilder(BaseStrategy):
    """
    Estrategia Experta para Validaciones Tipo D y E (Implicaciones Lógicas).
    Genera matrices de pruebas basadas en Tablas de Verdad usando un
    Producto Cartesiano MCDC para garantizar que las dependencias
    obligatorias disparen los bloqueos correctos.
    """

    def generar_casos(self, ast_tree, id_val):
        casos = []
        
        # --- NUEVO: Soporte dual para Validaciones D/E (Implicación) y M (Condicional) ---
        nodo_impl = self._encontrar_nodos_tipo(ast_tree, 'implicacion')
        if nodo_impl:
            gatillo_ast = nodo_impl[0].children[0]
            requisito_ast = nodo_impl[0].children[2] # Índice 2 para saltar el token '=>'
        else:
            nodo_cond = self._encontrar_nodos_tipo(ast_tree, 'condicional')
            if nodo_cond:
                # En un condicional, el hijo[0] es el SI, y el hijo[1] es el ENTONCES
                gatillo_ast = nodo_cond[0].children[0]
                requisito_ast = nodo_cond[0].children[1]
            else:
                return [{"id_validacion": id_val, "error": "No se encontró nodo de implicación ni condicional en el AST."}]

        z3_gatillo = self.evaluador.evaluar(gatillo_ast)
        z3_requisito = self.evaluador.evaluar(requisito_ast)

        premisas_universales = []
        z3_declaraciones = []
        nodos_var = self._encontrar_nodos_tipo(ast_tree, 'declaracion_variable')
        for nodo_var in nodos_var:
            z3_var = self.evaluador.evaluar(nodo_var)
            premisas_universales.append(z3_var)
            z3_declaraciones.append(z3_var)

        # Generamos los universos MCDC aislando la izquierda (gatillo) y derecha (requisito)
        gatillo_verdadero = self._desglosar_condicion_verdadera(z3_gatillo)
        gatillo_falso = self._desglosar_condicion_falsa(z3_gatillo)
        
        requisito_verdadero = self._desglosar_condicion_verdadera(z3_requisito)
        requisito_falso = self._desglosar_condicion_falsa(z3_requisito)

        # --- EXPANSIÓN MCDC DE VARIABLES (ITE LOCKING) ---
        # Buscamos todas las ramas condicionales anidadas dentro de las variables (ej: [m] = SI... ENTONCES...)
        rutas_internas_totales = [[]] 
        for z3_dec in z3_declaraciones:
            rutas_ite = self._extraer_rutas_ite(z3_dec)
            if len(rutas_ite) > 1: # Si hay más de una ruta, hubo al menos un IF
                # Producto cartesiano de las rutas (si hay múltiples variables condicionales)
                rutas_internas_totales = [r_base + r_nueva for r_base in rutas_internas_totales for r_nueva in rutas_ite]

        # --- CASO 1: FLUJO IDEAL (CUMPLE Y CUMPLE) ---
        for i, var_g in enumerate(gatillo_verdadero, 1):
            for j, var_r in enumerate(requisito_verdadero, 1):
                # Cruzamos contra TODAS las ramas condicionales internas descubiertas
                for idx_ruta, ruta_ite in enumerate(rutas_internas_totales, 1):
                    sufijo = f"_{i}_{j}_{idx_ruta}" if len(gatillo_verdadero) > 1 or len(requisito_verdadero) > 1 or len(rutas_internas_totales) > 1 else ""
                    desc = f"Gatillo activo ({var_g['desc']}) Y Requisito cumplido ({var_r['desc']})"
                    if len(ruta_ite) > 0: desc += f" [Forzando Rama Interna {idx_ruta}]"
                    
                    casos.append(
                        self._ejecutar_escenario_aislado(
                            premisas_universales + ruta_ite + [var_g["restriccion"], var_r["restriccion"]], 
                            lambda d=desc, s=sufijo: self._resolver_y_formatear(
                                id_val, f"CUMPLE_CONDICION{s}", d, "BUENO", ast_tree=ast_tree)
                        )
                    )

        # --- CASO 2: QUIEBRE DE REGLA (FALLA ESPERADA) ---
        for i, var_g in enumerate(gatillo_verdadero, 1):
            for j, var_r in enumerate(requisito_falso, 1):
                for idx_ruta, ruta_ite in enumerate(rutas_internas_totales, 1):
                    sufijo = f"_{i}_{j}_{idx_ruta}" if len(gatillo_verdadero) > 1 or len(requisito_falso) > 1 or len(rutas_internas_totales) > 1 else ""
                    desc = f"Se fuerza error: Gatillo activo ({var_g['desc']}) PERO Requisito falla ({var_r['desc']})"
                    if len(ruta_ite) > 0: desc += f" [Forzando Rama Interna {idx_ruta}]"
                    
                    casos.append(
                        self._ejecutar_escenario_aislado(
                            premisas_universales + ruta_ite + [var_g["restriccion"], var_r["restriccion"]], 
                            lambda d=desc, s=sufijo: self._resolver_y_formatear(
                                id_val, f"INCUMPLE_CONDICION{s}", d, "MENSAJE", ast_tree=ast_tree)
                        )
                    )

        # --- CASO 3: OMISIÓN (NO APLICA LA REGLA) ---
        for i, var_g in enumerate(gatillo_falso, 1):
            sufijo = f"_{i}" if len(gatillo_falso) > 1 else ""
            desc = f"La regla no aplica: Gatillo inactivo ({var_g['desc']})"
            
            casos.append(
                self._ejecutar_escenario_aislado(
                    premisas_universales + [var_g["restriccion"]], 
                    lambda d=desc, s=sufijo: self._resolver_y_formatear(
                        id_val, f"NO_APLICA{s}", d, "BUENO", ast_tree=ast_tree)
                )
            )

        # --- CASO 4: FRONTERAS MATEMÁTICAS INTERNAS (AISLAMIENTO Y PATH LOCKING) ---
        nodos_func = self._encontrar_nodos_tipo(nodo_impl, 'funcion_matematica') + self._encontrar_nodos_tipo(nodo_impl, 'funcion_directa')
        
        if nodos_func:
            gap = 2
            restriccion_gatillo = gatillo_verdadero[0]["restriccion"] if gatillo_verdadero else z3.BoolVal(True)
            z3_requisito_eval = self.evaluador.evaluar(requisito_ast)
            
            vars_req_totales = self._extraer_vars_z3(requisito_ast)
            
            func_names = [str(n.children[0]).upper() for n in nodos_func]
            func_totals = {name: func_names.count(name) for name in set(func_names)}
            func_current = {name: 0 for name in func_totals}
            
            for nodo_func in nodos_func:
                func_name = str(nodo_func.children[0]).upper()
                func_current[func_name] += 1
                sufijo = f"_{func_current[func_name]}" if func_totals[func_name] > 1 else ""
                
                if nodo_func.data == 'funcion_matematica':
                    args_limpios = [h for h in nodo_func.children[2].children if str(h) != ';']
                else:
                    args_limpios = [nodo_func.children[1]]

                # PATH EXECUTION LOCKING
                guardias_activas = self._obtener_guardias_nodo(requisito_ast, nodo_func) or []
                base_cond = premisas_universales + [restriccion_gatillo, z3_requisito_eval] + guardias_activas

                # AISLAMIENTO ANTI-ENMASCARAMIENTO
                vars_func_actual = self._extraer_vars_z3(nodo_func)
                restricciones_aislamiento = []
                for nombre, var_z3 in vars_req_totales.items():
                    if nombre not in vars_func_actual:
                        restricciones_aislamiento.append(var_z3 == 0)

                def ejecutar_con_aislamiento(restriccion_frontera, lambda_formateador):
                    res = self._ejecutar_escenario_aislado(base_cond + restricciones_aislamiento + [restriccion_frontera], lambda_formateador)
                    if res and res.get("estado_interno") == "INSATISFACTIBLE":
                        res = self._ejecutar_escenario_aislado(base_cond + [restriccion_frontera], lambda_formateador)
                    return res

                if func_name == 'ABS':
                    z3_arg = self.evaluador.evaluar(args_limpios[0])
                    casos.append(ejecutar_con_aislamiento(z3_arg <= -gap, lambda n=func_name, s=sufijo: self._resolver_y_formatear(id_val, f"FUNC_{n}{s}_ENTRADA_NEGATIVA", f"El valor interno de {n} es negativo, aislando y forzando conversión.", "BUENO", ast_tree=ast_tree)))
                    casos.append(ejecutar_con_aislamiento(z3_arg >= gap, lambda n=func_name, s=sufijo: self._resolver_y_formatear(id_val, f"FUNC_{n}{s}_ENTRADA_POSITIVA", f"El valor interno de {n} es positivo, manteniendo su valor.", "BUENO", ast_tree=ast_tree)))
                    
                elif func_name == 'POS':
                    z3_arg = self.evaluador.evaluar(args_limpios[0])
                    casos.append(ejecutar_con_aislamiento(z3_arg >= gap, lambda n=func_name, s=sufijo: self._resolver_y_formatear(id_val, f"FUNC_{n}{s}_MAYOR_CERO", f"El valor interno de {n} es positivo aislando la ruta.", "BUENO", ast_tree=ast_tree)))
                    casos.append(ejecutar_con_aislamiento(z3_arg <= -gap, lambda n=func_name, s=sufijo: self._resolver_y_formatear(id_val, f"FUNC_{n}{s}_MENOR_CERO", f"El valor interno de {n} es negativo, forzando a 0.", "BUENO", ast_tree=ast_tree)))
                    
                elif func_name == 'NEG':
                    z3_arg = self.evaluador.evaluar(args_limpios[0])
                    casos.append(ejecutar_con_aislamiento(z3_arg <= -gap, lambda n=func_name, s=sufijo: self._resolver_y_formatear(id_val, f"FUNC_{n}{s}_MENOR_CERO", f"El valor interno de {n} es negativo aislando su valor absoluto.", "BUENO", ast_tree=ast_tree)))
                    casos.append(ejecutar_con_aislamiento(z3_arg >= gap, lambda n=func_name, s=sufijo: self._resolver_y_formatear(id_val, f"FUNC_{n}{s}_MAYOR_CERO", f"El valor interno de {n} es positivo, forzando a 0.", "BUENO", ast_tree=ast_tree)))
                    
                elif func_name in ('MIN', 'MAX'):
                    z3_arg1, z3_arg2 = self.evaluador.evaluar(args_limpios[0]), self.evaluador.evaluar(args_limpios[1])
                    if func_name == 'MIN':
                        casos.append(ejecutar_con_aislamiento(z3_arg1 <= (z3_arg2 - gap), lambda n=func_name, s=sufijo: self._resolver_y_formatear(id_val, f"FUNC_{n}{s}_IZQ", f"El límite {n} toma el valor izquierdo.", "BUENO", ast_tree=ast_tree)))
                        casos.append(ejecutar_con_aislamiento(z3_arg1 >= (z3_arg2 + gap), lambda n=func_name, s=sufijo: self._resolver_y_formatear(id_val, f"FUNC_{n}{s}_DER", f"El límite {n} toma el valor derecho.", "BUENO", ast_tree=ast_tree)))
                    else:
                        casos.append(ejecutar_con_aislamiento(z3_arg1 >= (z3_arg2 + gap), lambda n=func_name, s=sufijo: self._resolver_y_formatear(id_val, f"FUNC_{n}{s}_IZQ", f"El límite {n} toma el valor izquierdo.", "BUENO", ast_tree=ast_tree)))
                        casos.append(ejecutar_con_aislamiento(z3_arg1 <= (z3_arg2 - gap), lambda n=func_name, s=sufijo: self._resolver_y_formatear(id_val, f"FUNC_{n}{s}_DER", f"El límite {n} toma el valor derecho.", "BUENO", ast_tree=ast_tree)))

        # Limpieza, Filtrado de Contradicciones y Deduplicación
        casos_validos = []
        inputs_vistos = set()
        idx_real = 1
        
        for caso in casos:
            if caso and caso.get("estado_interno") != "INSATISFACTIBLE":
                # ---> CORRECCIÓN: Incluimos los vectores en la firma de unicidad <---
                firma_unica = (
                    caso.get("rut"), 
                    tuple(sorted(caso.get("inputs", {}).items())),
                    tuple(sorted(caso.get("vectores", {}).items())) # <-- El eslabón perdido
                )
                if firma_unica not in inputs_vistos:
                    inputs_vistos.add(firma_unica)
                    caso["id_validacion"] = f"{id_val}.{idx_real}"
                    idx_real += 1
                    casos_validos.append(caso)

        return casos_validos if casos_validos else [{"id_validacion": id_val, "error": "Contradicción matemática. Revisar si la implicación es posible."}]

    # ==========================================
    # HERRAMIENTAS INTERNAS DE DESGLOSE MCDC
    # ==========================================

    def _encontrar_nodos_tipo(self, arbol, tipo_data):
        encontrados = []
        if hasattr(arbol, 'data'):
            if arbol.data == tipo_data:
                encontrados.append(arbol)
            for hijo in arbol.children:
                if hasattr(hijo, 'data') or hasattr(hijo, 'value'):
                    encontrados.extend(self._encontrar_nodos_tipo(hijo, tipo_data))
        return encontrados

    def _desglosar_condicion_verdadera(self, z3_cond):
        import itertools
        if not z3.is_app(z3_cond):
            return [{"restriccion": z3_cond, "desc": "La condición se cumple."}]
            
        kind = z3_cond.decl().kind()
        
        # BVA PARA COMPARACIONES ATÓMICAS EN REQUISITOS (VERDADERAS)
        if kind in (z3.Z3_OP_LT, z3.Z3_OP_LE, z3.Z3_OP_GT, z3.Z3_OP_GE, z3.Z3_OP_EQ):
            izq, der = z3_cond.children()[0], z3_cond.children()[1]
            if kind == z3.Z3_OP_LT:   restr_bva = (izq == der - 1)
            elif kind == z3.Z3_OP_LE: restr_bva = (izq == der)
            elif kind == z3.Z3_OP_GT: 
                # Garantizamos que la celda real tome un valor >= 1
                restr_bva = z3.And(izq > der, izq >= 1)
            elif kind == z3.Z3_OP_GE: restr_bva = (izq == der)
            else:                     restr_bva = (izq == der)
            return [{"restriccion": restr_bva, "desc": "La sub-condición se cumple en su frontera exacta."}]

        elif kind == z3.Z3_OP_OR:
            variaciones = []
            hijos = z3_cond.children()
            for i, hijo_actual in enumerate(hijos):
                vars_hijo = self._desglosar_condicion_verdadera(hijo_actual)
                for var in vars_hijo:
                    restricciones = [var["restriccion"]]
                    for j, otro_hijo in enumerate(hijos):
                        if i != j:
                            restricciones.append(z3.Not(otro_hijo))
                    variaciones.append({
                        "restriccion": z3.And(*restricciones),
                        "desc": f"Bloque OR (opción {i+1}): {var['desc']}"
                    })
            return variaciones
            
        elif kind == z3.Z3_OP_AND:
            variaciones_hijos = [self._desglosar_condicion_verdadera(h) for h in z3_cond.children()]
            combinaciones = list(itertools.product(*variaciones_hijos))
            
            variaciones_finales = []
            for idx, combo in enumerate(combinaciones):
                restricciones = [item["restriccion"] for item in combo]
                variaciones_finales.append({
                    "restriccion": z3.And(*restricciones),
                    "desc": "Todas las sub-condiciones del AND se cumplen."
                })
            return variaciones_finales
            
        elif kind == z3.Z3_OP_NOT:
            return self._desglosar_condicion_falsa(z3_cond.children()[0])
            
        elif kind == z3.Z3_OP_ITE:
            cond = z3_cond.children()[0]
            then_expr = z3_cond.children()[1]
            else_expr = z3_cond.children()[2]
            
            variaciones = []
            vars_cond_v = self._desglosar_condicion_verdadera(cond)
            vars_then_v = self._desglosar_condicion_verdadera(then_expr)
            for vc in vars_cond_v:
                for vt in vars_then_v:
                    variaciones.append({
                        "restriccion": z3.And(vc["restriccion"], vt["restriccion"]),
                        "desc": f"IF cumple [{vc['desc']}] -> ENTONCES [{vt['desc']}]"
                    })
                    
            vars_cond_f = self._desglosar_condicion_falsa(cond)
            vars_else_v = self._desglosar_condicion_verdadera(else_expr)
            for vc in vars_cond_f:
                for ve in vars_else_v:
                    variaciones.append({
                        "restriccion": z3.And(vc["restriccion"], ve["restriccion"]),
                        "desc": f"IF falla [{vc['desc']}] -> SINO [{ve['desc']}]"
                    })
                    
            return variaciones
            
        else:
            return [{"restriccion": z3_cond, "desc": "La condición se cumple."}]

    def _desglosar_condicion_falsa(self, z3_cond):
        import itertools
        if not z3.is_app(z3_cond):
            return [{"restriccion": z3.Not(z3_cond), "desc": "La condición no se cumple."}]
            
        kind = z3_cond.decl().kind()
        
        # BVA PARA FALSA CONMUTACIÓN
        if kind in (z3.Z3_OP_LT, z3.Z3_OP_LE, z3.Z3_OP_GT, z3.Z3_OP_GE, z3.Z3_OP_EQ):
            izq, der = z3_cond.children()[0], z3_cond.children()[1]
            if kind == z3.Z3_OP_LT:   restr_bva = (izq == der)
            elif kind == z3.Z3_OP_LE: restr_bva = (izq == der + 1)
            elif kind == z3.Z3_OP_GT: restr_bva = (izq == der)
            elif kind == z3.Z3_OP_GE: restr_bva = (izq == der - 1)
            elif kind == z3.Z3_OP_EQ: restr_bva = (izq != der) # <-- ESTA ES LA MAGIA PARA LOS SUBTIPOS
            else:                     restr_bva = (izq != der) # <-- IGUAL AQUÍ
            return [{"restriccion": restr_bva, "desc": "La sub-condición falla en su frontera exacta."}]

        elif kind == z3.Z3_OP_AND:
            variaciones = []
            hijos = z3_cond.children()
            for i, hijo_actual in enumerate(hijos):
                vars_hijo_falso = self._desglosar_condicion_falsa(hijo_actual)
                for var in vars_hijo_falso:
                    restricciones = [var["restriccion"]]
                    for j, otro_hijo in enumerate(hijos):
                        if i != j:
                            restricciones.append(otro_hijo) 
                    variaciones.append({
                        "restriccion": z3.And(*restricciones),
                        "desc": f"Bloque AND falla (sub-condición {i+1}): {var['desc']}"
                    })
            return variaciones
            
        elif kind == z3.Z3_OP_OR:
            variaciones_hijos = [self._desglosar_condicion_falsa(h) for h in z3_cond.children()]
            combinaciones = list(itertools.product(*variaciones_hijos))
            
            variaciones_finales = []
            for idx, combo in enumerate(combinaciones):
                restricciones = [item["restriccion"] for item in combo]
                variaciones_finales.append({
                    "restriccion": z3.And(*restricciones),
                    "desc": "Todas las opciones del OR son falsas."
                })
            return variaciones_finales
            
        elif kind == z3.Z3_OP_NOT:
            return self._desglosar_condicion_verdadera(z3_cond.children()[0])
            
        elif kind == z3.Z3_OP_ITE:
            cond = z3_cond.children()[0]
            then_expr = z3_cond.children()[1]
            else_expr = z3_cond.children()[2]
            
            variaciones = []
            vars_cond_v = self._desglosar_condicion_verdadera(cond)
            vars_then_f = self._desglosar_condicion_falsa(then_expr)
            for vc in vars_cond_v:
                for vt in vars_then_f:
                    variaciones.append({
                        "restriccion": z3.And(vc["restriccion"], vt["restriccion"]),
                        "desc": f"IF cumple [{vc['desc']}] -> ENTONCES FALLA [{vt['desc']}]"
                    })
                    
            vars_cond_f = self._desglosar_condicion_falsa(cond)
            vars_else_f = self._desglosar_condicion_falsa(else_expr)
            for vc in vars_cond_f:
                for ve in vars_else_f:
                    variaciones.append({
                        "restriccion": z3.And(vc["restriccion"], ve["restriccion"]),
                        "desc": f"IF falla [{vc['desc']}] -> SINO FALLA [{ve['desc']}]"
                    })
                    
            return variaciones
            
        else:
            return [{"restriccion": z3.Not(z3_cond), "desc": "La condición no se cumple."}]

    def _obtener_guardias_nodo(self, nodo_actual, nodo_objetivo, guardias_actuales=None):
        """Busca el camino exacto hacia un nodo y extrae los IFs necesarios para alcanzarlo."""
        if guardias_actuales is None:
            guardias_actuales = []
            
        if nodo_actual is nodo_objetivo:
            return guardias_actuales
            
        if not hasattr(nodo_actual, 'children'):
            return None
            
        if getattr(nodo_actual, 'data', '') == 'condicional':
            cond_ast = nodo_actual.children[0]
            cond_z3 = self.evaluador.evaluar(cond_ast)
            
            rama_v = nodo_actual.children[1]
            res_v = self._obtener_guardias_nodo(rama_v, nodo_objetivo, guardias_actuales + [cond_z3])
            if res_v is not None: return res_v
            
            if len(nodo_actual.children) > 2:
                rama_f = nodo_actual.children[2]
                res_f = self._obtener_guardias_nodo(rama_f, nodo_objetivo, guardias_actuales + [z3.Not(cond_z3)])
                if res_f is not None: return res_f
            return None
            
        for hijo in nodo_actual.children:
            res = self._obtener_guardias_nodo(hijo, nodo_objetivo, guardias_actuales)
            if res is not None: return res
            
        return None

    def _extraer_vars_z3(self, nodo):
        """Escanea el AST y extrae las variables Z3 (Celdas) puras."""
        vars_z3 = {}
        if not hasattr(nodo, 'data'):
            tipo = getattr(nodo, 'type', '')
            if tipo in ('CODIGO', 'VARIABLE_CORCHETE', 'VECTOR'):
                try:
                    var = self.evaluador.evaluar(nodo)
                    if z3.is_expr(var):
                        vars_z3[str(var)] = var
                except: pass
            return vars_z3
            
        for hijo in getattr(nodo, 'children', []):
            vars_z3.update(self._extraer_vars_z3(hijo))
        return vars_z3
    
    def _extraer_rutas_ite(self, z3_expr, ruta_actual=None):
        """
        Escanea una expresión Z3 en busca de condicionales (If-Then-Else).
        Retorna una lista de listas con todas las restricciones necesarias para alcanzar cada hoja.
        """
        if ruta_actual is None: ruta_actual = []
        if not z3.is_app(z3_expr): return [ruta_actual]
        
        kind = z3_expr.decl().kind()
        
        if kind == z3.Z3_OP_ITE:
            cond = z3_expr.children()[0]
            then_expr = z3_expr.children()[1]
            else_expr = z3_expr.children()[2]
            
            rutas_then = self._extraer_rutas_ite(then_expr, ruta_actual + [cond])
            rutas_else = self._extraer_rutas_ite(else_expr, ruta_actual + [z3.Not(cond)])
            return rutas_then + rutas_else
            
        rutas = [ruta_actual]
        for hijo in z3_expr.children():
            nuevas_rutas = []
            for r in rutas:
                nuevas_rutas.extend(self._extraer_rutas_ite(hijo, r))
            rutas = nuevas_rutas
        
        # Eliminar duplicados (si no hubieron ITEs, devolver solo una ruta)
        # Usamos string representation para comparar sin invocar Z3 eq
        rutas_unicas = []
        rutas_str = set()
        for r in rutas:
            r_str = str(r)
            if r_str not in rutas_str:
                rutas_str.add(r_str)
                rutas_unicas.append(r)
                
        return rutas_unicas