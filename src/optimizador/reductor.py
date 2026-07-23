class ReductorSetCover:
    """
    Aplica la regla estricta de Subconjuntos y Fusión Física.
    Si dos casos tienen la misma huella estructural y el mismo resultado de negocio, uno sobra.
    """
    def optimizar(self, casos_con_huellas):
        casos_sobrevivientes = {}
        idx_real = 1

        for caso in casos_con_huellas:
            if caso.get("estado_interno") == "INSATISFACTIBLE" or "error" in caso:
                continue

            huella = caso["huella_real"]
            rut = caso.get("rut", "")
            resultado = caso.get("resultado_esperado", "")
            objetivo_val = caso.get("objetivo", {}).get("valor", "")

            # Firma Lógica Absoluta (Agnóstica al nombre 'tipo_escenario' del generador)
            firma = (huella, rut, resultado, objetivo_val)

            if firma not in casos_sobrevivientes:
                # Este caso probó una ruta nueva que nadie más había probado
                caso_limpio = caso.copy()
                
                # Actualizamos su metadata para reflejar la realidad del nodo
                caso_limpio["huellas_cubiertas"] = [huella]
                del caso_limpio["huella_real"]  # Limpiamos el temporal
                
                casos_sobrevivientes[firma] = caso_limpio
            else:
                # REDUNDANCIA DETECTADA: Alguien más ya probó esta misma ruta matemática
                caso_existente = casos_sobrevivientes[firma]
                
                # Fusionamos la descripción para no perder el contexto de lo que el generador intentó hacer
                if caso['tipo_escenario'] not in caso_existente['tipo_escenario']:
                    caso_existente["tipo_escenario"] += f" | {caso['tipo_escenario']}"
                if caso['descripcion_qa'] not in caso_existente['descripcion_qa']:
                    caso_existente["descripcion_qa"] += f" || {caso['descripcion_qa']}"

        # Renumerar de forma limpia
        casos_finales = list(casos_sobrevivientes.values())
        id_base = ".".join(casos_finales[0]["id_validacion"].split(".")[:-1]) if casos_finales else "val"
        
        for i, c in enumerate(casos_finales, 1):
            c["id_validacion"] = f"{id_base}.{i}"

        return casos_finales