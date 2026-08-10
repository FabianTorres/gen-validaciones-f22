class RutProvider:
    def __init__(self, cache_ruts: list):
        """
        Recibe la lista de RUTs directamente desde la memoria RAM.
        Eliminamos la lectura de mock_ruts_qa.json.
        """
        self.ruts = []
        if cache_ruts:
            # Mantenemos tu lógica de orden determinista invariable
            self.ruts = sorted(cache_ruts, key=lambda x: x.get("rut", ""))
        # else:
        #     print("⚠️ Aviso: Caché de RUTs vacío. Se usarán RUTs de contingencia.")
        #     self.ruts = [
        #         {"rut": "99.999.999-9", "tipo_contribuyente": 1, "subtipo": 111, "atributos": []},
        #         {"rut": "11.111.111-1", "tipo_contribuyente": 1, "subtipo": 112, "atributos": ["M14A"]},
        #         {"rut": "22.222.222-2", "tipo_contribuyente": 2, "subtipo": 211, "atributos": ["M14B"]}
        #     ]

    def obtener_rut(self, atributos_req, atributos_prohibidos, tipo_req, subtipo_req):
        """
        Retorna el primer RUT del catálogo que cumpla las condiciones.
        """
        def coincide_atributos(mock):
            atributos_mock = set(mock.get("atributos", []))
            if atributos_prohibidos and any(atr in atributos_mock for atr in atributos_prohibidos):
                return False
            if atributos_req and not all(atr in atributos_mock for atr in atributos_req):
                return False
            return True

        # --- NIVEL 1: BÚSQUEDA ESTRICTA ---
        for mock in self.ruts:
            # ATENCIÓN: Cambiamos "tipo" por "tipo_contribuyente" por conflicto con Partition Key
            tipo_mock = mock.get("tipo_contribuyente")
            subtipo_mock = mock.get("subtipo")
            
            if tipo_req is not None and tipo_mock != tipo_req:
                continue
            if subtipo_req is not None and subtipo_mock != subtipo_req:
                continue
            if coincide_atributos(mock):
                return mock.get("rut")

        # --- NIVEL 2: RELAJAR TIPO ---
        for mock in self.ruts:
            subtipo_mock = mock.get("subtipo")
            if subtipo_req is not None and subtipo_mock != subtipo_req:
                continue
            if coincide_atributos(mock):
                return mock.get("rut")

        # --- NIVEL 3: RELAJAR SUBTIPO ---
        for mock in self.ruts:
            if coincide_atributos(mock):
                return mock.get("rut")

        return "SIN_RUT_VALIDO"