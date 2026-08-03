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
            
        # Orden determinista invariable
        self.ruts = sorted(self.ruts, key=lambda x: x.get("rut", ""))

    def obtener_rut(self, atributos_req, atributos_prohibidos, tipo_req, subtipo_req):
        """
        Retorna el primer RUT del catálogo que cumpla las condiciones.
        Aplica una cascada de búsqueda priorizada para garantizar compatibilidad hacia atrás
        y evitar falsos "SIN_RUT_VALIDO" cuando Z3 asigna valores a variables no restrictivas.
        """
        def coincide_atributos(mock):
            atributos_mock = set(mock.get("atributos", []))
            
            # Filtro de Atributos Prohibidos
            if atributos_prohibidos and any(atr in atributos_mock for atr in atributos_prohibidos):
                return False
                
            # Filtro de Atributos Requeridos
            if atributos_req and not all(atr in atributos_mock for atr in atributos_req):
                return False
                
            return True

        # --- NIVEL 1: BÚSQUEDA ESTRICTA (COMPORTAMIENTO ORIGINAL) ---
        # Si un caso de A, B o C funcionaba antes, se resuelve exactamente aquí sin cambios.
        for mock in self.ruts:
            tipo_mock = mock.get("tipo")
            subtipo_mock = mock.get("subtipo")
            
            if tipo_req is not None and tipo_mock != tipo_req:
                continue
            if subtipo_req is not None and subtipo_mock != subtipo_req:
                continue
            if coincide_atributos(mock):
                return mock.get("rut")

        # --- NIVEL 2: RELAJAR TIPO ---
        # Si Z3 asignó un Tipo que la regla no exigía estrictamente, buscamos por (Subtipo + Atributos).
        for mock in self.ruts:
            subtipo_mock = mock.get("subtipo")
            
            if subtipo_req is not None and subtipo_mock != subtipo_req:
                continue
            if coincide_atributos(mock):
                return mock.get("rut")

        # --- NIVEL 3: RELAJAR SUBTIPO ---
        # Si la regla sólo evaluaba Atributos (ej. violación de Atributo), buscamos por Atributos puros.
        for mock in self.ruts:
            if coincide_atributos(mock):
                return mock.get("rut")

        return "SIN_RUT_VALIDO"