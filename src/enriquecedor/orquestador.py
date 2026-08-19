from typing import List

class OrquestadorEnriquecimiento:
    def __init__(self, cache_codigos: dict):
        """
        Constructor simplificado gracias a la arquitectura Shift-Left.
        Solo necesitamos el catálogo de códigos. Se ha eliminado todo el 
        código muerto (cache_asts y config_motor) tras la actualización del Backend.
        """
        self.cache_codigos = cache_codigos

    def procesar_matriz(self, casos: List[dict]) -> List[dict]:
        """
        Actúa como un Sanitizador para Selenium (RPA).
        Toma los casos matemáticamente perfectos de la Fase 2, separa los códigos autocalculados 
        de los editables, y formatea el JSON cumpliendo con el esquema DetalleInputs.
        """
        casos_formateados = []
        
        for caso in casos:
            # 1. Leemos desde la bóveda intocable generada en main_api
            inputs_origen = caso.get("inputs_matematicos")
            
            # Fallback de seguridad por si el caso viene corrupto o vacío
            if not inputs_origen or caso.get("error"):
                casos_formateados.append(caso)
                continue

            # 2. Inicialización de las cajas para la UI
            editables = {}
            autocalculados = {}

            # 3. Clasificación Meticulosa
            for clave_corchetes, valor in inputs_origen.items():
                codigo_limpio = clave_corchetes.replace('[', '').replace(']', '').strip()
                info_codigo = self.cache_codigos.get(codigo_limpio, {})
                
                if info_codigo.get("autocalculado", False):
                    autocalculados[clave_corchetes] = valor
                else:
                    editables[clave_corchetes] = valor

            # 4. Construcción de la Capa Humana (Auditoría Pydantic)
            # Respetamos estrictamente el contrato con schemas.py
            caso["detalle_inputs"] = {
                "editables_originales": editables.copy(),
                "autocalculados_originales": autocalculados.copy(),
                "editables_inyectados": {} 
            }

            # 5. Construcción de la Capa Máquina (Para Selenium)
            # Sobreescribimos inputs solo con los códigos editables permitidos
            caso["inputs"] = editables.copy()

            # 6. Sello de Aprobación
            caso["estado_interno"] = "ENRIQUECIDO"
            casos_formateados.append(caso)

        return casos_formateados