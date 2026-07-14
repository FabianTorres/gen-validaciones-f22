import z3
from src.config import settings
from src.generador.strategies.base_strategy import BaseStrategy

class CalculationBuilder(BaseStrategy):
    """
    Estrategia Experta para Validaciones Tipo A, B.
    Implementa "Path Execution Locking" para garantizar que Z3
    camine por la rama (SI o SINO) correcta antes de evaluar un límite matemático.
    """

    def generar_casos(self, ast_tree, id_val):
        casos = []
        
        nodo_principal = self._encontrar_nodos_tipo(ast_tree, 'autocalculado')
        if not nodo_principal:
            nodo_principal = self._encontrar_nodos_tipo(ast_tree, 'validacion_libre')
            
        if not nodo_principal:
            return [{"id_validacion": id_val, "error": "No se encontró nodo de cálculo."}]
            
        z3_ecuacion = self.evaluador.evaluar(nodo_principal[0])
        z3_cond = self._extraer_condicion_z3_desde_ast(ast_tree)
        
        nodos_func = self._encontrar_nodos_tipo(ast_tree, 'funcion_matematica')
        nodo_min = next((n for n in nodos_func if str(n.children[0]).upper() == 'MIN'), None)
        nodo_max = next((n for n in nodos_func if str(n.children[0]).upper() == 'MAX'), None)
        nodo_pos = next((n for n in nodos_func if str(n.children[0]).upper() == 'POS'), None)
        nodo_neg = next((n for n in nodos_func if str(n.children[0]).upper() == 'NEG'), None)

        gap = 1 if not settings.USAR_DECIMALES else 0

        # 1. EVALUAR LÍMITES MATEMÁTICOS CON BLOQUEO DE RUTA (Path Locking)
        if nodo_min:
            args_node = nodo_min.children[2]
            args_limpios = [h for h in args_node.children if str(h) != ';']
            z3_arg1 = self.evaluador.evaluar(args_limpios[0])
            z3_arg2 = self.evaluador.evaluar(args_limpios[1])
            
            restriccion_ruta = self._obtener_restriccion_rama(nodo_min, ast_tree, z3_cond)
            base_cond = [z3_ecuacion] + restriccion_ruta
            
            casos.append(self._ejecutar_escenario_aislado(
                base_cond + [z3_arg1 <= (z3_arg2 - gap)], 
                lambda: self._resolver_y_formatear(
                    id_val, "CALCULO_MIN_IZQ", 
                    "El límite MIN toma el valor izquierdo garantizando su ruta de ejecución.", "VERIFICAR_AUTOCALCULO")
            ))
            casos.append(self._ejecutar_escenario_aislado(
                base_cond + [z3_arg1 >= (z3_arg2 + gap)], 
                lambda: self._resolver_y_formatear(
                    id_val, "CALCULO_MIN_DER", 
                    "El límite MIN se topa con el valor derecho garantizando su ruta de ejecución.", "VERIFICAR_AUTOCALCULO")
            ))

        if nodo_max:
            args_node = nodo_max.children[2]
            args_limpios = [h for h in args_node.children if str(h) != ';']
            z3_arg1 = self.evaluador.evaluar(args_limpios[0])
            z3_arg2 = self.evaluador.evaluar(args_limpios[1])
            
            restriccion_ruta = self._obtener_restriccion_rama(nodo_max, ast_tree, z3_cond)
            base_cond = [z3_ecuacion] + restriccion_ruta

            casos.append(self._ejecutar_escenario_aislado(
                base_cond + [z3_arg1 >= (z3_arg2 + gap)], 
                lambda: self._resolver_y_formatear(
                    id_val, "CALCULO_MAX_IZQ", 
                    "El límite MAX toma el valor izquierdo garantizando su ruta de ejecución.", "VERIFICAR_AUTOCALCULO")
            ))
            casos.append(self._ejecutar_escenario_aislado(
                base_cond + [z3_arg1 <= (z3_arg2 - gap)], 
                lambda: self._resolver_y_formatear(
                    id_val, "CALCULO_MAX_DER", 
                    "El límite MAX se topa con el valor derecho garantizando su ruta de ejecución.", "VERIFICAR_AUTOCALCULO")
            ))

        if nodo_pos:
            args_node = nodo_pos.children[2]
            args_limpios = [h for h in args_node.children if str(h) != ';']
            z3_arg_pos = self.evaluador.evaluar(args_limpios[0])
            
            restriccion_ruta = self._obtener_restriccion_rama(nodo_pos, ast_tree, z3_cond)
            base_cond = [z3_ecuacion] + restriccion_ruta

            casos.append(self._ejecutar_escenario_aislado(
                base_cond + [z3_arg_pos >= gap], 
                lambda: self._resolver_y_formatear(
                    id_val, "CALCULO_POS_MAYOR_CERO", 
                    "El valor interno de la función POS es positivo, ruta bloqueada correctamente.", "VERIFICAR_AUTOCALCULO")
            ))
            casos.append(self._ejecutar_escenario_aislado(
                base_cond + [z3_arg_pos <= -gap], 
                lambda: self._resolver_y_formatear(
                    id_val, "CALCULO_POS_MENOR_CERO", 
                    "El valor interno de la función POS es negativo, forzando a 0 en ruta correcta.", "VERIFICAR_AUTOCALCULO")
            ))
        
        if nodo_neg:
            args_node = nodo_neg.children[2]
            args_limpios = [h for h in args_node.children if str(h) != ';']
            z3_arg_neg = self.evaluador.evaluar(args_limpios[0])
            
            restriccion_ruta = self._obtener_restriccion_rama(nodo_neg, ast_tree, z3_cond)
            base_cond = [z3_ecuacion] + restriccion_ruta

            casos.append(self._ejecutar_escenario_aislado(
                base_cond + [z3_arg_neg <= -gap], 
                lambda: self._resolver_y_formatear(
                    id_val, "CALCULO_NEG_MENOR_CERO", 
                    "El valor interno de la función NEG es negativo, retornando su valor absoluto (ruta bloqueada).", "VERIFICAR_AUTOCALCULO")
            ))
            
            casos.append(self._ejecutar_escenario_aislado(
                base_cond + [z3_arg_neg >= gap], 
                lambda: self._resolver_y_formatear(
                    id_val, "CALCULO_NEG_MAYOR_CERO", 
                    "El valor interno de la función NEG es positivo o cero, forzando a 0 en ruta correcta.", "VERIFICAR_AUTOCALCULO")
            ))

        # 2. EVALUAR RAMAS CONDICIONALES (MCDC)
        if z3_cond is not None:
            casos.append(self._ejecutar_escenario_aislado(
                [z3_ecuacion, z3_cond], 
                lambda: self._resolver_y_formatear(
                    id_val, "CALCULO_VERDADERO_SIMPLE", 
                    "La condición principal se cumple (Rama ENTONCES).", "VERIFICAR_AUTOCALCULO")
            ))
            
            variaciones_falsas = self._desglosar_condicion_falsa(z3_cond)
            for i, var_falsa in enumerate(variaciones_falsas, 1):
                sufijo = f"_{i}" if len(variaciones_falsas) > 1 else ""
                casos.append(self._ejecutar_escenario_aislado(
                    [z3_ecuacion, var_falsa["restriccion"]], 
                    lambda v=var_falsa, s=sufijo: self._resolver_y_formatear(
                        id_val, f"CALCULO_FALSO_SINO{s}", 
                        v["desc"], "VERIFICAR_AUTOCALCULO")
                ))

        # 3. FALLBACK LINEAL
        if z3_cond is None and not nodo_min and not nodo_max and not nodo_pos and not nodo_neg:
            casos.append(self._ejecutar_escenario_aislado(
                [z3_ecuacion], 
                lambda: self._resolver_y_formatear(
                    id_val, "CALCULO_LINEAL_EXACTO", 
                    "Se resuelve la ecuación matemática lineal de forma exacta sin ramificaciones.", "VERIFICAR_AUTOCALCULO")
            ))

        # 4. VISIBILIDAD DE ERRORES, DEDUPLICACION Y LIMPIEZA
        casos_validos = []
        inputs_vistos = set()
        idx_real = 1
        
        for c in casos:
            if c is not None:
                if "error" in c:
                    print(f"⚠️ Aviso en {id_val}: Escenario descartado internamente. Motivo: {c['error']}")
                else:
                    # Convierte el diccionario a una tupla ordenada e inmutable para evaluarla
                    firma_inputs = tuple(sorted(c["inputs"].items()))
                    
                    if firma_inputs not in inputs_vistos:
                        inputs_vistos.add(firma_inputs)
                        c["id_validacion"] = f"{id_val}.{idx_real}"
                        idx_real += 1
                        casos_validos.append(c)
                    else:
                        print(f"Fase 2: Deduplicación en {id_val}: Caso '{c['tipo_escenario']}' ignorado por tener inputs idénticos.")

        return casos_validos if casos_validos else [{"id_validacion": id_val, "error": "Inconsistencia matemática en todas las ramas."}]

    def _obtener_restriccion_rama(self, nodo_objetivo, ast_tree, z3_cond):
        """Rastrea el AST para bloquear a Z3 en la rama correspondiente (ENTONCES o SINO)."""
        if z3_cond is None:
            return []
            
        nodos_condicional = self._encontrar_nodos_tipo(ast_tree, 'condicional')
        if nodos_condicional:
            for cond_node in nodos_condicional:
                # Rama ENTONCES suele ser el hijo 1
                if len(cond_node.children) >= 2 and self._contiene_nodo(cond_node.children[1], nodo_objetivo):
                    return [z3_cond]
                # Rama SINO suele ser el hijo 2
                if len(cond_node.children) >= 3 and self._contiene_nodo(cond_node.children[2], nodo_objetivo):
                    return [z3.Not(z3_cond)]
                        
        nodos_trailing = self._encontrar_nodos_tipo(ast_tree, 'caso_trailing')
        if nodos_trailing:
            for trail_node in nodos_trailing:
                if self._contiene_nodo(trail_node, nodo_objetivo):
                    return [z3_cond]  # En caso trailing, la función siempre requiere que la condición sea True
                    
        return []

    def _contiene_nodo(self, raiz, nodo_buscado):
        """Búsqueda recursiva para saber si un nodo está dentro de un sub-árbol."""
        if raiz is nodo_buscado:
            return True
        if hasattr(raiz, 'children'):
            for hijo in raiz.children:
                if self._contiene_nodo(hijo, nodo_buscado):
                    return True
        return False

    def _extraer_condicion_z3_desde_ast(self, ast_tree):
        nodos_condicional = self._encontrar_nodos_tipo(ast_tree, 'condicional')
        if nodos_condicional:
            evaluado = self.evaluador.evaluar(nodos_condicional[0].children[0])
            if z3.is_bool(evaluado):
                return evaluado

        nodos_posibles = ['comparacion_simple', 'condicion', 'expresion_logica', 'comparacion']
        for nombre in nodos_posibles:
            nodos = self._encontrar_nodos_tipo(ast_tree, nombre)
            if nodos:
                evaluado = self.evaluador.evaluar(nodos[0])
                if z3.is_bool(evaluado):
                    return evaluado
        
        nodos_trailing = self._encontrar_nodos_tipo(ast_tree, 'caso_trailing')
        if nodos_trailing:
            evaluado = self.evaluador.evaluar(nodos_trailing[0].children[-1])
            if z3.is_bool(evaluado):
                return evaluado
                
        return None

    def _desglosar_condicion_falsa(self, z3_cond):
        variaciones = []
        if z3.is_app(z3_cond) and z3_cond.decl().kind() == z3.Z3_OP_AND:
            hijos = z3_cond.children()
            for i in range(len(hijos)):
                restricciones = []
                for j, hijo in enumerate(hijos):
                    if i == j:
                        restricciones.append(z3.Not(hijo)) 
                    else:
                        restricciones.append(hijo)          
                
                variaciones.append({
                    "restriccion": z3.And(*restricciones),
                    "desc": f"La sub-condición {i+1} del IF principal falla, mientras las demás se cumplen. Se fuerza la celda al valor por defecto (Sino)."
                })
        else:
            variaciones.append({
                "restriccion": z3.Not(z3_cond),
                "desc": "La condición no se cumple, forzando la celda a su valor por defecto (ej. Sino 0)."
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