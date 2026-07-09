import json
import os
from src.normalizador.formatter import normalizar_y_validar
from src.generador.test_builder import TestMatrixBuilder

RUTA_OUTPUT = "data/output_matrices_qa.json"

def probar_generacion_z3(id_val, formula_cruda, builder, resultados_globales):
    print(f"Procesando: {id_val} ... ", end="")
    
    # 1. FASE 1: Obtener el AST (El motor NUNCA lee el texto crudo)
    respuesta_fase1 = normalizar_y_validar(formula_cruda, id_val)
    
    if respuesta_fase1["estado"] != "EXITO":
        print("❌ Error en Normalizador")
        return
        
    arbol_ast = respuesta_fase1["arbol"]
    
    # 2. FASE 2: Pasamos el ÁRBOL al Director Z3
    try:
        matriz_resultados = builder.generar_matriz_pruebas(arbol_ast, id_val)
        resultados_globales.extend(matriz_resultados)
        print("✅ Matriz Generada")
    except Exception as e:
        print(f"⚠️ Error Z3: {e}")

if __name__ == "__main__":
    print(f"\n--- INICIANDO BATERIA DE PRUEBAS Z3 ---")
    
    # Director principal
    builder = TestMatrixBuilder()
    resultados_globales = []
    
    # BATERIA DE FÓRMULAS
    probar_generacion_z3("a.190", "[1793] = [1789] + [1790] + [1791] + [1792]", builder, resultados_globales)
    probar_generacion_z3("c.80", "[1031] + [1635] <= ([1032] * P84) + P736", builder, resultados_globales)
    probar_generacion_z3("d.150", "([893] + [894]) > 0 => Si Atributo = M14A; entonces [844] > 0 Sino 0", builder, resultados_globales)
    
    # EXPORTACIÓN
    os.makedirs(os.path.dirname(RUTA_OUTPUT), exist_ok=True)
    with open(RUTA_OUTPUT, 'w', encoding='utf-8') as f:
        json.dump(resultados_globales, f, indent=4, ensure_ascii=False)
        
    print(f"\n🚀 Pruebas finalizadas. Revisa el archivo: {RUTA_OUTPUT}\n")