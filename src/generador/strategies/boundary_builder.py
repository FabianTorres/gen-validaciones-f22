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

        # RECOLECCIÓN DE VARIABLES (Premisas Universales)
        premisas_universales = []
        nodos_var = self._encontrar_nodos_tipo(ast_tree, 'declaracion_variable')
        for nodo_var in nodos_var:
            premisas_universales.append(self.evaluador.evaluar(nodo_var))

        # MAPA LÓGICO BVA (Boundary Value Analysis)
        mapa_resultados = {
            '<=': ('BUENO', 'MENSAJE', 'BUENO'),
            '<':  ('MENSAJE', 'MENSAJE', 'BUENO'),
            '>=': ('BUENO', 'BUENO', 'MENSAJE'),
            '>':  ('MENSAJE', 'BUENO', 'MENSAJE'),
            '=':  ('BUENO', 'MENSAJE', 'MENSAJE'),
            '!=': ('MENSAJE', 'BUENO', 'BUENO')
        }
        res_exacto, res_sup, res_inf = mapa_resultados.get(operador, ('BUENO', 'BUENO', 'BUENO'))

        # FUNCIÓN BVA DINÁMICA: Aplica los 3 límites sobre cualquier ruta impuesta
        def aplicar_bva(restricciones_ruta, sufijo_nombre, desc_ruta):
            # CASO 1: EXACTO
            casos.append(self._ejecutar_escenario_aislado(
                [z3_izq == z3_der] + premisas_universales + restricciones_ruta, 
                lambda: self._resolver_y_formatear(
                    id_val, f"LIMITE_EXACTO_{sufijo_nombre}", 
                    f"Frontera exacta. {desc_ruta}", res_exacto
                )
            ))
            # CASO 2: EXCEDE (+1 PESO)
            casos.append(self._ejecutar_escenario_aislado(
                [z3_izq == (z3_der + 1)] + premisas_universales + restricciones_ruta, 
                lambda: self._resolver_y_formatear(
                    id_val, f"EXCEDE_LIMITE_{sufijo_nombre}", 
                    f"Supera límite por 1 peso. {desc_ruta}", res_sup
                )
            ))
            # CASO 3: BAJO (-1 PESO)
            casos.append(self._ejecutar_escenario_aislado(
                [z3_izq == (z3_der - 1)] + premisas_universales + restricciones_ruta, 
                lambda: self._resolver_y_formatear(
                    id_val, f"BAJO_LIMITE_{sufijo_nombre}", 
                    f"Bajo el límite por 1 peso. {desc_ruta}", res_inf
                )
            ))

        # 1. EVALUAR RAMAS CONDICIONALES (MCDC INYECTADO PARA COTAS)
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
                
                # Desglose de rutas Verdaderas
                vars_verdaderas = self._desglosar_condicion_verdadera(z3_cond_actual)
                for i, var_v in enumerate(vars_verdaderas, 1):
                    sufijo = f"VERDADERO_{nivel}_{i}" if len(vars_verdaderas) > 1 else f"VERDADERO_{nivel}"
                    aplicar_bva([var_v["restriccion"]], sufijo, var_v["desc"])
                
                # Desglose de rutas Falsas
                vars_falsas = self._desglosar_condicion_falsa(z3_cond_actual)
                for i, var_f in enumerate(vars_falsas, 1):
                    sufijo = f"FALSO_{nivel}_{i}" if len(vars_falsas) > 1 else f"FALSO_{nivel}"
                    aplicar_bva([var_f["restriccion"]], sufijo, var_f["desc"])
        else:
            # Fallback si la regla no tiene condiciones (Cotas lineales)
            aplicar_bva([], "LINEAL", "Evaluación sin condicionales ramificados.")


        # 2. PRUEBAS CRUZADAS: LÍMITES DE FUNCIONES INTERNAS (MIN, MAX, POS, NEG, ABS)
        nodos_func = self._encontrar_nodos_tipo(ast_tree, 'funcion_matematica')
        if nodos_func and casos:
            restriccion_base_buena = None
            restriccion_base_mala = None
            
            for c in casos:
                if c and "resultado_esperado" in c:
                    res = c["resultado_esperado"]
                    tipo = c["tipo_escenario"]
                    if "LIMITE_EXACTO" in tipo: cond = (z3_izq == z3_der)
                    elif "EXCEDE_LIMITE" in tipo: cond = (z3_izq == (z3_der + 1))
                    elif "BAJO_LIMITE" in tipo: cond = (z3_izq == (z3_der - 1))
                    else: continue

                    if res == "BUENO" and restriccion_base_buena is None: restriccion_base_buena = cond
                    elif res == "MENSAJE" and restriccion_base_mala is None: restriccion_base_mala = cond
            
            if restriccion_base_buena is None: restriccion_base_buena = (z3_izq == z3_der)
            if restriccion_base_mala is None: restriccion_base_mala = z3.Not(restriccion_base_buena)

            for f_node in nodos_func:
                nombre_func = str(f_node.children[0]).upper()
                args_node = f_node.children[2]
                args_limpios = [h for h in args_node.children if str(h) != ';']
                
                if nombre_func in ('MIN', 'MAX'):
                    for idx_arg, arg_ast in enumerate(args_limpios):
                        var_z3 = self.evaluador.evaluar(arg_ast)
                        otras_vars = [self.evaluador.evaluar(a) for i, a in enumerate(args_limpios) if i != idx_arg]
                        
                        if nombre_func == 'MIN': restricciones_limite = [var_z3 <= otra for otra in otras_vars]
                        else: restricciones_limite = [var_z3 >= otra for otra in otras_vars]
                            
                        casos.append(self._ejecutar_escenario_aislado(
                            [restriccion_base_buena] + restricciones_limite + premisas_universales, 
                            lambda n=nombre_func, i=idx_arg+1: self._resolver_y_formatear(
                                id_val, f"COTA_FUNC_{n}_ARG_{i}_BUENO", 
                                f"Función {n} evaluada por su argumento {i} respetando el límite legal.", "BUENO"
                            )
                        ))

                        casos.append(self._ejecutar_escenario_aislado(
                            [restriccion_base_mala] + restricciones_limite + premisas_universales, 
                            lambda n=nombre_func, i=idx_arg+1: self._resolver_y_formatear(
                                id_val, f"COTA_FUNC_{n}_ARG_{i}_MENSAJE", 
                                f"Función {n} evaluada por su argumento {i} violando el límite legal.", "MENSAJE"
                            )
                        ))

                elif nombre_func in ('POS', 'NEG', 'ABS'):
                    arg_z3 = self.evaluador.evaluar(args_limpios[0])
                    fronteras_simples = [
                        (arg_z3 > 0, "MAYOR_A_CERO", "con argumento > 0"),
                        (arg_z3 < 0, "MENOR_A_CERO", "forzada a límite negativo")
                    ]
                    
                    for borde, estado, desc in fronteras_simples:
                        casos.append(self._ejecutar_escenario_aislado(
                            [restriccion_base_buena, borde] + premisas_universales,
                            lambda n=nombre_func, e=estado, d=desc: self._resolver_y_formatear(
                                id_val, f"COTA_FUNC_{n}_{e}_BUENO", 
                                f"Función {n} {d} respetando el límite legal.", "BUENO"
                            )
                        ))
                        
                        casos.append(self._ejecutar_escenario_aislado(
                            [restriccion_base_mala, borde] + premisas_universales,
                            lambda n=nombre_func, e=estado, d=desc: self._resolver_y_formatear(
                                id_val, f"COTA_FUNC_{n}_{e}_MENSAJE", 
                                f"Función {n} {d} violando el límite legal.", "MENSAJE"
                            )
                        ))

        # 3. FILTRO Y NUMERACIÓN DEDUPLICADA (Firma: RUT + Inputs)
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

        return casos_validos if casos_validos else [{"id_validacion": id_val, "error": "Contradicción matemática en el cálculo de límites."}]

    # --- MÉTODOS MCDC INCORPORADOS DESDE LA ESTRATEGIA EXPERTA ---
    def _desglosar_condicion_verdadera(self, z3_cond):
        variaciones = []
        def aplanar_or(expr):
            if z3.is_app(expr) and expr.decl().kind() == z3.Z3_OP_OR:
                res = []
                for c in expr.children(): res.extend(aplanar_or(c))
                return res
            return [expr]

        if z3.is_app(z3_cond) and z3_cond.decl().kind() == z3.Z3_OP_OR:
            hijos = aplanar_or(z3_cond)
            for i in range(len(hijos)):
                restricciones = []
                for j, hijo in enumerate(hijos):
                    if i == j: restricciones.append(hijo)
                    else: restricciones.append(z3.Not(hijo))
                variaciones.append({
                    "restriccion": z3.And(*restricciones),
                    "desc": f"La sub-condición {i+1} del bloque OR se cumple de forma exclusiva."
                })
        else:
            variaciones.append({"restriccion": z3_cond, "desc": "La condición se cumple (Rama alcanzada)."})
        return variaciones

    def _desglosar_condicion_falsa(self, z3_cond):
        variaciones = []
        def aplanar_and(expr):
            if z3.is_app(expr) and expr.decl().kind() == z3.Z3_OP_AND:
                res = []
                for c in expr.children(): res.extend(aplanar_and(c))
                return res
            return [expr]

        if z3.is_app(z3_cond) and z3_cond.decl().kind() == z3.Z3_OP_AND:
            hijos = aplanar_and(z3_cond)
            for i in range(len(hijos)):
                restricciones = []
                for j, hijo in enumerate(hijos):
                    if i == j: restricciones.append(z3.Not(hijo))
                    else: restricciones.append(hijo)
                variaciones.append({
                    "restriccion": z3.And(*restricciones),
                    "desc": f"La sub-condición {i+1} del bloque AND falla de forma exclusiva."
                })
        else:
            variaciones.append({"restriccion": z3.Not(z3_cond), "desc": "La condición no se cumple."})
        return variaciones

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