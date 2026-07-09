import json
import z3

class ParamProvider:
    def __init__(self, ruta_json="data/mock_parametros.json"):
        self.ruta_json = ruta_json
        self.parametros = self._cargar_datos()

    def _cargar_datos(self):
        try:
            with open(self.ruta_json, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            # Fallback seguro con decimales
            return {
                "P08": 1500000,
                "P42": 800000,
                "P84": 1.05,       
                "P736": 250000,    
                "P722": 100000,
                "P11": 0.19        
            }

    def inyectar_en_motor(self, motor_z3):
        """
        Inyecta todos los parámetros blindados contra errores tipográficos.
        """
        for nombre, valor in self.parametros.items():
            # Forzamos a Float nativo de Python para limpiar basura del JSON
            # antes de entregárselo al estricto parser de C++ de Z3
            try:
                valor_limpio = float(valor)
            except (ValueError, TypeError):
                valor_limpio = 0.0
                
            motor_z3.variables_memoria[nombre] = z3.RealVal(valor_limpio)