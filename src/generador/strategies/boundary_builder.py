from src.generador.strategies.base_strategy import BaseStrategy

class BoundaryBuilder(BaseStrategy):
    def generar_casos(self, ast_tree, id_val):
        casos = []
        
        nodo_cota = self._encontrar_nodo_cota(ast_tree)
        if not nodo_cota:
            return [{"id_validacion": id_val, "error": "No se encontró nodo de cota en el AST."}]

        z3_izq = self.evaluador.evaluar(nodo_cota.children[0])
        operador = str(self.evaluador.evaluar(nodo_cota.children[1])).strip()
        z3_der = self.evaluador.evaluar(nodo_cota.children[2])

        # MAPA LÓGICO BVA (Boundary Value Analysis)
        # Define qué etiqueta corresponde según el operador y la frontera.
        # Orden de la tupla: (Frontera Exacta, Frontera Superior +1, Frontera Inferior -1)
        mapa_resultados = {
            '<=': ('BUENO', 'MENSAJE', 'BUENO'),
            '<':  ('MENSAJE', 'MENSAJE', 'BUENO'),
            '>=': ('BUENO', 'BUENO', 'MENSAJE'),
            '>':  ('MENSAJE', 'BUENO', 'MENSAJE'),
            '=':  ('BUENO', 'MENSAJE', 'MENSAJE'),
            '!=': ('MENSAJE', 'BUENO', 'BUENO')
        }
        
        # Obtenemos las etiquetas correctas. Si el operador es raro, asumimos BUENO por seguridad.
        res_exacto, res_sup, res_inf = mapa_resultados.get(operador, ('BUENO', 'BUENO', 'BUENO'))

        # --- CASO 1: FRONTERA EXACTA ---
        casos.append(
            self._ejecutar_escenario_aislado(
                [z3_izq == z3_der], 
                lambda: self._resolver_y_formatear(
                    id_val, 
                    "LIMITE_EXACTO", 
                    "El valor ingresado es exactamente igual al límite matemático de la regla.", 
                    res_exacto
                )
            )
        )

        # --- CASO 2: FRONTERA SUPERIOR (+ 1 PESO) ---
        casos.append(
            self._ejecutar_escenario_aislado(
                [z3_izq == (z3_der + 1)], 
                lambda: self._resolver_y_formatear(
                    id_val, 
                    "EXCEDE_LIMITE", 
                    "El valor ingresado supera el tope permitido de la regla por 1 peso.", 
                    res_sup
                )
            )
        )

        # --- CASO 3: FRONTERA INFERIOR (- 1 PESO) ---
        casos.append(
            self._ejecutar_escenario_aislado(
                [z3_izq == (z3_der - 1)], 
                lambda: self._resolver_y_formatear(
                    id_val, 
                    "BAJO_LIMITE", 
                    "El valor ingresado se mantiene justo por debajo del límite de la regla.", 
                    res_inf
                )
            )
        )

        # FILTRO Y NUMERACIÓN: Solo guardamos los casos que Z3 logró resolver lógicamente
        casos_validos = []
        idx = 1
        for caso in casos:
            if caso and caso.get("estado_interno") != "INSATISFACTIBLE":
                caso["id_validacion"] = f"{id_val}.{idx}"
                idx += 1
                casos_validos.append(caso)

        return casos_validos if casos_validos else [{"id_validacion": id_val, "error": "Contradicción matemática en el cálculo de límites."}]

    def _encontrar_nodo_cota(self, nodo):
        if hasattr(nodo, 'data') and nodo.data == 'cota':
            return nodo
        if hasattr(nodo, 'children'):
            for hijo in nodo.children:
                encontrado = self._encontrar_nodo_cota(hijo)
                if encontrado:
                    return encontrado
        return None