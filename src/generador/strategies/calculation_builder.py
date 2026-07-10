import z3
from src.generador.strategies.base_strategy import BaseStrategy

class CalculationBuilder(BaseStrategy):
    """
    Estrategia Experta para Validaciones Tipo A, B (Autocalculadas) y M (Lógica Libre).
    Genera el escenario base (Happy Path) donde la ecuación matemática se cumple 
    perfectamente, entregando los inputs exactos para validar la celda bloqueada.
    """

    def generar_casos(self, ast_tree, id_val):
        casos = []
        
        # 1. Encontrar el nodo principal (autocalculado o validacion_libre)
        nodo_principal = None
        for hijo in ast_tree.children:
            if hasattr(hijo, 'data') and hijo.data in ['autocalculado', 'validacion_libre']:
                nodo_principal = hijo
                break
                
        if not nodo_principal:
            return [{"id_validacion": id_val, "error": "No se encontró nodo de cálculo en el AST."}]

        # 2. Traducir la ecuación completa a Z3 (El evaluador ya sabe que 'autocalculado' es A == B)
        z3_ecuacion = self.evaluador.evaluar(nodo_principal)

        # --- CASO 1: CÁLCULO EXACTO (Happy Path) ---
        casos.append(
            self._ejecutar_escenario_aislado(
                [z3_ecuacion], 
                lambda: self._resolver_y_formatear(
                    id_val, 
                    "CALCULO_ESPERADO", 
                    "El portal debe calcular automáticamente este monto en base a los inputs ingresados. No se levanta validación.", 
                    "VERIFICAR_AUTOCALCULO"
                )
            )
        )

        # Numeramos dinámicamente los casos generados (ej. a.190.1)
        for idx, caso in enumerate(casos, 1):
            if "id_validacion" in caso:
                caso["id_validacion"] = f"{id_val}.{idx}"

        return casos