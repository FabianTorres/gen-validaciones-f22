from src.generador.strategies.base_strategy import BaseStrategy
import z3

class BoundaryBuilder(BaseStrategy):
    def generar_casos(self, ast_tree, id_val):
        casos = []
        
        nodo_cota = self._encontrar_nodo_cota(ast_tree)
        if not nodo_cota:
            return [{"id_validacion": id_val, "error": "No se encontró nodo de cota en el AST."}]

        z3_izq = self.evaluador.evaluar(nodo_cota.children[0])
        operador = str(self.evaluador.evaluar(nodo_cota.children[1])).strip()
        z3_der = self.evaluador.evaluar(nodo_cota.children[2])

        if operador == '<=': condicion_maestra = (z3_izq <= z3_der)
        elif operador == '<':  condicion_maestra = (z3_izq < z3_der)
        elif operador == '>=': condicion_maestra = (z3_izq >= z3_der)
        elif operador == '>':  condicion_maestra = (z3_izq > z3_der)
        elif operador == '=':  condicion_maestra = (z3_izq == z3_der)
        elif operador == '!=': condicion_maestra = (z3_izq != z3_der)
        else: condicion_maestra = None

        premisas_universales = []
        nodos_var = self._encontrar_nodos_tipo(ast_tree, 'declaracion_variable')
        for nodo_var in nodos_var:
            premisas_universales.append(self.evaluador.evaluar(nodo_var))

        mapa_resultados = {
            '<=': ('BUENO', 'MENSAJE', 'BUENO'),
            '<':  ('MENSAJE', 'MENSAJE', 'BUENO'),
            '>=': ('BUENO', 'BUENO', 'MENSAJE'),
            '>':  ('MENSAJE', 'BUENO', 'MENSAJE'),
            '=':  ('BUENO', 'MENSAJE', 'MENSAJE'),
            '!=': ('MENSAJE', 'BUENO', 'BUENO')
        }
        res_exacto, res_sup, res_inf = mapa_resultados.get(operador, ('BUENO', 'BUENO', 'BUENO'))

        mapa_restricciones = {
            '<=': (z3_izq == z3_der, z3_izq == z3_der + 1),
            '<':  (z3_izq == z3_der - 1, z3_izq == z3_der),
            '>=': (z3_izq == z3_der, z3_izq == z3_der - 1),
            '>':  (z3_izq == z3_der + 1, z3_izq == z3_der),
            '=':  (z3_izq == z3_der, z3_izq == z3_der + 1),
            '!=': (z3_izq == z3_der + 1, z3_izq == z3_der)
        }
        restriccion_base_buena, restriccion_base_mala = mapa_restricciones.get(operador, (z3_izq == z3_der, z3_izq == z3_der + 1))

        def aplicar_bva(restricciones_ruta, sufijo_nombre, desc_ruta):
            casos.append(self._ejecutar_escenario_aislado(
                [z3_izq == z3_der] + premisas_universales + restricciones_ruta, 
                lambda: self._resolver_y_formatear(
                    id_val, f"LIMITE_EXACTO_{sufijo_nombre}", 
                    f"Frontera exacta. {desc_ruta}", res_exacto,
                    condicion_verificadora=condicion_maestra,  ast_tree=ast_tree
                )
            ))
            casos.append(self._ejecutar_escenario_aislado(
                [z3_izq == (z3_der + 1)] + premisas_universales + restricciones_ruta, 
                lambda: self._resolver_y_formatear(
                    id_val, f"EXCEDE_LIMITE_{sufijo_nombre}", 
                    f"Supera límite por 1 peso. {desc_ruta}", res_sup,
                    condicion_verificadora=condicion_maestra,  ast_tree=ast_tree
                )
            ))
            casos.append(self._ejecutar_escenario_aislado(
                [z3_izq == (z3_der - 1)] + premisas_universales + restricciones_ruta, 
                lambda: self._resolver_y_formatear(
                    id_val, f"BAJO_LIMITE_{sufijo_nombre}", 
                    f"Bajo el límite por 1 peso. {desc_ruta}", res_inf,
                    condicion_verificadora=condicion_maestra, ast_tree=ast_tree
                )
            ))

        nodos_condicional = self._encontrar_nodos_tipo(ast_tree, 'condicional')
        nodos_trailing = self._encontrar_nodos_tipo(ast_tree, 'caso_trailing')
        
        condiciones_a_evaluar = []
        for c in nodos_condicional: condiciones_a_evaluar.append(c.children[0])
        for t in nodos_trailing: condiciones_a_evaluar.append(t.children[-1])
            
        if condiciones_a_evaluar:
            for idx, cond_ast in enumerate(condiciones_a_evaluar, 1):
                z3_cond_actual = self.evaluador.evaluar(cond_ast)
                if not z3.is_bool(z3_cond_actual): continue
                    
                nivel = "PRINCIPAL" if idx == 1 else f"ANIDADO_{idx}"
                
                vars_verdaderas = self._desglosar_condicion_verdadera(z3_cond_actual)
                for i, var_v in enumerate(vars_verdaderas, 1):
                    sufijo = f"VERDADERO_{nivel}_{i}" if len(vars_verdaderas) > 1 else f"VERDADERO_{nivel}"
                    aplicar_bva([var_v["restriccion"]], sufijo, var_v["desc"])
                
                vars_falsas = self._desglosar_condicion_falsa(z3_cond_actual)
                for i, var_f in enumerate(vars_falsas, 1):
                    sufijo = f"FALSO_{nivel}_{i}" if len(vars_falsas) > 1 else f"FALSO_{nivel}"
                    aplicar_bva([var_f["restriccion"]], sufijo, var_f["desc"])
        else:
            aplicar_bva([], "LINEAL", "Evaluación sin condicionales ramificados.")

        # Unificamos ambas estructuras gramaticales de función
        nodos_func = self._encontrar_nodos_tipo(ast_tree, 'funcion_matematica') + self._encontrar_nodos_tipo(ast_tree, 'funcion_directa')
        if nodos_func:
            for func_idx, f_node in enumerate(nodos_func, 1):
                nombre_func_base = str(f_node.children[0]).upper()
                nombre_func_id = f"{nombre_func_base}_{func_idx}"
                
                if f_node.data == 'funcion_matematica':
                    args_node = f_node.children[2]
                    args_limpios = [h for h in args_node.children if str(h) != ';']
                else:
                    args_limpios = [f_node.children[1]]
                
                guardias_activas = self._obtener_guardias_nodo(ast_tree, f_node) or []
                
                if nombre_func_base in ('MIN', 'MAX'):
                    for idx_arg, arg_ast in enumerate(args_limpios):
                        var_z3 = self.evaluador.evaluar(arg_ast)
                        otras_vars = [self.evaluador.evaluar(a) for i, a in enumerate(args_limpios) if i != idx_arg]
                        
                        if nombre_func_base == 'MIN': restricciones_limite = [var_z3 < otra for otra in otras_vars]
                        else: restricciones_limite = [var_z3 > otra for otra in otras_vars]
                            
                        casos.append(self._ejecutar_escenario_aislado(
                            [restriccion_base_buena] + restricciones_limite + premisas_universales + guardias_activas, 
                            lambda n=nombre_func_id, i=idx_arg+1: self._resolver_y_formatear(
                                id_val, f"COTA_FUNC_{n}_ARG_{i}_BUENO", 
                                f"Función {n} evaluada por su argumento {i} en su ruta activa respetando el límite legal.", "BUENO",
                                condicion_verificadora=condicion_maestra, ast_tree=ast_tree
                            )
                        ))

                        casos.append(self._ejecutar_escenario_aislado(
                            [restriccion_base_mala] + restricciones_limite + premisas_universales + guardias_activas, 
                            lambda n=nombre_func_id, i=idx_arg+1: self._resolver_y_formatear(
                                id_val, f"COTA_FUNC_{n}_ARG_{i}_MENSAJE", 
                                f"Función {n} evaluada por su argumento {i} en su ruta activa violando el límite legal.", "MENSAJE",
                                condicion_verificadora=condicion_maestra, ast_tree=ast_tree
                            )
                        ))

                elif nombre_func_base in ('POS', 'NEG', 'ABS'):
                    arg_z3 = self.evaluador.evaluar(args_limpios[0])
                    fronteras_simples = [
                        (arg_z3 > 0, "MAYOR_A_CERO", "con argumento > 0"),
                        (arg_z3 < 0, "MENOR_A_CERO", "forzada a límite negativo")
                    ]
                    
                    for borde, estado, desc in fronteras_simples:
                        casos.append(self._ejecutar_escenario_aislado(
                            [restriccion_base_buena, borde] + premisas_universales + guardias_activas,
                            lambda n=nombre_func_id, e=estado, d=desc: self._resolver_y_formatear(
                                id_val, f"COTA_FUNC_{n}_{e}_BUENO", 
                                f"Función {n} {d} en su ruta activa respetando el límite.", "BUENO",
                                condicion_verificadora=condicion_maestra, ast_tree=ast_tree
                            )
                        ))
                        
                        casos.append(self._ejecutar_escenario_aislado(
                            [restriccion_base_mala, borde] + premisas_universales + guardias_activas,
                            lambda n=nombre_func_id, e=estado, d=desc: self._resolver_y_formatear(
                                id_val, f"COTA_FUNC_{n}_{e}_MENSAJE", 
                                f"Función {n} {d} en su ruta activa violando el límite.", "MENSAJE",
                                condicion_verificadora=condicion_maestra, ast_tree=ast_tree
                            )
                        ))

                elif nombre_func_base == 'ROUND':
                    var_expr = self.evaluador.evaluar(args_limpios[0])
                    
                    dec_val = 0
                    if len(args_limpios) > 1:
                        decimales_ast = self.evaluador.evaluar(args_limpios[1])
                        if hasattr(decimales_ast, 'as_long'): dec_val = decimales_ast.as_long()
                        elif hasattr(decimales_ast, 'as_fraction'): dec_val = int(decimales_ast.as_fraction())
                        elif isinstance(decimales_ast, (int, float)): dec_val = int(decimales_ast)
                        
                    factor = 10 ** dec_val
                    val_multiplicado = var_expr * factor
                    parte_entera = z3.ToReal(z3.ToInt(val_multiplicado))
                    parte_decimal = val_multiplicado - parte_entera
                    
                    restriccion_redondeo = parte_decimal >= z3.RealVal("0.5")
                    
                    casos.append(self._ejecutar_escenario_aislado(
                        [restriccion_base_buena, restriccion_redondeo] + premisas_universales + guardias_activas,
                        lambda n=nombre_func_id: self._resolver_y_formatear(
                            id_val, f"COTA_FUNC_{n}_HACIA_ARRIBA_BUENO", 
                            f"Función {n} forzada a redondear hacia arriba (residuo >= 0.5) en su ruta activa.", "BUENO",
                            condicion_verificadora=condicion_maestra, ast_tree=ast_tree
                        )
                    ))

        casos_validos = []
        idx_real = 1
        
        for caso in casos:
            if caso:
                if "error" in caso:
                    # 🛑 BLOQUEO ESTRICTO SOLO PARA RUT
                    if "No hay RUTs disponibles" in caso["error"]:
                        return [caso]
                    else:
                        print(f"⚠️ Aviso en {id_val}: Escenario descartado internamente. Motivo: {caso['error']}")
                        continue
                
                if caso.get("estado_interno") != "INSATISFACTIBLE":
                    # SIN DEDUPLICACIÓN
                    caso["id_validacion"] = f"{id_val}.{idx_real}"
                    idx_real += 1
                    casos_validos.append(caso)

        return casos_validos if casos_validos else [{"id_validacion": id_val, "error": "Contradicción matemática en el cálculo de límites."}]

    def _obtener_guardias_nodo(self, nodo_actual, nodo_objetivo, guardias_actuales=None):
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
            return [{"restriccion": z3_cond, "desc": "La condición se cumple (Rama alcanzada)."}]

    def _desglosar_condicion_falsa(self, z3_cond):
        import itertools
        if not z3.is_app(z3_cond):
            return [{"restriccion": z3.Not(z3_cond), "desc": "La condición no se cumple."}]
            
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
            return [{"restriccion": z3.Not(z3_cond), "desc": "La condición no se cumple."}]

    def _encontrar_nodo_cota(self, nodo):
        if hasattr(nodo, 'data') and nodo.data == 'cota': return nodo
        if hasattr(nodo, 'children'):
            for hijo in nodo.children:
                encontrado = self._encontrar_nodo_cota(hijo)
                if encontrado: return encontrado
        return None
    
    def _encontrar_nodos_tipo(self, arbol, tipo_data):
        encontrados = []
        if hasattr(arbol, 'data'):
            if arbol.data == tipo_data: encontrados.append(arbol)
            for hijo in arbol.children:
                if hasattr(hijo, 'data') or hasattr(hijo, 'value'):
                    encontrados.extend(self._encontrar_nodos_tipo(hijo, tipo_data))
        return encontrados