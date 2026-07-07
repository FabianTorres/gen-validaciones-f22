import json
from src.normalizador.formatter import normalizar_y_validar
from src.generador.solver import GeneradorCasos

def probar_generacion_z3(id_val, formula_cruda):
    print(f"\n{'='*50}")
    print(f"🚀 INYECTANDO A Z3: {id_val}")
    print(f"Original: {formula_cruda}")
    print(f"{'='*50}")
    
    # 1. FASE 1: Obtener el AST validado
    respuesta_fase1 = normalizar_y_validar(formula_cruda, id_val)
    
    if respuesta_fase1["estado"] != "EXITO":
        print(f"❌ La Fase 1 bloqueó la entrada:\n{respuesta_fase1['mensaje']}")
        return
        
    arbol_ast = respuesta_fase1["arbol"]
    
    # 2. FASE 2: Inyectar al motor matemático
    # Instanciamos un generador nuevo para limpiar la memoria de Z3 en cada prueba
    generador = GeneradorCasos() 
    
    try:
        resultado = generador.generar_caso_positivo(arbol_ast)
        print("\n✅ DATOS CALCULADOS POR Z3 (Happy Path):")
        print(json.dumps(resultado, indent=2, ensure_ascii=False))
    except Exception as e:
        print(f"\n⚠️ ERROR EN EL MOTOR Z3:")
        print(f"Detalle: {e}")

if __name__ == "__main__":
    # PRUEBA 1: Autocalculado simple (Z3 debe despejar la suma)
    probar_generacion_z3(
        "a.190", 
        "[1793] = [1789] + [1790] + [1791] + [1792]"
    )
    
    # PRUEBA 2: Cota Matemática con Parámetros
    probar_generacion_z3(
        "c.80", 
        "[1031] + [1635] <= ([1032] * P84) + P736"
    )
    
    # PRUEBA 3: La Prueba de Fuego (Inferencia de Tipos y Strings)
    # Aquí probaremos que el "Sino 0" no rompa la máquina y que soporte textos como "M14A"
    probar_generacion_z3(
        "d.150", 
        "([893] + [894]) > 0 => Si Atributo = M14A; entonces [844] > 0 Sino 0"
    )