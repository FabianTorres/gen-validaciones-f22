class ExtractorModelo:
    def __init__(self, cache_codigos: dict):
        """
        Inicializa el extractor con el catálogo de códigos en memoria RAM.
        Esto permite saber qué variables son autocalculadas y cuáles son "hojas" digitables.
        """
        self.cache_codigos = cache_codigos

    def procesar_modelo(self, modelo_z3) -> dict:
        """
        Toma el modelo resuelto por Z3, limpia variables temporales,
        filtra las autocalculadas y devuelve un diccionario puro con enteros.
        """
        inputs_enriquecidos = {}
        
        if not modelo_z3:
            return inputs_enriquecidos

        for declaracion in modelo_z3.decls():
            nombre_var = declaracion.name()
            
            # Limpieza de formato
            codigo_limpio = nombre_var.replace('[', '').replace(']', '').strip()
            
            # Filtrar variables temporales o lógicas (ej. IS_ATRIBUTO_M14A, Alfa, Beta)
            if not codigo_limpio.isdigit():
                continue
                
            # Filtrar códigos autocalculados 
            info_codigo = self.cache_codigos.get(codigo_limpio, {})
            if info_codigo.get("autocalculado", False):
                continue
                
            # Extracción y Casteo del valor a entero nativo de Python
            valor_z3 = modelo_z3[declaracion]
            
            try:
                if hasattr(valor_z3, 'as_long'):
                    valor_final = valor_z3.as_long()
                elif hasattr(valor_z3, 'as_fraction'):
                    valor_final = int(valor_z3.as_fraction())
                else:
                    valor_str = str(valor_z3)
                    valor_final = int(float(valor_str))
                    
                # FIX SPARSITY: Ignoramos los ceros absolutos, el F22 los asume si están vacíos.
                if valor_final == 0:
                    continue
                    
                clave_json = f"[{codigo_limpio}]"
                inputs_enriquecidos[clave_json] = valor_final
                
            except Exception:
                pass

        return inputs_enriquecidos