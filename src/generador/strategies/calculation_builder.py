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
            
        z3_ecuacion = self.evaluador.evaluar(nodo_principal[0])
        
        # 1. RECOLECCIÓN DE CONTEXTO BASE
        premisas_universales = []
        if hasattr(ast_tree, 'data') and ast_tree.data == 'validacion':
            for hijo in ast_tree.children:
                if hasattr(hijo, 'data') and hijo.data in ('cota', 'declaracion_variable'):
                    premisas_universales.append(self.evaluador.evaluar(hijo))
                    
        ecuacion_completa = [z3_ecuacion] + premisas_universales
        
        gap = 1 if not settings.USAR_DECIMALES else 0

        # 2. EVALUAR LÍMITES MATEMÁTICOS CON BLOQUEO DE RUTA
        nodos_func = self._encontrar_nodos_tipo(ast_tree, 'funcion_matematica')
        
        for nodo_func in nodos_func:
            func_name = str(nodo_func.children[0]).upper()
            args_limpios = [h for h in nodo_func.children[2].children if str(h) != ';']
            camino_base = self._obtener_camino_a_nodo(nodo_func, ast_tree)
            base_cond = ecuacion_completa + camino_base

            if func_name == 'MIN':
                z3_arg1, z3_arg2 = self.evaluador.evaluar(args_limpios[0]), self.evaluador.evaluar(args_limpios[1])
                casos.append(self._ejecutar_escenario_aislado(
                    base_cond + [z3_arg1 <= (z3_arg2 - gap)], 
                    lambda: self._resolver_y_formatear(id_val, "CALCULO_MIN_IZQ", "El límite MIN toma el valor izquierdo garantizando su ruta.", "VERIFICAR_AUTOCALCULO")
                ))
                casos.append(self._ejecutar_escenario_aislado(
                    base_cond + [z3_arg1 >= (z3_arg2 + gap)], 
                    lambda: self._resolver_y_formatear(id_val, "CALCULO_MIN_DER", "El límite MIN toma el valor derecho garantizando su ruta.", "VERIFICAR_AUTOCALCULO")
                ))

            elif func_name == 'MAX':
                z3_arg1, z3_arg2 = self.evaluador.evaluar(args_limpios[0]), self.evaluador.evaluar(args_limpios[1])
                casos.append(self._ejecutar_escenario_aislado(
                    base_cond + [z3_arg1 >= (z3_arg2 + gap)], 
                    lambda: self._resolver_y_formatear(id_val, "CALCULO_MAX_IZQ", "El límite MAX toma el valor izquierdo garantizando su ruta.", "VERIFICAR_AUTOCALCULO")
                ))
                casos.append(self._ejecutar_escenario_aislado(
                    base_cond + [z3_arg1 <= (z3_arg2 - gap)], 
                    lambda: self._resolver_y_formatear(id_val, "CALCULO_MAX_DER", "El límite MAX toma el valor derecho garantizando su ruta.", "VERIFICAR_AUTOCALCULO")
                ))

            elif func_name == 'POS':
                z3_arg = self.evaluador.evaluar(args_limpios[0])
                casos.append(self._ejecutar_escenario_aislado(
                    base_cond + [z3_arg >= gap], 
                    lambda: self._resolver_y_formatear(id_val, "CALCULO_POS_MAYOR_CERO", "El valor interno de POS es positivo en su ruta correcta.", "VERIFICAR_AUTOCALCULO")
                ))
                casos.append(self._ejecutar_escenario_aislado(
                    base_cond + [z3_arg <= -gap], 
                    lambda: self._resolver_y_formatear(id_val, "CALCULO_POS_MENOR_CERO", "El valor interno de POS es negativo, forzando a 0.", "VERIFICAR_AUTOCALCULO")
                ))

            elif func_name == 'NEG':
                z3_arg = self.evaluador.evaluar(args_limpios[0])
                casos.append(self._ejecutar_escenario_aislado(
                    base_cond + [z3_arg <= -gap], 
                    lambda: self._resolver_y_formatear(id_val, "CALCULO_NEG_MENOR_CERO", "El valor interno de NEG es negativo, retornando valor absoluto.", "VERIFICAR_AUTOCALCULO")
                ))
                casos.append(self._ejecutar_escenario_aislado(
                    base_cond + [z3_arg >= gap], 
                    lambda: self._resolver_y_formatear(id_val, "CALCULO_NEG_MAYOR_CERO", "El valor interno de NEG es positivo, forzando a 0.", "VERIFICAR_AUTOCALCULO")
                ))

            elif func_name == 'ABS':
                z3_arg = self.evaluador.evaluar(args_limpios[0])
                casos.append(self._ejecutar_escenario_aislado(
                    base_cond + [z3_arg <= -gap], 
                    lambda: self._resolver_y_formatear(id_val, "ABS_ENTRADA_NEGATIVA", "El valor interno de ABS es negativo, forzando conversión a positivo.", "VERIFICAR_AUTOCALCULO")
                ))
                casos.append(self._ejecutar_escenario_aislado(
                    base_cond + [z3_arg >= gap], 
                    lambda: self._resolver_y_formatear(id_val, "ABS_ENTRADA_POSITIVA", "El valor interno de ABS es positivo, manteniendo su valor.", "VERIFICAR_AUTOCALCULO")
                ))

        # 3. EVALUAR RAMAS CONDICIONALES (MCDC RECURSIVO)
        nodos_condicional = self._encontrar_nodos_tipo(ast_tree, 'condicional')
        
        for idx, cond_node in enumerate(nodos_condicional, 1):
            z3_cond_actual = self.evaluador.evaluar(cond_node.children[0])
            if not z3.is_bool(z3_cond_actual):
                continue
                
            # Extraemos el camino necesario para que Z3 active obligatoriamente este IF
            camino_base = self._obtener_camino_a_nodo(cond_node, ast_tree)
            base_cond = ecuacion_completa + camino_base
            nivel = "PRINCIPAL" if idx == 1 else f"ANIDADO_{idx}"
            
            # Caso Verdadero
            casos.append(self._ejecutar_escenario_aislado(
                base_cond + [z3_cond_actual], 
                lambda n=nivel: self._resolver_y_formatear(
                    id_val, f"CALCULO_VERDADERO_{n}", 
                    f"La condición {n} se cumple (Rama ENTONCES alcanzada).", "VERIFICAR_AUTOCALCULO")
            ))
            
            # Casos Falsos (MCDC desglosado para este IF en particular)
            variaciones_falsas = self._desglosar_condicion_falsa(z3_cond_actual)
            for i, var_falsa in enumerate(variaciones_falsas, 1):
                sufijo = f"_{i}" if len(variaciones_falsas) > 1 else ""
                casos.append(self._ejecutar_escenario_aislado(
                    base_cond + [var_falsa["restriccion"]], 
                    lambda v=var_falsa, s=sufijo, n=nivel: self._resolver_y_formatear(
                        id_val, f"CALCULO_FALSO_{n}_SINO{s}", 
                        v["desc"], "VERIFICAR_AUTOCALCULO")
                ))

        # 4. FALLBACK LINEAL
        if not nodos_condicional and not nodos_func:
            casos.append(self._ejecutar_escenario_aislado(
                ecuacion_completa, 
                lambda: self._resolver_y_formatear(
                    id_val, "CALCULO_LINEAL_EXACTO", 
                    "Se resuelve la ecuación matemática lineal de forma exacta sin ramificaciones.", "VERIFICAR_AUTOCALCULO")
            ))

        # 5. DEDUPLICACIÓN EN CALIENTE Y LIMPIEZA
        casos_validos = []
        inputs_vistos = set()
        idx_real = 1
        
        for c in casos:
            if c is not None:
                if "error" in c:
                    print(f"⚠️ Aviso en {id_val}: Escenario descartado internamente. Motivo: {c['error']}")
                else:
                    firma_inputs = tuple(sorted(c["inputs"].items()))
                    if firma_inputs not in inputs_vistos:
                        inputs_vistos.add(firma_inputs)
                        c["id_validacion"] = f"{id_val}.{idx_real}"
                        idx_real += 1
                        casos_validos.append(c)
                    else:
                        print(f"Fase 2: Deduplicación en {id_val}: Caso '{c['tipo_escenario']}' ignorado por redundancia de inputs.")

        return casos_validos if casos_validos else [{"id_validacion": id_val, "error": "Inconsistencia matemática en todas las ramas."}]

    def _obtener_camino_a_nodo(self, nodo_objetivo, ast_tree):
        """
        Analiza el AST para descubrir qué condiciones superiores deben cumplirse 
        para que el flujo de ejecución alcance el nodo_objetivo.
        Implementa rastreo Sintáctico (anidamiento) y Semántico (uso de variables).
        """
        camino = []
        
        # 1. ¿El nodo objetivo pertenece a una variable declarada en una Cota?
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
            
            # A. Bloqueo Sintáctico (El nodo está físicamente dentro del IF)
            en_entonces = len(cond_node.children) >= 2 and self._contiene_nodo(cond_node.children[1], nodo_objetivo)
            en_sino = len(cond_node.children) >= 3 and self._contiene_nodo(cond_node.children[2], nodo_objetivo)
            
            # B. Bloqueo Semántico (El nodo define una variable que se usa dentro del IF)
            if not en_entonces and not en_sino and var_asociada:
                en_entonces = len(cond_node.children) >= 2 and self._contiene_texto(cond_node.children[1], var_asociada)
                en_sino = len(cond_node.children) >= 3 and self._contiene_texto(cond_node.children[2], var_asociada)
            
            # Forzamos a Z3 a tomar la ruta correcta para que la evaluación no quede flotando
            if en_entonces:
                camino.append(z3_cond_actual)
            elif en_sino:
                camino.append(z3.Not(z3_cond_actual))
                
        return camino

    def _contiene_nodo(self, raiz, nodo_buscado):
        """Búsqueda recursiva sintáctica."""
        if raiz is nodo_buscado:
            return True
        if hasattr(raiz, 'children'):
            for hijo in raiz.children:
                if self._contiene_nodo(hijo, nodo_buscado):
                    return True
        return False

    def _contiene_texto(self, raiz, texto):
        """Búsqueda recursiva semántica para ubicar dónde se usa una variable."""
        if hasattr(raiz, 'children'):
            for hijo in raiz.children:
                if self._contiene_texto(hijo, texto):
                    return True
        else:
            return str(raiz).strip().upper() == texto
        return False

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
                    "desc": f"La sub-condición {i+1} del IF falla, las demás se cumplen. Se fuerza la celda al valor por defecto (Sino)."
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