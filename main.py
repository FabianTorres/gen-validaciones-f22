import os
import json
from src.normalizador.formatter import normalizar_y_validar
from src.generador.test_builder import TestMatrixBuilder

def procesar_lote_formulas(ruta_input, ruta_output, ruta_arbol, ruta_json_qa):
    print("--- INICIANDO PIPELINE COMPLETO (FASE 1 + FASE 2) ---")
    
    if not os.path.exists(ruta_input):
        print(f"❌ Error: No se encontro el archivo {ruta_input}")
        return

    # Leer las lineas
    with open(ruta_input, 'r', encoding='utf-8') as file:
        lineas_crudas = file.readlines()

    # --- LOGICA: Agrupador Multilinea ---
    validaciones = []
    buffer_val = ""
    
    for linea in lineas_crudas:
        linea_limpia = linea.strip()
        if not linea_limpia: 
            continue
            
        if "|" in linea_limpia:
            if buffer_val:
                validaciones.append(buffer_val)
            buffer_val = linea_limpia
        else:
            buffer_val += " " + linea_limpia
            
    if buffer_val:
        validaciones.append(buffer_val)

    resultados_exitosos = []
    arboles_exitosos = []
    matrices_qa_globales = []  
    
    print(f"Se lograron agrupar {len(validaciones)} validaciones completas.\n")

    builder_z3 = TestMatrixBuilder()

    for index, linea in enumerate(validaciones, 1):
        try:
            id_val, formula_cruda = linea.split("|", 1)
            id_val = id_val.strip()
            formula_cruda = formula_cruda.strip()
            
            # Salto de línea inicial para cada ID
            print(f"Procesando: {id_val}")
            
            # --- FASE 1: NORMALIZADOR ---
            respuesta = normalizar_y_validar(formula_cruda, id_val)
            
            if respuesta["estado"] == "EXITO":
                print("Fase 1: OK")
                
                bloque_resultado = f"Validacion: {id_val} [ESTADO: OK]\n{'-'*40}\n{respuesta['texto_formateado']}\n{'='*40}\n"
                resultados_exitosos.append(bloque_resultado)
                
                bloque_arbol = f"Validacion: {id_val}\n{'-'*40}\n{respuesta['arbol'].pretty()}\n{'='*40}\n"
                arboles_exitosos.append(bloque_arbol)
                
                # --- FASE 2: GENERADOR Z3 ---
                try:
                    matriz_resultados = builder_z3.generar_matriz_pruebas(respuesta['arbol'], id_val)
                    matrices_qa_globales.extend(matriz_resultados)
                    print("Fase 2: OK\n")
                except Exception as e:
                    print(f"Fase 2: NK ... Error en ({e})\n")
                    matrices_qa_globales.append({
                        "id_validacion": id_val,
                        "error": "Error interno en motor matemático Z3",
                        "detalle": str(e)
                    })
                
            else:
                print(f"Fase 1: NK ... Error en ({respuesta['tipo_error']})\n")
                bloque_error = f"Validacion: {id_val} [ESTADO: RECHAZADA]\n{'-'*40}\n{respuesta['mensaje']}\n{'='*40}\n"
                resultados_exitosos.append(bloque_error)
                
        except Exception as e:
            print(f"\n⚠️ ERROR CRÍTICO procesando '{linea[:20]}...'")
            print(f"Detalle: {e}\n")

    # 1. Generar archivo de salida del Frontend
    with open(ruta_output, 'w', encoding='utf-8') as file_out:
        file_out.write("=== RESULTADOS NORMALIZADOS (VISTA FRONTEND) ===\n\n")
        for res in resultados_exitosos:
            file_out.write(res)

    # 2. Generar archivo de salida de los Árboles (AST)
    with open(ruta_arbol, 'w', encoding='utf-8') as file_arbol:
        file_arbol.write("=== ÁRBOLES DE SINTAXIS ABSTRACTA (AST) - DEPURACIÓN ===\n\n")
        for arbol in arboles_exitosos:
            file_arbol.write(arbol)

    # 3. Generar archivo JSON con las matrices para QA
    os.makedirs(os.path.dirname(ruta_json_qa), exist_ok=True)
    with open(ruta_json_qa, 'w', encoding='utf-8') as f:
        json.dump(matrices_qa_globales, f, indent=4, ensure_ascii=False)

    print("--- RESUMEN DEL PROCESAMIENTO ---")
    print(f"Total procesadas: {len(validaciones)}")
    print(f"Exitosas (Fase 1 completada): {len(arboles_exitosos)}")
    print(f"Rechazadas por Reglas de Negocio: {len(validaciones) - len(arboles_exitosos)}\n")

if __name__ == "__main__":
    archivo_entrada = "data/input_excel.txt"
    archivo_salida = "data/output_frontend.txt"
    archivo_arbol = "data/output_arbol.txt"  
    archivo_json_qa = "data/output_matrices_qa.json"
    
    procesar_lote_formulas(archivo_entrada, archivo_salida, archivo_arbol, archivo_json_qa)