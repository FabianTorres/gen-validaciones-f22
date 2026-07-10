import json
import random

class RutProvider:
    def __init__(self, ruta_json="data/mock_ruts_qa.json"):
        self.ruta_json = ruta_json
        self.ruts = self._cargar_datos()

    def _cargar_datos(self):
        try:
            with open(self.ruta_json, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            return []

    def obtener_rut(self, atributos_req, atributos_prohibidos, tipo_req=None):
        """
        Filtra la base de datos de RUTs asegurando que cumpla 
        las exigencias lógicas de Z3.
        """
        candidatos = []
        for contribuyente in self.ruts:
            atributos_contrib = contribuyente.get("atributos", [])
            
            # 1. Filtro Tipo (ej. TIPO([03]) = 1)
            if tipo_req is not None and contribuyente.get("tipo") != tipo_req:
                continue
                
            # 2. Filtro Atributos Requeridos (Debe tenerlos TODOS)
            if not all(atr in atributos_contrib for atr in atributos_req):
                continue
                
            # 3. Filtro Atributos Prohibidos (No debe tener NINGUNO)
            if any(atr in atributos_contrib for atr in atributos_prohibidos):
                continue
                
            candidatos.append(contribuyente["rut"])
            
        # Si encuentra coincidencias, elige uno al azar para dar variedad al QA
        if candidatos:
            return random.choice(candidatos)
            
        return "ERROR_SIN_RUT_COMPATIBLE"