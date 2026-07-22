import json
import os

class RutProvider:
    def __init__(self, ruta_json="data/mock_ruts_qa.json"):
        self.ruts = []
        if os.path.exists(ruta_json):
            with open(ruta_json, 'r', encoding='utf-8') as f:
                self.ruts = json.load(f)
        else:
            print(f"⚠️ Aviso: No se encontró {ruta_json}. Se usarán RUTs de contingencia deterministas.")
            self.ruts = [
                {"rut": "99.999.999-9", "tipo": 1, "subtipo": 111, "atributos": []},
                {"rut": "11.111.111-1", "tipo": 1, "subtipo": 112, "atributos": ["M14A"]},
                {"rut": "22.222.222-2", "tipo": 2, "subtipo": 211, "atributos": ["M14B"]}
            ]
            
        # MAGIA DETERMINISTA: Ordenamos la lista por RUT para "congelar" el orden en memoria.
        # Esto asegura que la búsqueda siempre itere en el mismo orden exacto.
        self.ruts = sorted(self.ruts, key=lambda x: x.get("rut", ""))

    def obtener_rut(self, atributos_req, atributos_prohibidos, tipo_req, subtipo_req):
        """
        Retorna el primer RUT del catálogo que cumpla todas las condiciones.
        Al no usar random y tener la lista ordenada, el resultado es 100% determinista.
        """
        for mock in self.ruts:
            tipo_mock = mock.get("tipo")
            subtipo_mock = mock.get("subtipo")
            atributos_mock = set(mock.get("atributos", []))
            
            # 1. Filtro de Tipo (Reglas TIPO([03]) = X)
            if tipo_req is not None and tipo_mock != tipo_req:
                continue
                
            # 2. Filtro de Subtipo (Reglas SUBTIPO([03]) = X)
            if subtipo_req is not None and subtipo_mock != subtipo_req:
                continue
                
            # 3. Filtro de Atributos Prohibidos
            if atributos_prohibidos and any(atr in atributos_mock for atr in atributos_prohibidos):
                continue
                
            # 4. Filtro de Atributos Requeridos
            if atributos_req and not all(atr in atributos_mock for atr in atributos_req):
                continue
                
            # Si el RUT sobrevive a todos los filtros, es el elegido.
            return mock.get("rut")
            
        # NUEVO: Si la regla exige una combinación que no existe en el catálogo, 
        # devolvemos un string explícito de error en lugar de un RUT genérico.
        return "SIN_RUT_VALIDO"