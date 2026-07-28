class ReductorCasos:
    def __init__(self):
        self.casos_optimizados = {}
        self.orden_reglas = [] # <--- NUEVO: Memoria para mantener tu orden original

    def procesar_casos(self, lista_casos: list) -> list:
        for caso in lista_casos:
            id_val_original = caso.get("id_validacion", "")
            id_val_base = id_val_original.rsplit(".", 1)[0] if "." in id_val_original else id_val_original
            
            # Guardamos el orden en que van apareciendo las reglas
            if id_val_base not in self.orden_reglas:
                self.orden_reglas.append(id_val_base)
            
            res_esperado = caso.get("resultado_esperado", "DEFAULT")
            huella_dict = caso.get("huella_logica", {})
            huella_str = str(tuple(sorted(huella_dict.items())))
            
            firma_unica = f"{id_val_base}|{res_esperado}|{huella_str}"

            if firma_unica not in self.casos_optimizados:
                self.casos_optimizados[firma_unica] = caso
            else:
                caso_existente = self.casos_optimizados[firma_unica]
                # Competencia: Elige al mejor candidato
                if self._calcular_peso(caso) < self._calcular_peso(caso_existente):
                    self.casos_optimizados[firma_unica] = caso

        resultados_finales = []
        conteo_por_regla = {}
        
        for firma, caso_ganador in self.casos_optimizados.items():
            id_val_base = firma.split("|")[0]
            conteo_por_regla[id_val_base] = conteo_por_regla.get(id_val_base, 0) + 1
            
            caso_final = caso_ganador.copy()
            caso_final["id_validacion"] = f"{id_val_base}.{conteo_por_regla[id_val_base]}"
            resultados_finales.append(caso_final)

        # <--- NUEVO: Ordena usando la memoria original y luego por número de caso
        resultados_finales.sort(key=lambda x: (
            self.orden_reglas.index(x["id_validacion"].rsplit(".", 1)[0]),
            int(x["id_validacion"].rsplit(".", 1)[1])
        ))
        
        return resultados_finales

    def _calcular_peso(self, caso: dict) -> float:
        inputs = caso.get("inputs", {})
        variables_activas = sum(1 for v in inputs.values() if isinstance(v, (int, float)) and v != 0)
        suma_absoluta = sum(abs(v) for v in inputs.values() if isinstance(v, (int, float)))
        return (variables_activas * 1_000_000_000) + suma_absoluta