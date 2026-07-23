import json
import sys
import os

# Inyección de ruta para evitar ModuleNotFoundError
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

# Importación correcta de la función que expone tu parser
from src.normalizador.parser import obtener_parser 
from src.optimizador.trazador import TrazadorLogico
from src.optimizador.reductor import ReductorSetCover

class OptimizadorOrquestador:
    def __init__(self, ruta_json="data/output_matrices_qa.json", ruta_excel="data/input_excel.txt"):
        self.ruta_json = ruta_json
        self.ruta_excel = ruta_excel
        self.ruta_salida = ruta_json.replace(".json", "_optimizado.json")
        
        # Instanciamos el parser puro de Lark
        self.parser = obtener_parser()
        self.trazador = TrazadorLogico()
        self.reductor = ReductorSetCover()

    def ejecutar(self):
        if not os.path.exists(self.ruta_json):
            print(f"⚠️ Sin entrada JSON en {self.ruta_json}")
            return

        print("🔍 Fase 3: Leyendo matriz de casos generados...")
        with open(self.ruta_json, 'r', encoding='utf-8') as f:
            casos = json.load(f)

        print("🌳 Fase 3: Reconstruyendo Árboles AST en memoria...")
        mapa_ast = {}
        with open(self.ruta_excel, 'r', encoding='utf-8') as f:
            for linea in f:
                linea = linea.strip()
                if not linea: continue
                
                # Detectamos separadores comunes en archivos txt (Tab o Pipe)
                if '\t' in linea:
                    id_val, regla_txt = linea.split('\t', 1)
                elif '|' in linea:
                    id_val, regla_txt = linea.split('|', 1)
                else:
                    # Asume que el primer espacio separa el ID de la regla
                    partes = linea.split(" ", 1)
                    if len(partes) == 2:
                        id_val, regla_txt = partes
                    else:
                        continue
                        
                try:
                    mapa_ast[id_val.strip()] = self.parser.parse(regla_txt.strip())
                except Exception as e:
                    pass # Silenciamos errores de reglas inválidas para no ensuciar la consola

        grupos_validacion = {}
        for caso in casos:
            id_base = ".".join(caso["id_validacion"].split(".")[:-1])
            if not id_base: id_base = caso["id_validacion"]
            if id_base not in grupos_validacion: grupos_validacion[id_base] = []
            grupos_validacion[id_base].append(caso)

        casos_totales_optimizados = []

        print("⚙️ Fase 3: Simulando rutas y aplicando Set Cover...")
        for id_base, lista_casos in grupos_validacion.items():
            ast_tree = mapa_ast.get(id_base)
            
            # Paso 1: Trazar la huella real de cada caso
            if ast_tree:
                for caso in lista_casos:
                    if "inputs" in caso:
                        caso["huella_real"] = self.trazador.obtener_huella(ast_tree, caso["inputs"])
                    else:
                        caso["huella_real"] = ("ERROR_NO_INPUTS",)
            else:
                # Fallback de emergencia si la regla no estaba en el txt
                for caso in lista_casos:
                    caso["huella_real"] = (caso.get("tipo_escenario", "SIN_AST"),)
            
            # Paso 2: Reducir duplicados lógicos
            optimizados = self.reductor.optimizar(lista_casos)
            casos_totales_optimizados.extend(optimizados)

        with open(self.ruta_salida, 'w', encoding='utf-8') as f:
            json.dump(casos_totales_optimizados, f, indent=4, ensure_ascii=False)

        ahorro = len(casos) - len(casos_totales_optimizados)
        porcentaje = (ahorro / len(casos) * 100) if len(casos) > 0 else 0
        
        print("\n" + "="*50)
        print("🚀 REPORTE DE OPTIMIZACIÓN ESTRUCTURAL (FASE 3) 🚀")
        print("="*50)
        print(f"📊 Casos entrantes (Fase 2): {len(casos)}")
        print(f"🎯 Casos efectivos (Fase 3): {len(casos_totales_optimizados)}")
        print(f"🗑️ Casos redundantes eliminados: {ahorro} ({porcentaje:.1f}%)")
        print(f"💾 Guardado en: {self.ruta_salida}")
        print("="*50 + "\n")

if __name__ == "__main__":
    app = OptimizadorOrquestador()
    app.ejecutar()