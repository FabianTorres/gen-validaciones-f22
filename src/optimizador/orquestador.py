import json
import logging
import os
import sys

# Parche de ruta para ejecutar standalone
ruta_raiz = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if ruta_raiz not in sys.path:
    sys.path.insert(0, ruta_raiz)

from src.optimizador.reductor import ReductorCasos

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

class OrquestadorFase3:
    def __init__(self, ruta_matrices_in: str, ruta_matrices_out: str):
        self.ruta_matrices_in = ruta_matrices_in
        self.ruta_matrices_out = ruta_matrices_out
        self.reductor = ReductorCasos()

    def ejecutar(self):
        logging.info("Iniciando Fase 3: Deduplicación por Firma Lógica Estricta...")
        
        if not os.path.exists(self.ruta_matrices_in):
            logging.error(f"No se encontró el archivo de matrices: {self.ruta_matrices_in}")
            return

        with open(self.ruta_matrices_in, 'r', encoding='utf-8') as f:
            casos_generados = json.load(f)

        total_inicial = len(casos_generados)
        logging.info(f"Casos crudos recibidos (Fase 2): {total_inicial}")

        # Ejecutar deduplicación real
        casos_optimizados = self.reductor.procesar_casos(casos_generados)
        
        total_final = len(casos_optimizados)
        reduccion_porcentaje = ((total_inicial - total_final) / total_inicial) * 100 if total_inicial > 0 else 0

        with open(self.ruta_matrices_out, 'w', encoding='utf-8') as f:
            json.dump(casos_optimizados, f, indent=4, ensure_ascii=False)

        logging.info(f"Optimización completada. Casos finales conservados: {total_final}")
        logging.info(f"Redundancia eliminada (Clones lógicos estocásticos): {reduccion_porcentaje:.2f}%")
        logging.info(f"Archivo exportado a: {self.ruta_matrices_out}")

# ==========================================
if __name__ == "__main__":
    ruta_base = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    in_file = os.path.join(ruta_base, "data", "output_matrices_qa.json")
    out_file = os.path.join(ruta_base, "data", "output_matrices_qa_optimizado.json")
    
    orquestador = OrquestadorFase3(in_file, out_file)
    orquestador.ejecutar()