import z3
from src.config import settings
from src.generador.strategies.base_strategy import BaseStrategy

class CalculationBuilder(BaseStrategy):
    """
    Estrategia Experta para Validaciones.
    Implementa "MCDC Recursivo" y "Path Execution Locking Semántico" 
    para garantizar la cobertura del 100% de los nodos alcanzables.
    """

    def generar_casos(self, ast_tree, id_val):
        casos = []
        
        nodo_principal = self._encontrar_nodos_tipo(ast_tree, 'autocalculado')
        if not nodo_principal:
            nodo_principal = self._encontrar_nodos_tipo(ast_tree, 'validacion_libre')
            
        if not nodo_principal:
            return [{"id_validacion": id_val, "error": "No se encontró nodo de cálculo."}]
            
        codigo_objetivo = None
        if nodo_principal[0].data == 'autocalculado':
            codigo_objetivo = str(nodo_principal[0].children[0]).strip()
            
        z3_ecuacion = self.evaluador.evaluar(nodo_principal[0])
        
        premisas_universales = []
        if hasattr(ast_tree, 'data') and ast_tree.data == 'validacion':
            for hijo in ast_tree.children:
                if hasattr(hijo, 'data') and hijo.data in ('cota', 'declaracion_variable'):
                    premisas_universales.append(self.evaluador.evaluar(hijo))
                    
        # ---> NUEVO: ESCUDO DECIMAL Y JAULA DE RUT <---
        for nombre, var_z3 in self.motor.variables_memoria.items():
            # 1. Escudo Anti-Polvo Decimal (Solo para códigos tributarios)
            if not self.config_motor.get("usar_decimales", False) and nombre.startswith('[') and nombre.endswith(']'):
                premisas_universales.append(var_z3 == z3.ToReal(z3.ToInt(var_z3)))
                
            # 2. Jaula de Dominio (Obligamos a Z3 a usar Tipos reales Y ENTEROS)
            if nombre == "TIPO_[03]":
                premisas_universales.append(var_z3 == z3.ToReal(z3.ToInt(var_z3))) 
                premisas_universales.append(var_z3 >= 1)
                premisas_universales.append(var_z3 <= 8)
                
            # 3. Blindaje para Subtipos
            if nombre == "SUBTIPO_[03]":
                premisas_universales.append(var_z3 == z3.ToReal(z3.ToInt(var_z3)))
                    
        ecuacion_completa = [z3_ecuacion] + premisas_universales
        
        # Se fuerza una distancia estricta mínima de 2
        gap = 2

        # Unificamos ambas estructuras gramaticales de función
        nodos_func = self._encontrar_nodos_tipo(ast_tree, 'funcion_matematica') + self._encontrar_nodos_tipo(ast_tree, 'funcion_directa')
        
        func_names = [str(n.children[0]).upper() for n in nodos_func]
        func_totals = {name: func_names.count(name) for name in set(func_names)}
        func_current = {name: 0 for name in func_totals}
        
        for nodo_func in nodos_func:
            func_name = str(nodo_func.children[0]).upper()
            func_current[func_name] += 1
            
            sufijo = f"_{func_current[func_name]}" if func_totals[func_name] > 1 else ""
            desc_sufijo = f" (Instancia {func_current[func_name]})" if func_totals[func_name] > 1 else ""
            
            if nodo_func.data == 'funcion_matematica':
                args_limpios = [h for h in nodo_func.children[2].children if str(h) != ';']
            else:
                args_limpios = [nodo_func.children[1]]



            camino_base = self._obtener_camino_a_nodo(nodo_func, ast_tree)
            base_cond = ecuacion_completa + camino_base

            if func_name == 'MIN':
                z3_arg1, z3_arg2 = self.evaluador.evaluar(args_limpios[0]), self.evaluador.evaluar(args_limpios[1])
                casos.append(self._ejecutar_escenario_aislado(
                    base_cond + [z3_arg1 <= (z3_arg2 - gap)], 
                    lambda s=sufijo, d=desc_sufijo: self._resolver_y_formatear(id_val, f"CALCULO_MIN{s}_IZQ", f"El límite MIN{d} toma el valor izquierdo garantizando su ruta.", "VERIFICAR_AUTOCALCULO", codigo_objetivo, ast_tree=ast_tree)
                ))
                casos.append(self._ejecutar_escenario_aislado(
                    base_cond + [z3_arg1 >= (z3_arg2 + gap)], 
                    lambda s=sufijo, d=desc_sufijo: self._resolver_y_formatear(id_val, f"CALCULO_MIN{s}_DER", f"El límite MIN{d} toma el valor derecho garantizando su ruta.", "VERIFICAR_AUTOCALCULO", codigo_objetivo, ast_tree=ast_tree)
                ))

            elif func_name == 'MAX':
                z3_arg1, z3_arg2 = self.evaluador.evaluar(args_limpios[0]), self.evaluador.evaluar(args_limpios[1])
                casos.append(self._ejecutar_escenario_aislado(
                    base_cond + [z3_arg1 >= (z3_arg2 + gap)], 
                    lambda s=sufijo, d=desc_sufijo: self._resolver_y_formatear(id_val, f"CALCULO_MAX{s}_IZQ", f"El límite MAX{d} toma el valor izquierdo garantizando su ruta.", "VERIFICAR_AUTOCALCULO", codigo_objetivo, ast_tree=ast_tree)
                ))
                casos.append(self._ejecutar_escenario_aislado(
                    base_cond + [z3_arg1 <= (z3_arg2 - gap)], 
                    lambda s=sufijo, d=desc_sufijo: self._resolver_y_formatear(id_val, f"CALCULO_MAX{s}_DER", f"El límite MAX{d} toma el valor derecho garantizando su ruta.", "VERIFICAR_AUTOCALCULO", codigo_objetivo, ast_tree=ast_tree)
                ))

            elif func_name == 'POS':
                z3_arg = self.evaluador.evaluar(args_limpios[0])
                casos.append(self._ejecutar_escenario_aislado(
                    base_cond + [z3_arg >= gap], 
                    lambda s=sufijo, d=desc_sufijo: self._resolver_y_formatear(id_val, f"CALCULO_POS{s}_MAYOR_CERO", f"El valor interno de POS{d} es positivo en su ruta correcta.", "VERIFICAR_AUTOCALCULO", codigo_objetivo, ast_tree=ast_tree)
                ))
                casos.append(self._ejecutar_escenario_aislado(
                    base_cond + [z3_arg <= -gap], 
                    lambda s=sufijo, d=desc_sufijo: self._resolver_y_formatear(id_val, f"CALCULO_POS{s}_MENOR_CERO", f"El valor interno de POS{d} es negativo, forzando a 0.", "VERIFICAR_AUTOCALCULO", codigo_objetivo, ast_tree=ast_tree)
                ))

            elif func_name == 'NEG':
                z3_arg = self.evaluador.evaluar(args_limpios[0])
                casos.append(self._ejecutar_escenario_aislado(
                    base_cond + [z3_arg <= -gap], 
                    lambda s=sufijo, d=desc_sufijo: self._resolver_y_formatear(id_val, f"CALCULO_NEG{s}_MENOR_CERO", f"El valor interno de NEG{d} es negativo, retornando valor absoluto.", "VERIFICAR_AUTOCALCULO", codigo_objetivo, ast_tree=ast_tree)
                ))
                casos.append(self._ejecutar_escenario_aislado(
                    base_cond + [z3_arg >= gap], 
                    lambda s=sufijo, d=desc_sufijo: self._resolver_y_formatear(id_val, f"CALCULO_NEG{s}_MAYOR_CERO", f"El valor interno de NEG{d} es positivo, forzando a 0.", "VERIFICAR_AUTOCALCULO", codigo_objetivo, ast_tree=ast_tree)
                ))

            elif func_name == 'ABS':
                z3_arg = self.evaluador.evaluar(args_limpios[0])
                casos.append(self._ejecutar_escenario_aislado(
                    base_cond + [z3_arg <= -gap], 
                    lambda s=sufijo, d=desc_sufijo: self._resolver_y_formatear(id_val, f"ABS{s}_ENTRADA_NEGATIVA", f"El valor interno de ABS{d} es negativo, forzando conversión a positivo.", "VERIFICAR_AUTOCALCULO", codigo_objetivo, ast_tree=ast_tree)
                ))
                casos.append(self._ejecutar_escenario_aislado(
                    base_cond + [z3_arg >= gap], 
                    lambda s=sufijo, d=desc_sufijo: self._resolver_y_formatear(id_val, f"ABS{s}_ENTRADA_POSITIVA", f"El valor interno de ABS{d} es positivo, manteniendo su valor.", "VERIFICAR_AUTOCALCULO", codigo_objetivo, ast_tree=ast_tree)
                ))

        nodos_condicional = self._encontrar_nodos_tipo(ast_tree, 'condicional')
        nodos_trailing = self._encontrar_nodos_tipo(ast_tree, 'caso_trailing')
        
        condiciones_a_evaluar = []
        for c in nodos_condicional:
            # Guardamos: nodo, condicion_logica, expresion_entonces
            condiciones_a_evaluar.append((c, c.children[0], c.children[1]))
        for t in nodos_trailing:
            # Guardamos: nodo, condicion_logica, expresion_entonces
            condiciones_a_evaluar.append((t, t.children[-1], t.children[0]))
            
        for idx, (cond_node, cond_ast, expr_ast) in enumerate(condiciones_a_evaluar, 1):
            z3_cond_actual = self.evaluador.evaluar(cond_ast)
            if not z3.is_bool(z3_cond_actual):
                continue
                
            camino_base = self._obtener_camino_a_nodo(cond_node, ast_tree)
            base_cond = ecuacion_completa + camino_base
            nivel = "PRINCIPAL" if idx == 1 else f"ANIDADO_{idx}"
            
            variaciones_verdaderas = self._desglosar_condicion_verdadera(z3_cond_actual)
            for i, var_verdadera in enumerate(variaciones_verdaderas, 1):
                # CORRECCIÓN: Usamos 'tag_limite' en lugar de 'bva_tag'
                tag_limite = f"_{var_verdadera['tag_limite']}" if "tag_limite" in var_verdadera else ""
                sufijo = f"_{i}" if len(variaciones_verdaderas) > 1 else ""
                casos.append(self._ejecutar_escenario_aislado(
                    base_cond + [var_verdadera["restriccion"]], 
                    lambda v=var_verdadera, s=sufijo, n=nivel, t=tag_limite: self._resolver_y_formatear(
                        id_val, f"CALCULO_VERDADERO_{n}{s}{t}", 
                        v["desc"], "VERIFICAR_AUTOCALCULO", codigo_objetivo, ast_tree=ast_tree)
                ))
            
            variaciones_falsas = self._desglosar_condicion_falsa(z3_cond_actual)
            for i, var_falsa in enumerate(variaciones_falsas, 1):
                # CORRECCIÓN: Usamos 'tag_limite' en lugar de 'bva_tag'
                tag_limite = f"_{var_falsa['tag_limite']}" if "tag_limite" in var_falsa else ""
                sufijo = f"_{i}" if len(variaciones_falsas) > 1 else ""
                
                # ---> ANTI-MASKING: Intentamos inflar la rama muerta <---
                def generar_falso_anti_masking(v=var_falsa, s=sufijo, n=nivel, t=tag_limite, expr=expr_ast):
                    try:
                        # Evaluamos matemáticamente la rama ENTONCES (la que quedó muerta)
                        z3_expr_muerta = self.evaluador.evaluar(expr)
                        
                        # Guardamos el estado del solver y forzamos a que esa rama tenga valor
                        self.motor.solver.push()
                        self.motor.solver.add(z3_expr_muerta >= gap)
                        
                        res = self._resolver_y_formatear(
                            id_val, f"CALCULO_FALSO_{n}_SINO{s}{t}",
                            v["desc"] + " [Anti-Masking Inyectado]", "VERIFICAR_AUTOCALCULO", codigo_objetivo, ast_tree=ast_tree
                        )
                        self.motor.solver.pop()
                        
                        if res and res.get("estado_interno") != "INSATISFACTIBLE":
                            return res
                    except Exception:
                        pass
                    
                    # Fallback: Si el Anti-Masking causa contradicción, retornamos el falso normal
                    return self._resolver_y_formatear(
                        id_val, f"CALCULO_FALSO_{n}_SINO{s}{t}",
                        v["desc"], "VERIFICAR_AUTOCALCULO", codigo_objetivo, ast_tree=ast_tree
                    )
                
                casos.append(self._ejecutar_escenario_aislado(
                    base_cond + [var_falsa["restriccion"]], 
                    generar_falso_anti_masking
                ))

        if not casos:
            casos.append(self._ejecutar_escenario_aislado(
                ecuacion_completa, 
                lambda: self._resolver_y_formatear(
                    id_val, "CALCULO_LINEAL_EXACTO", 
                    "Se resuelve la ecuación matemática lineal de forma exacta sin ramificaciones.", "VERIFICAR_AUTOCALCULO", codigo_objetivo, ast_tree=ast_tree)
            ))

        # =================================================================
        # ---> NUEVO BLOQUE: ESCENARIO NEGATIVO (Validación de Catálogo) <---
        # =================================================================
        if codigo_objetivo:
            # 1. Limpiamos el código objetivo (ej. "[1066]" -> "1066") para buscarlo en RAM
            cod_limpio = codigo_objetivo.replace('[', '').replace(']', '').strip()
            
            # 2. Consultamos el catálogo inyectado en el motor Z3
            info_codigo = self.motor.catalogo_signos.get(cod_limpio, {})
            signo_permitido = info_codigo.get("signo_permitido", "+")
            
            # 3. Si el negocio tributario permite negativos, atacamos la frontera
            if signo_permitido in ("+/-", "-"):
                var_objetivo_z3 = self.motor.obtener_o_crear_variable(codigo_objetivo)
                
                # 4. Inyectamos la restricción dura (Hard Constraint): Obligamos a que el resultado sea negativo.
                # Usamos '-gap' (ej. <= -2) para asegurar un negativo claro y no un 0.
                casos.append(self._ejecutar_escenario_aislado(
                    ecuacion_completa + [var_objetivo_z3 <= -gap], 
                    lambda: self._resolver_y_formatear(
                        id_val, "CALCULO_RESULTADO_NEGATIVO", 
                        f"Se fuerza la ecuación a generar un resultado negativo para {codigo_objetivo}, permitido por el catálogo.", 
                        "VERIFICAR_AUTOCALCULO", codigo_objetivo, ast_tree=ast_tree)
                ))
        # =================================================================

        casos_validos = []
        idx_real = 1
        
        for c in casos:
            if c is not None:
                # 1. Si es un caso con falta de RUT, lo DEJAMOS PASAR para el Frontend
                if c.get("estado_interno") == "ERROR_RUT":
                    c["id_validacion"] = f"{id_val}.{idx_real}"
                    idx_real += 1
                    casos_validos.append(c)
                    
                # 2. Otros errores estructurales (ej. falta de AST) sí se bloquean o descartan
                elif "error" in c:
                    print(f"⚠️ Aviso en {id_val}: Escenario descartado internamente. Motivo: {c['error']}")
                
                # 3. Contradicciones matemáticas de Z3 se ignoran
                elif c.get("estado_interno") == "INSATISFACTIBLE":
                    pass
                
                # 4. Casos perfectos y enriquecidos
                elif "inputs" in c:
                    c["id_validacion"] = f"{id_val}.{idx_real}"
                    idx_real += 1
                    casos_validos.append(c)

        return casos_validos if casos_validos else [{"id_validacion": id_val, "error": "Inconsistencia matemática en todas las ramas."}]

    def _obtener_camino_a_nodo(self, nodo_objetivo, ast_tree):
        camino = []
        
        var_asociada = None
        nodos_cota = self._encontrar_nodos_tipo(ast_tree, 'cota')
        for cota in nodos_cota:
            if self._contiene_nodo(cota, nodo_objetivo):
                var_asociada = str(cota.children[0]).strip().upper()
                break

        nodos_condicional = self._encontrar_nodos_tipo(ast_tree, 'condicional')
        for cond_node in nodos_condicional:
            if cond_node is nodo_objetivo:
                continue
            z3_cond_actual = self.evaluador.evaluar(cond_node.children[0])
            if not z3.is_bool(z3_cond_actual):
                continue
            
            en_entonces = len(cond_node.children) >= 2 and self._contiene_nodo(cond_node.children[1], nodo_objetivo)
            en_sino = len(cond_node.children) >= 3 and self._contiene_nodo(cond_node.children[2], nodo_objetivo)
            
            if not en_entonces and not en_sino and var_asociada:
                en_entonces = len(cond_node.children) >= 2 and self._contiene_texto(cond_node.children[1], var_asociada)
                en_sino = len(cond_node.children) >= 3 and self._contiene_texto(cond_node.children[2], var_asociada)
            
            if en_entonces:
                camino.append(z3_cond_actual)
            elif en_sino:
                camino.append(z3.Not(z3_cond_actual))

        nodos_trailing = self._encontrar_nodos_tipo(ast_tree, 'caso_trailing')
        for trail_node in nodos_trailing:
            if trail_node is nodo_objetivo:
                continue
            
            z3_cond_actual = self.evaluador.evaluar(trail_node.children[-1])
            if not z3.is_bool(z3_cond_actual):
                continue
            
            en_entonces = self._contiene_nodo(trail_node, nodo_objetivo)
            
            if not en_entonces and var_asociada:
                en_entonces = self._contiene_texto(trail_node, var_asociada)
                
            if en_entonces:
                camino.append(z3_cond_actual)
                
        return camino

    def _contiene_nodo(self, raiz, nodo_buscado):
        if raiz is nodo_buscado:
            return True
        if hasattr(raiz, 'children'):
            for hijo in raiz.children:
                if self._contiene_nodo(hijo, nodo_buscado):
                    return True
        return False

    def _contiene_texto(self, raiz, texto):
        if hasattr(raiz, 'children'):
            for hijo in raiz.children:
                if self._contiene_texto(hijo, texto):
                    return True
        else:
            return str(raiz).strip().upper() == texto
        return False

    def _desglosar_condicion_verdadera(self, z3_cond):
        import itertools
        if not z3.is_app(z3_cond):
            return [{"restriccion": z3_cond, "desc": "La condición se cumple (Rama alcanzada)."}]
            
        kind = z3_cond.decl().kind()
        
        if kind == z3.Z3_OP_OR:
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
            
        else:
            # =====================================================================
            # [INTERRUPTOR BVA] LISTO PARA VOLVER
            # Cambiar a False si mañana el negocio no soporta la cantidad de casos adicionales
            # =====================================================================
            ACTIVAR_LIMITES_CALCULOS = True
            
            # En _desglosar_condicion_verdadera:
            if ACTIVAR_LIMITES_CALCULOS and kind in (z3.Z3_OP_LT, z3.Z3_OP_LE, z3.Z3_OP_GT, z3.Z3_OP_GE):
                izq, der = z3_cond.children()[0], z3_cond.children()[1]
                variaciones = []
                if kind == z3.Z3_OP_LE:
                    variaciones.append({"restriccion": izq == der, "desc": "Evaluación en el límite exacto (<=).", "tag_limite": "EN_EL_LIMITE"})
                    variaciones.append({"restriccion": izq == der - 1, "desc": "Evaluación bajo el límite (<=).", "tag_limite": "BAJO_EL_LIMITE"})
                elif kind == z3.Z3_OP_GE:
                    variaciones.append({"restriccion": izq == der, "desc": "Evaluación en el límite exacto (>=).", "tag_limite": "EN_EL_LIMITE"})
                    variaciones.append({"restriccion": izq == der + 1, "desc": "Evaluación sobre el límite (>=).", "tag_limite": "SOBRE_EL_LIMITE"})
                elif kind == z3.Z3_OP_LT:
                    variaciones.append({"restriccion": izq == der - 1, "desc": "Evaluación bajo el límite (<).", "tag_limite": "BAJO_EL_LIMITE"})
                elif kind == z3.Z3_OP_GT:
                    variaciones.append({"restriccion": izq == der + 1, "desc": "Evaluación sobre el límite (>).", "tag_limite": "SOBRE_EL_LIMITE"})
                return variaciones
            # =====================================================================
            
            return [{"restriccion": z3_cond, "desc": "La condición se cumple (Rama alcanzada)."}]

    def _desglosar_condicion_falsa(self, z3_cond):
        import itertools
        if not z3.is_app(z3_cond):
            return [{"restriccion": z3.Not(z3_cond), "desc": "La condición no se cumple, forzando la celda a su valor por defecto."}]
            
        kind = z3_cond.decl().kind()
        
        if kind == z3.Z3_OP_AND:
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
            
        else:
            # =====================================================================
            # [INTERRUPTOR BVA] LISTO PARA VOLVER
            # Cambiar a False si mañana el negocio no soporta la cantidad de casos
            # =====================================================================
            ACTIVAR_LIMITES_CALCULOS = True
            
            if ACTIVAR_LIMITES_CALCULOS and kind in (z3.Z3_OP_LT, z3.Z3_OP_LE, z3.Z3_OP_GT, z3.Z3_OP_GE):
                izq, der = z3_cond.children()[0], z3_cond.children()[1]
                variaciones = []
                if kind == z3.Z3_OP_LE: # Falso de <= es >
                    variaciones.append({"restriccion": izq == der + 1, "desc": "Condición falla sobre el límite (<=).", "tag_limite": "SOBRE_EL_LIMITE"})
                elif kind == z3.Z3_OP_GE: # Falso de >= es <
                    variaciones.append({"restriccion": izq == der - 1, "desc": "Condición falla bajo el límite (>=).", "tag_limite": "BAJO_EL_LIMITE"})
                elif kind == z3.Z3_OP_LT: # Falso de < es >=
                    variaciones.append({"restriccion": izq == der, "desc": "Condición falla en el límite exacto (<).", "tag_limite": "EN_EL_LIMITE"})
                    variaciones.append({"restriccion": izq == der + 1, "desc": "Condición falla sobre el límite (<).", "tag_limite": "SOBRE_EL_LIMITE"})
                elif kind == z3.Z3_OP_GT: # Falso de > es <=
                    variaciones.append({"restriccion": izq == der, "desc": "Condición falla en el límite exacto (>).", "tag_limite": "EN_EL_LIMITE"})
                    variaciones.append({"restriccion": izq == der - 1, "desc": "Condición falla bajo el límite (>).", "tag_limite": "BAJO_EL_LIMITE"})
                return variaciones
            # =====================================================================
            
            return [{"restriccion": z3.Not(z3_cond), "desc": "La condición no se cumple, forzando la celda a su valor por defecto."}]

    def _encontrar_nodos_tipo(self, arbol, tipo_data):
        encontrados = []
        if hasattr(arbol, 'data'):
            if arbol.data == tipo_data:
                encontrados.append(arbol)
            for hijo in arbol.children:
                if hasattr(hijo, 'data') or hasattr(hijo, 'value'):
                    encontrados.extend(self._encontrar_nodos_tipo(hijo, tipo_data))
        return encontrados