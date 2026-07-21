import json
import os

class ExportadorCSV:
    def __init__(self, ruta_json="data/output_matrices_qa.json", ruta_mensajes="data/catalogo_mensajes.txt", ruta_salida="data/casos_selenium.csv"):
        self.ruta_json = ruta_json
        self.ruta_mensajes = ruta_mensajes
        self.ruta_salida = ruta_salida
        self.mensajes = self._cargar_mensajes()

    def _cargar_mensajes(self):
        """Carga el diccionario de glosas de error en memoria."""
        mensajes = {}
        if os.path.exists(self.ruta_mensajes):
            with open(self.ruta_mensajes, 'r', encoding='utf-8') as f:
                for linea in f:
                    linea = linea.strip()
                    if not linea or linea.startswith("ID_VALIDACION"):
                        continue
                    if '|' in linea:
                        partes = linea.split('|', 1)
                        # Guardamos el ID base (ej. 'c.7') en minúsculas para el cruce
                        mensajes[partes[0].strip().lower()] = partes[1].strip()
        return mensajes

    def generar_csv(self):
        """Lee el JSON, aplana los datos y escribe el formato para el Bot."""
        if not os.path.exists(self.ruta_json):
            print("⚠️ No hay JSON generado para exportar.")
            return

        with open(self.ruta_json, 'r', encoding='utf-8') as f:
            casos = json.load(f)

        lineas_csv = []
        for caso in casos:
            if "error" in caso:
                continue # Ignoramos los casos que no se pudieron generar
                
            id_val = caso.get("id_validacion", "ID_DESC")
            # Extraemos el ID base (ej: 'c.7' a partir de 'c.7.1')
            base_id = id_val.rsplit('.', 1)[0].lower() 
            
            # 1. Fila de Identidad
            lineas_csv.append(f"{id_val};RUT;{caso.get('rut', '')}")
            
            # 2. Filas de Llenado de Celdas
            inputs = caso.get("inputs", {})
            for key, value in inputs.items():
                # Limpiamos el formato interno [822] -> C822
                if key.startswith('[') and key.endswith(']'):
                    key_fmt = key.replace('[', 'C').replace(']', '')
                else:
                    key_fmt = key
                    
                lineas_csv.append(f"{id_val};{key_fmt};{value}")
            
            # 3. Fila de Aserción (Resultado Esperado)
            resultado = caso.get("resultado_esperado")
            
            if resultado == "MENSAJE":
                mensaje_texto = self.mensajes.get(base_id, "MENSAJE_NO_ENCONTRADO")
                lineas_csv.append(f"{id_val};MENSAJE;{mensaje_texto}")
                
            elif resultado == "BUENO":
                lineas_csv.append(f"{id_val};BUENO;")
                
            elif resultado == "VERIFICAR_AUTOCALCULO":
                # --- EXTRACCIÓN DEL OBJETIVO PARA REGLAS A y B ---
                obj = caso.get("objetivo", {})
                cod_crudo = obj.get("codigo", "")
                
                # Transformamos [1926] en C1926
                cod_fmt = cod_crudo.replace('[', 'C').replace(']', '') if cod_crudo else "ERROR_COD"
                val_obj = obj.get("valor", 0)
                
                lineas_csv.append(f"{id_val};AUTO;{cod_fmt}={val_obj}")

        # Guardar archivo
        with open(self.ruta_salida, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lineas_csv))
        
        print(f"✅ CSV para el Bot de Selenium generado exitosamente en: {self.ruta_salida}")