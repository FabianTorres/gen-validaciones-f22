class RutProvider:
    def __init__(self, cache_ruts: list):
        """
        Recibe la lista de RUTs directamente desde la memoria RAM.
        Eliminamos la lectura de mock_ruts_qa.json.
        """
        self.ruts = []
        if cache_ruts:
            # MAGIA HEURÍSTICA: Ordenamos priorizando los RUTs universales, 
            # y luego por número de RUT para mantener el determinismo.
            # El signo negativo (-) hace un orden descendente (True va antes que False).
            self.ruts = sorted(
                cache_ruts, 
                key=lambda x: (-x.get("es_formulario_universal", False), x.get("rut", ""))
            )

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