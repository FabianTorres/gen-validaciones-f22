from src.generador.strategies.base_strategy import BaseStrategy

class BoundaryBuilder(BaseStrategy):
    def generar_casos(self, ast_tree, id_val):
        casos = []
        
        nodo_cota = self._encontrar_nodo_cota(ast_tree)
        if not nodo_cota:
            return [{"id_validacion": id_val, "error": "No se encontró nodo de cota en el AST."}]

        z3_izq = self.evaluador.evaluar(nodo_cota.children[0])
        operador = str(self.evaluador.evaluar(nodo_cota.children[1]))
        z3_der = self.evaluador.evaluar(nodo_cota.children[2])

        rut_simulado = self.rut_provider.obtener_rut_por_defecto() if self.rut_provider else "11.111.111-1"

        # --- CASO 1: FRONTERA EXACTA ---
        es_error_exacto = "CON_VALIDACION" if operador in ['<', '>'] else None
        
        casos.append(
            self._ejecutar_escenario_aislado(
                [z3_izq == z3_der], 
                lambda: self._resolver_y_formatear(
                    id_val, 
                    "FRONTERA_EXACTA", 
                    "Se fuerza igualdad: Lado Izquierdo == Lado Derecho", 
                    rut_simulado, 
                    es_error_exacto
                )
            )
        )

        # --- CASO 2: FRONTERA SUPERIOR (+ 1 PESO) ---
        es_error_superior = "CON_VALIDACION" if operador in ['<=', '<', '='] else None
        
        casos.append(
            self._ejecutar_escenario_aislado(
                [z3_izq == (z3_der + 1)], 
                lambda: self._resolver_y_formatear(
                    id_val, 
                    "FRONTERA_SUPERIOR", 
                    "Se excede el tope: Lado Izquierdo == Lado Derecho + 1", 
                    rut_simulado, 
                    es_error_superior
                )
            )
        )

        # --- CASO 3: FRONTERA INFERIOR (- 1 PESO) ---
        es_error_inferior = "CON_VALIDACION" if operador in ['>=', '>', '='] else None
        
        casos.append(
            self._ejecutar_escenario_aislado(
                [z3_izq == (z3_der - 1)], 
                lambda: self._resolver_y_formatear(
                    id_val, 
                    "FRONTERA_INFERIOR", 
                    "Bajo el tope: Lado Izquierdo == Lado Derecho - 1", 
                    rut_simulado, 
                    es_error_inferior
                )
            )
        )

        # MAGIA AQUÍ: Numeramos dinámicamente los casos generados
        for idx, caso in enumerate(casos, 1):
            if "id_validacion" in caso:
                caso["id_validacion"] = f"{id_val}.{idx}"

        return casos

    def _encontrar_nodo_cota(self, arbol):
        for hijo in arbol.children:
            if hasattr(hijo, 'data') and hijo.data == 'cota':
                return hijo
        return None