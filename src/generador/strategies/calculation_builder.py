import z3
from src.generador.strategies.base_strategy import BaseStrategy

class CalculationBuilder(BaseStrategy):
    """
    Estrategia Experta para Validaciones Tipo A, B.
    Incluye 'Branch Explorer' para probar ramificaciones como MIN, MAX, POS
    y MCDC para aislar fallos en AND lógicos.
    """

    def generar_casos(self, ast_tree, id_val):
        casos = []
        
        nodo_principal = self._encontrar_nodos_tipo(ast_tree, 'autocalculado')
        if not nodo_principal:
            nodo_principal = self._encontrar_nodos_tipo(ast_tree, 'validacion_libre')
            
        if not nodo_principal:
            return [{"id_validacion": id_val, "error": "No se encontró nodo de cálculo."}]
            
        z3_ecuacion = self.evaluador.evaluar(nodo_principal[0])

        # 1. Analizar el AST buscando piezas clave
        nodos_condicion = self._encontrar_nodos_tipo(ast_tree, 'caso_trailing')
        nodos_func = self._encontrar_nodos_tipo(ast_tree, 'funcion_matematica')
        
        # Extraer condicional base si existe
        z3_cond = self.evaluador.evaluar(nodos_condicion[0].children[-1]) if nodos_condicion else None
        condiciones_base = [z3_ecuacion, z3_cond] if z3_cond is not None else [z3_ecuacion]

        # Buscar si hay alguna función de partición (MIN, MAX, POS)
        nodo_min = next((n for n in nodos_func if str(n.children[0]).upper() == 'MIN'), None)
        nodo_max = next((n for n in nodos_func if str(n.children[0]).upper() == 'MAX'), None)
        nodo_pos = next((n for n in nodos_func if str(n.children[0]).upper() == 'POS'), None)

        # --- RAMIFICACIÓN PRINCIPAL ---
        if nodo_min or nodo_max:
            nodo_objetivo = nodo_min if nodo_min else nodo_max
            es_min = bool(nodo_min)
            
            args_node = nodo_objetivo.children[2]
            args_limpios = [h for h in args_node.children if str(h) != ';']
            z3_arg1 = self.evaluador.evaluar(args_limpios[0])
            z3_arg2 = self.evaluador.evaluar(args_limpios[1])
            
            prefijo = "CALCULO_VERDADERO_" if z3_cond is not None else "CALCULO_"

            if es_min:
                casos.append(self._ejecutar_escenario_aislado(
                    condiciones_base + [z3_arg1 < z3_arg2], 
                    lambda: self._resolver_y_formatear(
                        id_val, f"{prefijo}MIN_IZQ", 
                        "La condición se cumple (si aplica) y el límite MIN toma el valor izquierdo.", "VERIFICAR_AUTOCALCULO")
                ))
                casos.append(self._ejecutar_escenario_aislado(
                    condiciones_base + [z3_arg2 < z3_arg1], 
                    lambda: self._resolver_y_formatear(
                        id_val, f"{prefijo}MIN_DER", 
                        "La condición se cumple (si aplica) y el límite MIN se topa con el valor derecho.", "VERIFICAR_AUTOCALCULO")
                ))
            else:
                casos.append(self._ejecutar_escenario_aislado(
                    condiciones_base + [z3_arg1 > z3_arg2], 
                    lambda: self._resolver_y_formatear(
                        id_val, f"{prefijo}MAX_IZQ", 
                        "La condición se cumple (si aplica) y el límite MAX toma el valor izquierdo.", "VERIFICAR_AUTOCALCULO")
                ))
                casos.append(self._ejecutar_escenario_aislado(
                    condiciones_base + [z3_arg2 > z3_arg1], 
                    lambda: self._resolver_y_formatear(
                        id_val, f"{prefijo}MAX_DER", 
                        "La condición se cumple (si aplica) y el límite MAX se topa con el valor derecho.", "VERIFICAR_AUTOCALCULO")
                ))

        elif nodo_pos:
            args_node = nodo_pos.children[2]
            # Extraemos el primer argumento limpio (igual que hicimos con MIN/MAX)
            args_limpios = [h for h in args_node.children if str(h) != ';']
            z3_arg_pos = self.evaluador.evaluar(args_limpios[0])
            
            prefijo = "CALCULO_VERDADERO_" if z3_cond is not None else "CALCULO_"

            casos.append(self._ejecutar_escenario_aislado(
                condiciones_base + [z3_arg_pos > 0], 
                lambda: self._resolver_y_formatear(
                    id_val, f"{prefijo}POS_MAYOR_CERO", 
                    "El valor interno de la función POS es positivo, por lo que el monto se mantiene intacto.", "VERIFICAR_AUTOCALCULO")
            ))
            casos.append(self._ejecutar_escenario_aislado(
                condiciones_base + [z3_arg_pos <= 0], 
                lambda: self._resolver_y_formatear(
                    id_val, f"{prefijo}POS_MENOR_CERO", 
                    "El valor interno de la función POS es negativo o cero, forzando la función a topar en 0.", "VERIFICAR_AUTOCALCULO")
            ))

        elif z3_cond is not None:
            casos.append(self._ejecutar_escenario_aislado(
                condiciones_base, 
                lambda: self._resolver_y_formatear(
                    id_val, "CALCULO_VERDADERO_SIMPLE", 
                    "La condición del IF se cumple y se calcula el monto directo.", "VERIFICAR_AUTOCALCULO")
            ))

        else:
            casos.append(self._ejecutar_escenario_aislado(
                condiciones_base, 
                lambda: self._resolver_y_formatear(
                    id_val, "CALCULO_LINEAL_EXACTO", 
                    "Se resuelve la ecuación matemática lineal de forma exacta sin ramificaciones.", "VERIFICAR_AUTOCALCULO")
            ))

        # --- RAMIFICACIÓN MCDC (FALSOS) ---
        if z3_cond is not None:
            variaciones_falsas = self._desglosar_condicion_falsa(z3_cond)
            for i, var_falsa in enumerate(variaciones_falsas, 1):
                sufijo = f"_{i}" if len(variaciones_falsas) > 1 else ""
                casos.append(self._ejecutar_escenario_aislado(
                    [z3_ecuacion, var_falsa["restriccion"]], 
                    lambda v=var_falsa, s=sufijo: self._resolver_y_formatear(
                        id_val, f"CALCULO_FALSO_SINO{s}", 
                        v["desc"], "VERIFICAR_AUTOCALCULO")
                ))

        for idx, caso in enumerate(casos, 1):
            if "id_validacion" in caso:
                caso["id_validacion"] = f"{id_val}.{idx}"

        return casos

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