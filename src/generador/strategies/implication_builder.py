import z3
from src.generador.strategies.base_strategy import BaseStrategy

class ImplicationBuilder(BaseStrategy):
    """
    Estrategia Experta para Validaciones Tipo D y E (Implicaciones Lógicas).
    Genera matrices de pruebas basadas en Tablas de Verdad para garantizar
    que las dependencias obligatorias disparen los bloqueos correctos.
    """

    def generar_casos(self, ast_tree, id_val):
        casos = []
        
        nodo_impl = self._encontrar_nodo_implicacion(ast_tree)
        if not nodo_impl:
            return [{"id_validacion": id_val, "error": "No se encontró nodo de implicacion en el AST."}]

        z3_gatillo = self.evaluador.evaluar(nodo_impl.children[0])
        z3_consecuencia = self.evaluador.evaluar(nodo_impl.children[2])

        # --- CASO 1: FLUJO IDEAL (CUMPLE Y CUMPLE) ---
        casos.append(
            self._ejecutar_escenario_aislado(
                [z3_gatillo, z3_consecuencia], 
                lambda: self._resolver_y_formatear(
                    id_val, 
                    "CUMPLE_CONDICION", 
                    "El contribuyente cumple la condición inicial y también satisface la exigencia final de la regla.", 
                    "SIN_VALIDACION"
                )
            )
        )

        # --- CASO 2: QUIEBRE DE REGLA (FALLA ESPERADA EN SII) ---
        casos.append(
            self._ejecutar_escenario_aislado(
                [z3_gatillo, z3.Not(z3_consecuencia)], 
                lambda: self._resolver_y_formatear(
                    id_val, 
                    "INCUMPLE_CONDICION", 
                    "Se fuerza un error: El contribuyente cumple la condición inicial, pero se omite llenar la exigencia final obligatoria.", 
                    "CON_VALIDACION"
                )
            )
        )

        # --- CASO 3: OMISIÓN (NO APLICA LA REGLA) ---
        casos.append(
            self._ejecutar_escenario_aislado(
                [z3.Not(z3_gatillo)], 
                lambda: self._resolver_y_formatear(
                    id_val, 
                    "NO_APLICA", 
                    "La regla no aplica para este caso (ej. atributos de RUT distintos). El sistema no debería exigir nada adicional.", 
                    "SIN_VALIDACION"
                )
            )
        )

        # Numeramos dinámicamente los casos generados (ej. d.150.1, d.150.2)
        for idx, caso in enumerate(casos, 1):
            if "id_validacion" in caso:
                caso["id_validacion"] = f"{id_val}.{idx}"

        return casos

    def _encontrar_nodo_implicacion(self, arbol):
        for hijo in arbol.children:
            if hasattr(hijo, 'data') and hijo.data == 'implicacion':
                return hijo
        return None