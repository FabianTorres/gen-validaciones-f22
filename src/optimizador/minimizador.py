import json
import os

class OptimizadorMatriz:
    def __init__(self, ruta_entrada="data/output_matrices_qa.json", ruta_salida="data/output_matrices_qa_optimizado.json"):
        self.ruta_entrada = ruta_entrada
        self.ruta_salida = ruta_salida

    def ejecutar(self):
        if not os.path.exists(self.ruta_entrada):
            print(f"⚠️ Error: No se encontró el archivo de entrada en {self.ruta_entrada}")
            return

        with open(self.ruta_entrada, 'r', encoding='utf-8') as f:
            casos = json.load(f)

        casos_optimizados = []
        
        # 1. Agrupamos los casos por Validación Base
        grupos_validacion = {}
        for caso in casos:
            id_base = ".".join(caso["id_validacion"].split(".")[:-1])
            if not id_base: id_base = caso["id_validacion"]
            if id_base not in grupos_validacion: grupos_validacion[id_base] = []
            grupos_validacion[id_base].append(caso)

        # 2. ALGORITMO ESTRUCTURAL DE DOBLE FILTRO
        for id_base, lista_casos in grupos_validacion.items():
            # Filtro 1: Unicidad de Ruta Lógica (Garantiza 1 caso por Huella AST)
            casos_unicos_logicos = {}
            for caso in lista_casos:
                if caso.get("estado_interno") == "INSATISFACTIBLE" or "error" in caso:
                    casos_optimizados.append(caso)
                    continue

                huella = caso.get("huella_estructural", caso.get("tipo_escenario", "DESCONOCIDO"))
                huella_str = json.dumps(huella, sort_keys=True) if isinstance(huella, dict) else str(huella)
                
                rut = caso.get("rut", "")
                resultado = caso.get("resultado_esperado", "")
                objetivo_cod = caso.get("objetivo", {}).get("codigo", "")
                objetivo_val = caso.get("objetivo", {}).get("valor", "")

                # Firma Lógica: "Estoy probando ESTE nodo, con ESTE contribuyente y ESTE resultado"
                firma_logica = (huella_str, rut, resultado, objetivo_cod, objetivo_val)
                
                if firma_logica not in casos_unicos_logicos:
                    casos_unicos_logicos[firma_logica] = caso.copy()

            # Filtro 2: Unicidad de Ejecución Física (Si 2 rutas usan exactos mismos inputs, se fusionan)
            firmas_ejecucion = {}
            idx_real = 1
            
            for caso in casos_unicos_logicos.values():
                # Firma Física Estricta: LLAVES y VALORES exactos. No más "valores simétricos".
                inputs_estrictos = tuple(sorted(caso.get("inputs", {}).items()))
                rut = caso.get("rut", "")
                resultado = caso.get("resultado_esperado", "")
                objetivo_cod = caso.get("objetivo", {}).get("codigo", "")
                objetivo_val = caso.get("objetivo", {}).get("valor", "")

                firma_fisica = (inputs_estrictos, rut, resultado, objetivo_cod, objetivo_val)

                if firma_fisica not in firmas_ejecucion:
                    caso_limpio = caso.copy()
                    caso_limpio["id_validacion"] = f"{id_base}.{idx_real}"
                    
                    # Convertimos la huella en lista para poder fusionar si es necesario
                    if "huella_estructural" in caso_limpio:
                        caso_limpio["huellas_cubiertas"] = [caso_limpio.pop("huella_estructural")]
                        
                    firmas_ejecucion[firma_fisica] = caso_limpio
                    idx_real += 1
                else:
                    # ¡Bingo! Dos nodos distintos resultaron en la misma ejecución exacta. Fusionamos cobertura.
                    caso_existente = firmas_ejecucion[firma_fisica]
                    caso_existente["tipo_escenario"] += f" | {caso['tipo_escenario']}"
                    
                    if "huella_estructural" in caso:
                        caso_existente["huellas_cubiertas"].append(caso["huella_estructural"])
                    
                    if caso['descripcion_qa'] not in caso_existente['descripcion_qa']:
                        caso_existente["descripcion_qa"] += f" || {caso['descripcion_qa']}"

            casos_optimizados.extend(firmas_ejecucion.values())

        # 3. Exportar el JSON optimizado
        with open(self.ruta_salida, 'w', encoding='utf-8') as f:
            json.dump(casos_optimizados, f, indent=4, ensure_ascii=False)

        ahorro = len(casos) - len(casos_optimizados)
        porcentaje = (ahorro / len(casos) * 100) if len(casos) > 0 else 0
        print("\n" + "="*50)
        print("🚀 REPORTE DE OPTIMIZACIÓN ESTRUCTURAL (FASE 3) 🚀")
        print("="*50)
        print(f"📊 Casos generados (Fase 2): {len(casos)}")
        print(f"🎯 Casos efectivos tras filtro MCDC: {len(casos_optimizados)}")
        if ahorro > 0:
            print(f"🗑️  Ahorro por colisión/ejecución idéntica: {ahorro} casos ({porcentaje:.1f}%)")
        else:
            print(f"✅ Motor perfecto: 0% de redundancia física. Cada caso es estructuralmente único.")
        print(f"💾 Archivo guardado en: {self.ruta_salida}")
        print("="*50 + "\n")

if __name__ == "__main__":
    optimizador = OptimizadorMatriz()
    optimizador.ejecutar()