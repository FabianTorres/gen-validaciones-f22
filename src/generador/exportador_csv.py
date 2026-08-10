import io

class ExportadorCSV:
    def __init__(self, cache_mensajes: dict):
        """
        Recibe el catálogo de mensajes directamente desde la memoria RAM (FastAPI).
        Eliminamos las rutas de disco duro.
        """
        self.mensajes = cache_mensajes

    def generar_csv(self, casos: list) -> str:
        """
        Toma la lista de casos optimizados (Fase 3) y retorna un String 
        con formato CSV listo para descargarse.
        """
        # io.StringIO() actúa exactamente como un archivo .txt, pero vive en la RAM
        buffer_salida = io.StringIO()

        for caso in casos:
            if "error" in caso:
                continue 
                
            id_val = caso.get("id_validacion", "ID_DESC")
            base_id = id_val.rsplit('.', 1)[0].lower() 
            
            # 1. Fila de Identidad
            buffer_salida.write(f"{id_val};RUT;{caso.get('rut', '')}\n")
            
            # 2. Filas de Llenado de Celdas
            inputs = caso.get("inputs", {})
            for key, value in inputs.items():
                if key.startswith('[') and key.endswith(']'):
                    key_fmt = key.replace('[', 'C').replace(']', '')
                else:
                    key_fmt = key
                buffer_salida.write(f"{id_val};{key_fmt};{value}\n")
            
            # 3. Fila de Aserción (Resultado Esperado)
            resultado = caso.get("resultado_esperado")
            
            if resultado == "MENSAJE":
                mensaje_texto = self.mensajes.get(base_id, "MENSAJE_NO_ENCONTRADO")
                buffer_salida.write(f"{id_val};MENSAJE;{mensaje_texto}\n")
                
            elif resultado == "BUENO":
                buffer_salida.write(f"{id_val};BUENO;\n")
                
            elif resultado == "VERIFICAR_AUTOCALCULO":
                obj = caso.get("objetivo", {})
                cod_crudo = obj.get("codigo", "")
                cod_fmt = cod_crudo.replace('[', 'C').replace(']', '') if cod_crudo else "ERROR_COD"
                val_obj = obj.get("valor", 0)
                buffer_salida.write(f"{id_val};AUTO;{cod_fmt}={val_obj}\n")

        # Extraemos el texto gigante del buffer virtual
        return buffer_salida.getvalue()