import os
from src.normalizador.formatter import normalizar_y_validar
from src.generador.solver import GeneradorCasos

def procesar_lote_formulas(ruta_input, ruta_output):
    print("--- INICIANDO PRUEBAS FASE 1 (NORMALIZADOR) Y FASE 2 (GENERADOR Z3) ---")
    
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

    # --- NUEVO: Instanciamos el Motor Matemático (Fase 2) ---
    generador_z3 = GeneradorCasos()

    for index, linea in enumerate(validaciones, 1):
        try:
            id_val, formula_cruda = linea.split("|", 1)
            id_val = id_val.strip()
            formula_cruda = formula_cruda.strip()
            
            print(f"Procesando Validacion: {id_val}")
            
            # --- FASE 1: Normalización y Parseo ---
            resultado_parseo = normalizar_y_validar(formula_cruda)
            
            # Desempaquetado seguro (soporta si formatter.py devuelve 2 o 3 valores)
            if len(resultado_parseo) == 3:
                exito, texto_resultado, arbol_ast = resultado_parseo
            else:
                exito, texto_resultado = resultado_parseo
                arbol_ast = None
            
            if exito:
                print("✅ Parseo exitoso (Fase 1).")
                
                # Guardamos como un bloque de texto ordenado para el frontend
                bloque_resultado = f"Validacion: {id_val}\n{'-'*40}\n{texto_resultado}\n{'='*40}\n"
                resultados_exitosos.append(bloque_resultado)
                
                # --- FASE 2: Generación Matemática con Z3 ---
                if arbol_ast is not None:
                    print("⚙️  Inyectando Árbol de Sintaxis a Z3 (Fase 2)...")
                    resultado_fase2 = generador_z3.generar_caso_positivo(arbol_ast)
                    
                    print("--- RESULTADO CASO POSITIVO BASE ---")
                    print(f"Estado: {resultado_fase2['Estado']}")
                    if resultado_fase2['Estado'] == 'EXITO':
                        for var, val in resultado_fase2['Datos'].items():
                            print(f"  {var}: {val}")
                    else:
                        print(f"  Detalle: {resultado_fase2['Detalle']}")
                    print("------------------------------------\n")
                else:
                    print("⚠️ Fase 2 omitida: normalizar_y_validar no está retornando el arbol_ast.\n")
                    
            else:
                print(f"\n{texto_resultado}\n")
                print(f"⚠️ ADVERTENCIA: La validacion {id_val} fue descartada.\n")
                
        except Exception as e:
            print(f"⚠️ ERROR CRÍTICO procesando '{linea[:20]}...'")
            print(f"Detalle del error: {e}")
            import traceback
            traceback.print_exc()  # Esto nos escupirá el clásico texto rojo con la línea exacta

    # Generar el archivo de salida
    with open(ruta_output, 'w', encoding='utf-8') as file_out:
        file_out.write("=== RESULTADOS NORMALIZADOS (VISTA FRONTEND) ===\n\n")
        for res in resultados_exitosos:
            file_out.write(res)

    print("--- RESUMEN DEL PROCESAMIENTO ---")
    print(f"Total procesadas: {len(validaciones)}")
    print(f"Exitosas (guardadas en output): {len(resultados_exitosos)}")

if __name__ == "__main__":
    archivo_entrada = "data/input_excel.txt"
    archivo_salida = "data/output_frontend.txt"
    procesar_lote_formulas(archivo_entrada, archivo_salida)