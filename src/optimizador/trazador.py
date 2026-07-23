import z3
from src.generador.z3_core import MotorZ3

class TrazadorLogico:
    """
    Simula la ejecución de una regla matemática inyectando los inputs generados
    para descubrir exactamente qué ruta lógica real transitó el caso.
    """
    def __init__(self):
        self.evaluador = MotorZ3()

    def obtener_huella(self, ast_tree, inputs):
        # Convertimos el diccionario de Selenium en sustituciones de Z3
        subs = [(z3.Real(k), z3.RealVal(v)) for k, v in inputs.items()]
        huella = set()

        # 1. RASTREO DE FUNCIONES (MIN, MAX, POS, NEG)
        nodos_func = self._encontrar_nodos(ast_tree, 'funcion_matematica')
        for i, nodo in enumerate(nodos_func, 1):
            nombre = str(nodo.children[0]).upper()
            args = [h for h in nodo.children[2].children if str(h) != ';']
            
            if nombre in ('MIN', 'MAX') and len(args) >= 2:
                v1 = self._eval_con_subs(self.evaluador.evaluar(args[0]), subs)
                v2 = self._eval_con_subs(self.evaluador.evaluar(args[1]), subs)
                gana = "ARG_1" if (v1 <= v2 if nombre == 'MIN' else v1 >= v2) else "ARG_2"
                huella.add(f"{nombre}_{i}_{gana}")
                
            elif nombre == 'POS':
                v1 = self._eval_con_subs(self.evaluador.evaluar(args[0]), subs)
                huella.add(f"POS_{i}_MAYOR_0" if v1 > 0 else f"POS_{i}_CERO")
                
            elif nombre == 'NEG':
                v1 = self._eval_con_subs(self.evaluador.evaluar(args[0]), subs)
                huella.add(f"NEG_{i}_MAYOR_0" if v1 >= 0 else f"NEG_{i}_MENOR_0")

        # 2. RASTREO CONDICIONAL (SI / SINO)
        nodos_cond = self._encontrar_nodos(ast_tree, 'condicional')
        for i, nodo in enumerate(nodos_cond, 1):
            z3_cond = self.evaluador.evaluar(nodo.children[0])
            evaluado = z3.simplify(z3.substitute(z3_cond, *subs))
            huella.add(f"IF_{i}_TRUE" if z3.is_true(evaluado) else f"IF_{i}_FALSE")

        # 3. RASTREO DE COTA (Evaluación del Límite Final)
        nodo_cota = self._encontrar_nodos(ast_tree, 'cota')
        if nodo_cota:
            v_izq = self._eval_con_subs(self.evaluador.evaluar(nodo_cota[0].children[0]), subs)
            v_der = self._eval_con_subs(self.evaluador.evaluar(nodo_cota[0].children[2]), subs)
            operador = str(self.evaluador.evaluar(nodo_cota[0].children[1])).strip()
            
            # Determinamos si el límite fue exacto, si excedió o faltó
            if v_izq == v_der: huella.add(f"COTA_LIMITE_EXACTO")
            elif v_izq > v_der: huella.add(f"COTA_LIMITE_SUPERIOR")
            elif v_izq < v_der: huella.add(f"COTA_LIMITE_INFERIOR")

        return tuple(sorted(huella))

    def _eval_con_subs(self, z3_expr, subs):
        """Simplifica la expresión con los valores numéricos inyectados."""
        resultado = z3.simplify(z3.substitute(z3_expr, *subs))
        if z3.is_rational_value(resultado): return resultado.as_fraction()
        if z3.is_int(resultado): return resultado.as_long()
        if z3.is_real(resultado) or z3.is_algebraic_value(resultado): return float(resultado.as_decimal(4).rstrip('?'))
        return 0

    def _encontrar_nodos(self, arbol, tipo_data):
        encontrados = []
        if hasattr(arbol, 'data'):
            if arbol.data == tipo_data: encontrados.append(arbol)
            for hijo in arbol.children:
                if hasattr(hijo, 'data') or hasattr(hijo, 'value'):
                    encontrados.extend(self._encontrar_nodos(hijo, tipo_data))
        return encontrados