import os
from src.normalizador.formatter import normalizar_y_validar

def procesar_lote_formulas(ruta_input, ruta_output):
    print("--- INICIANDO PRUEBAS FASE 1 (NORMALIZADOR) ---")
    
    if not os.path.exists(ruta_input):
        print(f"❌ Error: No se encontro el archivo {ruta_input}")
        return

    # Leer las lineas
    with open(ruta_input, 'r', encoding='utf-8') as file:
        lineas_crudas = file.readlines()

    # --- NUEVA LOGICA: Agrupador Multilinea ---
    validaciones = []
    buffer_val = ""
    
    for linea in lineas_crudas:
        linea_limpia = linea.strip()
        if not linea_limpia: 
            continue
            
        if "|" in linea_limpia:
            # Si hay un pipe, guardamos la validacion anterior y empezamos una nueva
            if buffer_val:
                validaciones.append(buffer_val)
            buffer_val = linea_limpia
        else:
            # Si no hay pipe, es un salto de linea de la misma formula (ej: "Sino 0")
            buffer_val += " " + linea_limpia
            
    # Guardar la ultima validacion en memoria
    if buffer_val:
        validaciones.append(buffer_val)

    resultados_exitosos = []
    print(f"Se lograron agrupar {len(validaciones)} validaciones completas.\n")

    for index, linea in enumerate(validaciones, 1):
        try:
            id_val, formula_cruda = linea.split("|", 1)
            id_val = id_val.strip()
            formula_cruda = formula_cruda.strip()
            
            print(f"Procesando Validacion: {id_val}")
            exito, resultado = normalizar_y_validar(formula_cruda)
            
            if exito:
                print("✅ OK")
                # Guardamos como un bloque de texto ordenado
                bloque_resultado = f"Validacion: {id_val}\n{'-'*40}\n{resultado}\n{'='*40}\n"
                resultados_exitosos.append(bloque_resultado)
            else:
                print(f"\n{resultado}\n")
                print(f"⚠️ ADVERTENCIA: La validacion {id_val} fue descartada.\n")
                
        except ValueError:
            print(f"⚠️ ADVERTENCIA: Error de formato en la entrada '{linea[:20]}...'")

    # Generar el archivo de salida
    with open(ruta_output, 'w', encoding='utf-8') as file_out:
        file_out.write("=== RESULTADOS NORMALIZADOS (VISTA FRONTEND) ===\n\n")
        for res in resultados_exitosos:
            file_out.write(res)

    print("\n--- RESUMEN DEL PROCESAMIENTO ---")
    print(f"Total procesadas: {len(validaciones)}")
    print(f"Exitosas (guardadas en output): {len(resultados_exitosos)}")

if __name__ == "__main__":
    archivo_entrada = "data/input_excel.txt"
    archivo_salida = "data/output_frontend.txt"
    procesar_lote_formulas(archivo_entrada, archivo_salida)