class RutProvider:
    def __init__(self, cache_ruts: list):
        """
        Recibe la lista de RUTs directamente desde la memoria RAM.
        """
        self.ruts = []
        if cache_ruts:
            # PREFERENCIA: Ordenamos priorizando los RUTs universales, 
            # y luego por número de RUT para mantener el determinismo.
            self.ruts = sorted(
                cache_ruts, 
                key=lambda x: (-x.get("es_formulario_universal", False), x.get("rut", ""))
            )

    def obtener_rut(self, atributos_req, atributos_prohibidos, tipo_req, subtipo_req):
        """
        Retorna el primer RUT del catálogo que cumpla ESTRICTAMENTE las matemáticas.
        Al estar pre-ordenado en el __init__, si existen varios que cumplan,
        siempre devolverá primero al que sea Universal.
        """
        def _norm_codigo(v):
            # Cosmos/API acepta Union[int, str] (ej. 8 vs "8"). Z3 siempre pide int.
            # Normalizamos a int cuando es numerico para evitar falsos "SIN_RUT_VALIDO".
            if v is None:
                return None
            try:
                return int(str(v).strip())
            except (ValueError, TypeError, AttributeError):
                return str(v).strip().upper()

        def _norm_attr(v):
            return str(v).strip().upper()

        def coincide_atributos(mock):
            atributos_mock = set(_norm_attr(a) for a in mock.get("atributos", []))
            if atributos_prohibidos and any(_norm_attr(atr) in atributos_mock for atr in atributos_prohibidos):
                return False
            if atributos_req and not all(_norm_attr(atr) in atributos_mock for atr in atributos_req):
                return False
            return True

        tipo_req_n = _norm_codigo(tipo_req) if tipo_req is not None else None
        subtipo_req_n = _norm_codigo(subtipo_req) if subtipo_req is not None else None

        # --- ÚNICO NIVEL: BÚSQUEDA ESTRICTA ---
        for mock in self.ruts:
            # ATENCIÓN: Cambiamos "tipo" por "tipo_contribuyente" por conflicto con Partition Key
            tipo_mock = _norm_codigo(mock.get("tipo_contribuyente"))
            subtipo_mock = _norm_codigo(mock.get("subtipo"))

            # Tolerancia Cero: Deben cumplir la matemática de Z3 sí o sí.
            if tipo_req_n is not None and tipo_mock != tipo_req_n:
                continue
            if subtipo_req_n is not None and subtipo_mock != subtipo_req_n:
                continue
            if not coincide_atributos(mock):
                continue
                
            # Si llegó aquí, cumplió todos los requisitos de Z3.
            # Retorna el primero (que será universal si existe, gracias al sorted).
            return mock.get("rut")

        # Si termina el bucle, simplemente no hay ningún RUT en la BD
        # que cumpla con la regla tributaria. 
        return "SIN_RUT_VALIDO"