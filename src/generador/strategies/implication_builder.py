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
        
        nodo_impl = self._encontrar_nodos_tipo(ast_tree, 'implicacion')
        if not nodo_impl:
            return [{"id_validacion": id_val, "error": "No se encontró nodo de implicacion en el AST."}]
            
        # Tomamos el primer nodo de implicación (normalmente único en la raíz de reglas d/e)
        nodo_impl = nodo_impl[0]

        gatillo_ast = nodo_impl.children[0]
        requisito_ast = nodo_impl.children[2] # Índice 2 para saltar el token '=>'

        z3_gatillo = self.evaluador.evaluar(gatillo_ast)
        z3_requisito = self.evaluador.evaluar(requisito_ast)

        premisas_universales = []
        nodos_var = self._encontrar_nodos_tipo(ast_tree, 'declaracion_variable')
        for nodo_var in nodos_var:
            premisas_universales.append(self.evaluador.evaluar(nodo_var))

        # Generamos los universos MCDC aislando la izquierda (gatillo) y derecha (requisito)
        gatillo_verdadero = self._desglosar_condicion_verdadera(z3_gatillo)
        gatillo_falso = self._desglosar_condicion_falsa(z3_gatillo)
        
        requisito_verdadero = self._desglosar_condicion_verdadera(z3_requisito)
        requisito_falso = self._desglosar_condicion_falsa(z3_requisito)

        # --- CASO 1: FLUJO IDEAL (CUMPLE Y CUMPLE) ---
        # Cruzamos todas las formas de encender el gatillo con todas las formas de cumplir el requisito
        for i, var_g in enumerate(gatillo_verdadero, 1):
            for j, var_r in enumerate(requisito_verdadero, 1):
                sufijo = f"_{i}_{j}" if len(gatillo_verdadero) > 1 or len(requisito_verdadero) > 1 else ""
                desc = f"Gatillo activo ({var_g['desc']}) Y Requisito cumplido ({var_r['desc']})"
                
                casos.append(
                    self._ejecutar_escenario_aislado(
                        premisas_universales + [var_g["restriccion"], var_r["restriccion"]], 
                        lambda d=desc, s=sufijo: self._resolver_y_formatear(
                            id_val, 
                            f"CUMPLE_CONDICION{s}", 
                            d, 
                            "BUENO",
                            ast_tree=ast_tree
                        )
                    )
                )

        # --- CASO 2: QUIEBRE DE REGLA (FALLA ESPERADA) ---
        # Cruzamos gatillo encendido contra todas las violaciones posibles del requisito
        for i, var_g in enumerate(gatillo_verdadero, 1):
            for j, var_r in enumerate(requisito_falso, 1):
                sufijo = f"_{i}_{j}" if len(gatillo_verdadero) > 1 or len(requisito_falso) > 1 else ""
                desc = f"Se fuerza error: Gatillo activo ({var_g['desc']}) PERO Requisito falla ({var_r['desc']})"
                
                casos.append(
                    self._ejecutar_escenario_aislado(
                        premisas_universales + [var_g["restriccion"], var_r["restriccion"]], 
                        lambda d=desc, s=sufijo: self._resolver_y_formatear(
                            id_val, 
                            f"INCUMPLE_CONDICION{s}", 
                            d, 
                            "MENSAJE",
                            ast_tree=ast_tree
                        )
                    )
                )

        # --- CASO 3: OMISIÓN (NO APLICA LA REGLA) ---
        # Exploramos todas las formas de evitar que la regla se gatille
        for i, var_g in enumerate(gatillo_falso, 1):
            sufijo = f"_{i}" if len(gatillo_falso) > 1 else ""
            desc = f"La regla no aplica: Gatillo inactivo ({var_g['desc']})"
            
            casos.append(
                self._ejecutar_escenario_aislado(
                    premisas_universales + [var_g["restriccion"]], 
                    lambda d=desc, s=sufijo: self._resolver_y_formatear(
                        id_val, 
                        f"NO_APLICA{s}", 
                        d, 
                        "BUENO",
                        ast_tree=ast_tree
                    )
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

                # PATH EXECUTION LOCKING: Extraemos el camino exacto para forzar a Z3 a llegar a la función
                guardias_activas = self._obtener_guardias_nodo(requisito_ast, nodo_func) or []
                base_cond = premisas_universales + [restriccion_gatillo, z3_requisito_eval] + guardias_activas

                # TÉCNICA DE AISLAMIENTO ANTI-ENMASCARAMIENTO
                vars_func_actual = self._extraer_vars_z3(nodo_func)
                restricciones_aislamiento = []
                for nombre, var_z3 in vars_req_totales.items():
                    if nombre not in vars_func_actual:
                        restricciones_aislamiento.append(var_z3 == 0)

                def ejecutar_con_aislamiento(restriccion_frontera, lambda_formateador):
                    # 1. Intentamos probar aislando el ruido con 0s
                    res = self._ejecutar_escenario_aislado(base_cond + restricciones_aislamiento + [restriccion_frontera], lambda_formateador)
                    # 2. Fallback por si aislar con 0 contradice la propia regla
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
                firma_unica = (caso.get("rut"), tuple(sorted(caso.get("inputs", {}).items())))
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
        
        # BVA PARA COMPARACIONES ATÓMICAS EN REQUISITOS
        if kind in (z3.Z3_OP_LT, z3.Z3_OP_LE, z3.Z3_OP_GT, z3.Z3_OP_GE, z3.Z3_OP_EQ):
            izq, der = z3_cond.children()[0], z3_cond.children()[1]
            if kind == z3.Z3_OP_LT:   restr_bva = (izq == der - 1)
            elif kind == z3.Z3_OP_LE: restr_bva = (izq == der)
            elif kind == z3.Z3_OP_GT: 
                # Si la expresión contiene celdas sumadas, garantizamos que al menos una celda real tome un valor >= 1
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
            else:                     restr_bva = (izq == der + 1)
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