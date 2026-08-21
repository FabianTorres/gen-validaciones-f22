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
        def coincide_atributos(mock):
            atributos_mock = set(mock.get("atributos", []))
            if atributos_prohibidos and any(atr in atributos_mock for atr in atributos_prohibidos):
                return False
            if atributos_req and not all(atr in atributos_mock for atr in atributos_req):
                return False
            return True

        # --- ÚNICO NIVEL: BÚSQUEDA ESTRICTA ---
        for mock in self.ruts:
            # ATENCIÓN: Cambiamos "tipo" por "tipo_contribuyente" por conflicto con Partition Key
            tipo_mock = mock.get("tipo_contribuyente")
            subtipo_mock = mock.get("subtipo")
            
            # Tolerancia Cero: Deben cumplir la matemática de Z3 sí o sí.
            if tipo_req is not None and tipo_mock != tipo_req:
                continue
            if subtipo_req is not None and subtipo_mock != subtipo_req:
                continue
            if not coincide_atributos(mock):
                continue
                
            # Si llegó aquí, cumplió todos los requisitos de Z3.
            # Retorna el primero (que será universal si existe, gracias al sorted).
            return mock.get("rut")

        # Si termina el bucle, simplemente no hay ningún RUT en la BD
        # que cumpla con la regla tributaria. 
        return "SIN_RUT_VALIDO"