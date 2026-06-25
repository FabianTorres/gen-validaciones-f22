import os
from src.normalizador.formatter import normalizar_y_validar

def procesar_lote_formulas(ruta_input, ruta_output, ruta_arbol):
    print("--- INICIANDO PRUEBAS FASE 1 (NORMALIZADOR) ---")
    
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
    arboles_exitosos = []  # NUEVO: Lista para guardar los AST
    print(f"Se lograron agrupar {len(validaciones)} validaciones completas.\n")

    for index, linea in enumerate(validaciones, 1):
        try:
            id_val, formula_cruda = linea.split("|", 1)
            id_val = id_val.strip()
            formula_cruda = formula_cruda.strip()
            
            print(f"Procesando Validacion: {id_val}")
            
            # Llamada "API" a nuestro núcleo
            respuesta = normalizar_y_validar(formula_cruda, id_val)
            
            if respuesta["estado"] == "EXITO":
                print("✅ Validacion OK.")
                
                # Cuadro de texto de la web con éxito
                bloque_resultado = f"Validacion: {id_val} [ESTADO: OK]\n{'-'*40}\n{respuesta['texto_formateado']}\n{'='*40}\n"
                resultados_exitosos.append(bloque_resultado)
                
                # --- VISUALIZADOR DEL ÁRBOL (AST) ---
                # Guardamos el árbol generado para el archivo de depuración
                bloque_arbol = f"Validacion: {id_val}\n{'-'*40}\n{respuesta['arbol'].pretty()}\n{'='*40}\n"
                arboles_exitosos.append(bloque_arbol)
                
            else:
                print(f"⚠️ Error detectado: {respuesta['tipo_error']}")
                # Cuadro de texto de la web mostrando el error explícito
                bloque_error = f"Validacion: {id_val} [ESTADO: RECHAZADA]\n{'-'*40}\n{respuesta['mensaje']}\n{'='*40}\n"
                resultados_exitosos.append(bloque_error)
                
        except Exception as e:
            print(f"⚠️ ERROR CRÍTICO procesando '{linea[:20]}...'")
            print(f"Detalle: {e}")

    # Generar archivo de salida del Frontend
    with open(ruta_output, 'w', encoding='utf-8') as file_out:
        file_out.write("=== RESULTADOS NORMALIZADOS (VISTA FRONTEND) ===\n\n")
        for res in resultados_exitosos:
            file_out.write(res)

    # NUEVO: Generar archivo de salida de los Árboles (AST)
    with open(ruta_arbol, 'w', encoding='utf-8') as file_arbol:
        file_arbol.write("=== ÁRBOLES DE SINTAXIS ABSTRACTA (AST) - DEPURACIÓN ===\n\n")
        for arbol in arboles_exitosos:
            file_arbol.write(arbol)

    print("--- RESUMEN DEL PROCESAMIENTO ---")
    print(f"Total procesadas: {len(validaciones)}")
    print(f"Exitosas (guardadas en output): {len(arboles_exitosos)}")
    print(f"Rechazadas: {len(validaciones) - len(arboles_exitosos)}")

if __name__ == "__main__":
    archivo_entrada = "data/input_excel.txt"
    archivo_salida = "data/output_frontend.txt"
    archivo_arbol = "data/output_arbol.txt"  # Nueva ruta para el AST
    procesar_lote_formulas(archivo_entrada, archivo_salida, archivo_arbol)