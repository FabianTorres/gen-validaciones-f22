import json
import logging
import os
import sys
import datetime

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

        # Ejecutar deduplicación real
        casos_optimizados, estadisticas = self.reductor.procesar_casos(casos_generados)
        
        total_final = len(casos_optimizados)
        reduccion_porcentaje = ((total_inicial - total_final) / total_inicial) * 100 if total_inicial > 0 else 0

        # Exportar JSON optimizado
        with open(self.ruta_matrices_out, 'w', encoding='utf-8') as f:
            json.dump(casos_optimizados, f, indent=4, ensure_ascii=False)

        # --- GENERACIÓN DEL HISTORIAL ACUMULATIVO ---
        ruta_log = os.path.join(os.path.dirname(self.ruta_matrices_out), "historial_optimizacion.txt")
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        with open(ruta_log, "a", encoding="utf-8") as f:
            f.write(f"\n[{timestamp}] EJECUCIÓN DE FASE 3\n")
            f.write("-" * 55 + "\n")
            f.write(f"{'VALIDACIÓN':<15} | {'ORIGINALES':<12} | {'OPTIMIZADOS':<12} | {'REDUCCIÓN':<10}\n")
            f.write("-" * 55 + "\n")
            
            for regla, data in estadisticas.items():
                orig = data['originales']
                opt = data['optimizados']
                red = ((orig - opt) / orig * 100) if orig > 0 else 0
                f.write(f"{regla:<15} | {orig:<12} | {opt:<12} | {red:>8.2f}%\n")
                
            f.write("-" * 55 + "\n")
            f.write(f"{'TOTAL GLOBAL':<15} | {total_inicial:<12} | {total_final:<12} | {reduccion_porcentaje:>8.2f}%\n")
            f.write("=" * 55 + "\n")

        logging.info(f"Optimización completada. Casos finales conservados: {total_final}")
        logging.info(f"Redundancia eliminada: {reduccion_porcentaje:.2f}%")
        logging.info(f"Registro histórico guardado en: {ruta_log}")

# ==========================================
if __name__ == "__main__":
    ruta_base = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    in_file = os.path.join(ruta_base, "data", "output_matrices_qa.json")
    out_file = os.path.join(ruta_base, "data", "output_matrices_qa_optimizado.json")
    
    orquestador = OrquestadorFase3(in_file, out_file)
    orquestador.ejecutar()