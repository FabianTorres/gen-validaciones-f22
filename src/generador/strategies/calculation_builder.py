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
                    
        ecuacion_completa = [z3_ecuacion] + premisas_universales
        
        gap = 1 if not settings.USAR_DECIMALES else 0

        nodos_func = self._encontrar_nodos_tipo(ast_tree, 'funcion_matematica')
        
        func_names = [str(n.children[0]).upper() for n in nodos_func]
        func_totals = {name: func_names.count(name) for name in set(func_names)}
        func_current = {name: 0 for name in func_totals}
        
        for nodo_func in nodos_func:
            func_name = str(nodo_func.children[0]).upper()
            func_current[func_name] += 1
            
            sufijo = f"_{func_current[func_name]}" if func_totals[func_name] > 1 else ""
            desc_sufijo = f" (Instancia {func_current[func_name]})" if func_totals[func_name] > 1 else ""
            
            args_limpios = [h for h in nodo_func.children[2].children if str(h) != ';']
            camino_base = self._obtener_camino_a_nodo(nodo_func, ast_tree)
            base_cond = ecuacion_completa + camino_base

            if func_name == 'MIN':
                z3_arg1, z3_arg2 = self.evaluador.evaluar(args_limpios[0]), self.evaluador.evaluar(args_limpios[1])
                casos.append(self._ejecutar_escenario_aislado(
                    base_cond + [z3_arg1 <= (z3_arg2 - gap)], 
                    lambda s=sufijo, d=desc_sufijo: self._resolver_y_formatear(id_val, f"CALCULO_MIN{s}_IZQ", f"El límite MIN{d} toma el valor izquierdo garantizando su ruta.", "VERIFICAR_AUTOCALCULO", codigo_objetivo)
                ))
                casos.append(self._ejecutar_escenario_aislado(
                    base_cond + [z3_arg1 >= (z3_arg2 + gap)], 
                    lambda s=sufijo, d=desc_sufijo: self._resolver_y_formatear(id_val, f"CALCULO_MIN{s}_DER", f"El límite MIN{d} toma el valor derecho garantizando su ruta.", "VERIFICAR_AUTOCALCULO", codigo_objetivo)
                ))

            elif func_name == 'MAX':
                z3_arg1, z3_arg2 = self.evaluador.evaluar(args_limpios[0]), self.evaluador.evaluar(args_limpios[1])
                casos.append(self._ejecutar_escenario_aislado(
                    base_cond + [z3_arg1 >= (z3_arg2 + gap)], 
                    lambda s=sufijo, d=desc_sufijo: self._resolver_y_formatear(id_val, f"CALCULO_MAX{s}_IZQ", f"El límite MAX{d} toma el valor izquierdo garantizando su ruta.", "VERIFICAR_AUTOCALCULO", codigo_objetivo)
                ))
                casos.append(self._ejecutar_escenario_aislado(
                    base_cond + [z3_arg1 <= (z3_arg2 - gap)], 
                    lambda s=sufijo, d=desc_sufijo: self._resolver_y_formatear(id_val, f"CALCULO_MAX{s}_DER", f"El límite MAX{d} toma el valor derecho garantizando su ruta.", "VERIFICAR_AUTOCALCULO", codigo_objetivo)
                ))

            elif func_name == 'POS':
                z3_arg = self.evaluador.evaluar(args_limpios[0])
                casos.append(self._ejecutar_escenario_aislado(
                    base_cond + [z3_arg >= gap], 
                    lambda s=sufijo, d=desc_sufijo: self._resolver_y_formatear(id_val, f"CALCULO_POS{s}_MAYOR_CERO", f"El valor interno de POS{d} es positivo en su ruta correcta.", "VERIFICAR_AUTOCALCULO", codigo_objetivo)
                ))
                casos.append(self._ejecutar_escenario_aislado(
                    base_cond + [z3_arg <= -gap], 
                    lambda s=sufijo, d=desc_sufijo: self._resolver_y_formatear(id_val, f"CALCULO_POS{s}_MENOR_CERO", f"El valor interno de POS{d} es negativo, forzando a 0.", "VERIFICAR_AUTOCALCULO", codigo_objetivo)
                ))

            elif func_name == 'NEG':
                z3_arg = self.evaluador.evaluar(args_limpios[0])
                casos.append(self._ejecutar_escenario_aislado(
                    base_cond + [z3_arg <= -gap], 
                    lambda s=sufijo, d=desc_sufijo: self._resolver_y_formatear(id_val, f"CALCULO_NEG{s}_MENOR_CERO", f"El valor interno de NEG{d} es negativo, retornando valor absoluto.", "VERIFICAR_AUTOCALCULO", codigo_objetivo)
                ))
                casos.append(self._ejecutar_escenario_aislado(
                    base_cond + [z3_arg >= gap], 
                    lambda s=sufijo, d=desc_sufijo: self._resolver_y_formatear(id_val, f"CALCULO_NEG{s}_MAYOR_CERO", f"El valor interno de NEG{d} es positivo, forzando a 0.", "VERIFICAR_AUTOCALCULO", codigo_objetivo)
                ))

            elif func_name == 'ABS':
                z3_arg = self.evaluador.evaluar(args_limpios[0])
                casos.append(self._ejecutar_escenario_aislado(
                    base_cond + [z3_arg <= -gap], 
                    lambda s=sufijo, d=desc_sufijo: self._resolver_y_formatear(id_val, f"ABS{s}_ENTRADA_NEGATIVA", f"El valor interno de ABS{d} es negativo, forzando conversión a positivo.", "VERIFICAR_AUTOCALCULO", codigo_objetivo)
                ))
                casos.append(self._ejecutar_escenario_aislado(
                    base_cond + [z3_arg >= gap], 
                    lambda s=sufijo, d=desc_sufijo: self._resolver_y_formatear(id_val, f"ABS{s}_ENTRADA_POSITIVA", f"El valor interno de ABS{d} es positivo, manteniendo su valor.", "VERIFICAR_AUTOCALCULO", codigo_objetivo)
                ))

        nodos_condicional = self._encontrar_nodos_tipo(ast_tree, 'condicional')
        nodos_trailing = self._encontrar_nodos_tipo(ast_tree, 'caso_trailing')
        
        condiciones_a_evaluar = []
        for c in nodos_condicional:
            condiciones_a_evaluar.append((c, c.children[0]))
        for t in nodos_trailing:
            condiciones_a_evaluar.append((t, t.children[-1]))
            
        for idx, (cond_node, cond_ast) in enumerate(condiciones_a_evaluar, 1):
            z3_cond_actual = self.evaluador.evaluar(cond_ast)
            if not z3.is_bool(z3_cond_actual):
                continue
                
            camino_base = self._obtener_camino_a_nodo(cond_node, ast_tree)
            base_cond = ecuacion_completa + camino_base
            nivel = "PRINCIPAL" if idx == 1 else f"ANIDADO_{idx}"
            
            variaciones_verdaderas = self._desglosar_condicion_verdadera(z3_cond_actual)
            for i, var_verdadera in enumerate(variaciones_verdaderas, 1):
                sufijo = f"_{i}" if len(variaciones_verdaderas) > 1 else ""
                casos.append(self._ejecutar_escenario_aislado(
                    base_cond + [var_verdadera["restriccion"]], 
                    lambda v=var_verdadera, s=sufijo, n=nivel: self._resolver_y_formatear(
                        id_val, f"CALCULO_VERDADERO_{n}{s}", 
                        v["desc"], "VERIFICAR_AUTOCALCULO", codigo_objetivo)
                ))
            
            variaciones_falsas = self._desglosar_condicion_falsa(z3_cond_actual)
            for i, var_falsa in enumerate(variaciones_falsas, 1):
                sufijo = f"_{i}" if len(variaciones_falsas) > 1 else ""
                casos.append(self._ejecutar_escenario_aislado(
                    base_cond + [var_falsa["restriccion"]], 
                    lambda v=var_falsa, s=sufijo, n=nivel: self._resolver_y_formatear(
                        id_val, f"CALCULO_FALSO_{n}_SINO{s}", 
                        v["desc"], "VERIFICAR_AUTOCALCULO", codigo_objetivo)
                ))

        if not casos:
            casos.append(self._ejecutar_escenario_aislado(
                ecuacion_completa, 
                lambda: self._resolver_y_formatear(
                    id_val, "CALCULO_LINEAL_EXACTO", 
                    "Se resuelve la ecuación matemática lineal de forma exacta sin ramificaciones.", "VERIFICAR_AUTOCALCULO", codigo_objetivo)
            ))

        casos_validos = []
        inputs_vistos = set()
        idx_real = 1
        
        for c in casos:
            if c is not None:
                if "error" in c:
                    print(f"⚠️ Aviso en {id_val}: Escenario descartado internamente. Motivo: {c['error']}")
                elif c.get("estado_interno") == "INSATISFACTIBLE":
                    print(f"Fase 2: Escenario '{c.get('tipo_escenario', 'Desconocido')}' descartado por ser matemáticamente imposible (Contradicción).")
                elif "inputs" in c:
                    firma_unica = (c.get("rut"), tuple(sorted(c["inputs"].items())))
                    
                    if firma_unica not in inputs_vistos:
                        inputs_vistos.add(firma_unica)
                        c["id_validacion"] = f"{id_val}.{idx_real}"
                        idx_real += 1
                        casos_validos.append(c)
                    else:
                        print(f"Fase 2: Deduplicación en {id_val}: Caso '{c['tipo_escenario']}' ignorado por redundancia total (RUT + Inputs).")

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
        variaciones = []
        def aplanar_or(expr):
            if z3.is_app(expr) and expr.decl().kind() == z3.Z3_OP_OR:
                res = []
                for c in expr.children():
                    res.extend(aplanar_or(c))
                return res
            return [expr]

        if z3.is_app(z3_cond) and z3_cond.decl().kind() == z3.Z3_OP_OR:
            hijos = aplanar_or(z3_cond)
            for i in range(len(hijos)):
                restricciones = []
                for j, hijo in enumerate(hijos):
                    if i == j:
                        restricciones.append(hijo)
                    else:
                        restricciones.append(z3.Not(hijo))
                variaciones.append({
                    "restriccion": z3.And(*restricciones),
                    "desc": f"La sub-condición {i+1} del bloque OR se cumple de forma exclusiva."
                })
        else:
            variaciones.append({
                "restriccion": z3_cond,
                "desc": "La condición se cumple (Rama alcanzada)."
            })
        return variaciones

    def _desglosar_condicion_falsa(self, z3_cond):
        variaciones = []
        def aplanar_and(expr):
            if z3.is_app(expr) and expr.decl().kind() == z3.Z3_OP_AND:
                res = []
                for c in expr.children():
                    res.extend(aplanar_and(c))
                return res
            return [expr]

        if z3.is_app(z3_cond) and z3_cond.decl().kind() == z3.Z3_OP_AND:
            hijos = aplanar_and(z3_cond)
            for i in range(len(hijos)):
                restricciones = []
                for j, hijo in enumerate(hijos):
                    if i == j:
                        restricciones.append(z3.Not(hijo))
                    else:
                        restricciones.append(hijo)
                variaciones.append({
                    "restriccion": z3.And(*restricciones),
                    "desc": f"La sub-condición {i+1} del bloque AND falla de forma exclusiva."
                })
        else:
            variaciones.append({
                "restriccion": z3.Not(z3_cond),
                "desc": "La condición no se cumple, forzando la celda a su valor por defecto."
            })
        return variaciones

    def _encontrar_nodos_tipo(self, arbol, tipo_data):
        encontrados = []
        if hasattr(arbol, 'data'):
            if arbol.data == tipo_data:
                encontrados.append(arbol)
            for hijo in arbol.children:
                if hasattr(hijo, 'data') or hasattr(hijo, 'value'):
                    encontrados.extend(self._encontrar_nodos_tipo(hijo, tipo_data))
        return encontrados