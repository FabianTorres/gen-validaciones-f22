from fastapi import FastAPI, HTTPException, Response, Query
from typing import List
from fastapi.concurrency import run_in_threadpool
from contextlib import asynccontextmanager
from fastapi.middleware.cors import CORSMiddleware
from lark import Tree, Token

# Importamos lógica de negocio y capa de datos
from src.generador.exportador_csv import ExportadorCSV
from src.db.cosmos_client import CatalogoCache, RepositorioHistorial
from src.normalizador.formatter import normalizar_y_validar
from src.generador.test_builder import TestMatrixBuilder
from src.optimizador.reductor import ReductorCasos

# Importamos todos los esquemas Pydantic
from src.api.schemas import (
    FormulaRequest, NormalizacionResponse, GeneracionResponse, 
    ParametroItem, CodigoItem, MensajeItem, RutItem,
    BatchParametros, BatchCodigos, BatchMensajes, BatchRuts,
    CasoQA, GuardarReglaRequest, GuardarReglaResponse, 
    BatchDependenciasRequest, CargarAstsRequest, HistorialItem, ReglaDetalleResponse
)

# ==========================================
# UTILIDADES CORE
# ==========================================

def serializar_ast(nodo):
    """
    Convierte recursivamente el árbol AST generado por Lark en un diccionario JSON-serializable.
    Esencial para persistir la estructura matemática en la base de datos sin perder jerarquía.
    """
    if isinstance(nodo, Token):
        return {"tipo": "token", "nombre": nodo.type, "valor": str(nodo)}
    elif isinstance(nodo, Tree):
        return {
            "tipo": "nodo", 
            "nombre": nodo.data, 
            "hijos": [serializar_ast(hijo) for hijo in nodo.children]
        }
    return str(nodo)


# ==========================================
# CICLO DE VIDA DE LA APLICACIÓN Y CONFIGURACIÓN
# ==========================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Se ejecuta una única vez al levantar el servidor.
    Hidrata la memoria RAM con los catálogos de Cosmos DB para garantizar latencia cero
    en las validaciones posteriores.
    """
    cache = CatalogoCache()
    await cache.cargar_desde_cosmos()
    yield
    # Aquí se podrían cerrar conexiones de base de datos o liberar recursos al apagar.

app = FastAPI(title="Motor Generador Validaciones F22", version="2.1.0", lifespan=lifespan)

# Instanciamos los Singletons de la capa de datos
cache = CatalogoCache()
repo_historial = RepositorioHistorial()

# Configuración de CORS para permitir solicitudes desde el Frontend local
#origenes_permitidos = ["http://localhost:5173", "http://127.0.0.1:5173"]
origenes_permitidos = ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origenes_permitidos,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ==========================================
# PIPELINE DE VALIDACIONES (FASE 1, 2 y 3)
# ==========================================

@app.post("/api/v1/normalizar", response_model=NormalizacionResponse)
async def endpoint_normalizar(req: FormulaRequest):
    """
    FASE 1: Análisis léxico y sintáctico de la fórmula.
    Verifica que la sintaxis sea correcta y normaliza el texto.
    """
    # Filtramos la memoria RAM para inyectar solo el contexto del Año Tributario solicitado
    codigos_at = cache.codigos.get(req.at, {})
    parametros_at = cache.parametros.get(req.at, {})

    # run_in_threadpool: Evita que el análisis pesado del parser bloquee las demás peticiones concurrentes de FastAPI
    resultado = await run_in_threadpool(
        normalizar_y_validar, 
        req.formula_cruda, 
        req.id_validacion, 
        codigos_at, 
        parametros_at
    )
    
    if resultado["estado"] == "ERROR":
        return NormalizacionResponse(estado="ERROR", tipo_error=resultado.get("tipo_error"), mensaje=resultado.get("mensaje"))
        
    return NormalizacionResponse(estado="EXITO", texto_formateado=resultado["texto_formateado"])


@app.post("/api/v1/generar-casos", response_model=GeneracionResponse)
async def endpoint_generar_casos(req: FormulaRequest):
    """
    PIPELINE COMPLETO: Ejecuta la validación, resuelve las ecuaciones mediante el SMT Solver (Z3),
    y optimiza el resultado usando el algoritmo Set Cover.
    """
    codigos_at = cache.codigos.get(req.at, {})
    parametros_at = cache.parametros.get(req.at, {})
    ruts_at = cache.ruts.get(req.at, [])

    # 1. Fase 1: Parseo
    res_norm = await run_in_threadpool(normalizar_y_validar, req.formula_cruda, req.id_validacion, codigos_at, parametros_at)
    if res_norm["estado"] == "ERROR":
        raise HTTPException(status_code=400, detail=res_norm["mensaje"])
        
    ast_tree = res_norm["arbol"]
    
    # Extraemos la configuración como diccionario
    config_dict = req.config_motor.model_dump() if req.config_motor else {}
    
    # 2. Fase 2: Z3 SMT Solver (Inyectamos config_dict aquí)
    builder = TestMatrixBuilder(parametros_at, ruts_at, codigos_at, config_dict)
    
    casos_brutos = await run_in_threadpool(builder.generar_matriz_pruebas, ast_tree, req.id_validacion)
    if not casos_brutos or "error" in casos_brutos[0]:
        raise HTTPException(status_code=400, detail=casos_brutos[0].get("error", "Error de contradicción lógica en SMT Solver"))
        
    # 3. Fase 3: Optimización
    reductor = ReductorCasos()
    casos_optimizados, estadisticas = await run_in_threadpool(reductor.procesar_casos, casos_brutos)
    
    # Cálculo de métricas
    stats_regla = estadisticas.get(req.id_validacion.split(".")[0], {"originales": len(casos_brutos), "optimizados": len(casos_optimizados)})
    reduccion = ((stats_regla["originales"] - stats_regla["optimizados"]) / stats_regla["originales"] * 100) if stats_regla["originales"] > 0 else 0.0

    # Ingeniería Inversa: Extraemos el código objetivo afectado desde el primer caso exitoso
    ast_diccionario = serializar_ast(ast_tree)
    codigo_obj_detectado = None
    for caso in casos_optimizados:
        if isinstance(caso, dict) and "objetivo" in caso and caso["objetivo"]:
            codigo_obj_detectado = caso["objetivo"].get("codigo")
            break

    return GeneracionResponse(
        estado="EXITO",
        id_validacion=req.id_validacion,
        mensaje="Matrices generadas y optimizadas correctamente",
        texto_formateado=res_norm["texto_formateado"],
        codigo_objetivo=codigo_obj_detectado,
        ast_json=ast_diccionario,
        total_casos_generados=stats_regla["originales"],
        total_casos_optimizados=stats_regla["optimizados"],
        porcentaje_reduccion=reduccion,
        casos_brutos=casos_brutos,
        casos=casos_optimizados
    )


# ==========================================
# LECTURA DE CATÁLOGOS
# ==========================================

@app.get("/api/v1/catalogos/{tipo}")
async def obtener_catalogo(tipo: str, at: int = Query(2026, description="Año Tributario (ej. 2026)")):
    """
    Sirve los catálogos base directamente desde la RAM. 
    Garantiza latencia de 0ms al no requerir viajes a Cosmos DB.
    """
    tipo_limpio = tipo.lower().strip()
    
    if tipo_limpio in ["parametro", "parametros"]: return cache.parametros.get(at, {})
    elif tipo_limpio in ["codigo", "codigos"]: return cache.codigos.get(at, {})
    elif tipo_limpio in ["rut", "ruts"]: return cache.ruts.get(at, [])
    elif tipo_limpio in ["mensaje", "mensajes"]: return cache.mensajes.get(at, {})
    else: raise HTTPException(status_code=404, detail="Tipo de catálogo no reconocido.")


# ==========================================
# GESTIÓN DE CATÁLOGOS: CREACIÓN/EDICIÓN INDIVIDUAL
# ==========================================

@app.post("/api/v1/catalogos/parametros/individual")
async def agregar_parametro(req: ParametroItem):
    item_dict = {**req.model_dump(exclude_none=True), "tipo": "parametro"}
    await cache.carga_masiva_catalogos([item_dict])
    return {"estado": "EXITO", "mensaje": f"Parámetro {req.id} guardado/actualizado en AT {req.at}"}

@app.post("/api/v1/catalogos/codigos/individual")
async def agregar_codigo(req: CodigoItem):
    item_dict = {**req.model_dump(exclude_none=True), "tipo": "codigo"}
    await cache.carga_masiva_catalogos([item_dict])
    return {"estado": "EXITO", "mensaje": f"Código {req.id} guardado/actualizado en AT {req.at}"}

@app.post("/api/v1/catalogos/mensajes/individual")
async def agregar_mensaje(req: MensajeItem):
    item_dict = {**req.model_dump(exclude_none=True), "tipo": "mensaje"}
    await cache.carga_masiva_catalogos([item_dict])
    return {"estado": "EXITO", "mensaje": f"Mensaje {req.id} guardado/actualizado en AT {req.at}"}

@app.post("/api/v1/catalogos/ruts/individual")
async def agregar_rut(req: RutItem):
    item_dict = {**req.model_dump(by_alias=True, exclude_none=True), "tipo": "rut"}
    await cache.carga_masiva_catalogos([item_dict])
    return {"estado": "EXITO", "mensaje": f"RUT {req.id} guardado/actualizado en AT {req.at}"}


# ==========================================
# GESTIÓN DE CATÁLOGOS: CARGA MASIVA (BATCH)
# ==========================================

@app.post("/api/v1/catalogos/parametros/batch")
async def batch_parametros(req: BatchParametros):
    items_dict = [ {**item.model_dump(exclude_none=True), "tipo": "parametro"} for item in req.items ]
    await cache.carga_masiva_catalogos(items_dict)
    return {"estado": "EXITO", "mensaje": f"Se procesaron {len(items_dict)} parámetros."}

@app.post("/api/v1/catalogos/codigos/batch")
async def batch_codigos(req: BatchCodigos):
    items_dict = [ {**item.model_dump(exclude_none=True), "tipo": "codigo"} for item in req.items ]
    await cache.carga_masiva_catalogos(items_dict)
    return {"estado": "EXITO", "mensaje": f"Se procesaron {len(items_dict)} códigos."}

@app.post("/api/v1/catalogos/mensajes/batch")
async def batch_mensajes(req: BatchMensajes):
    items_dict = [ {**item.model_dump(exclude_none=True), "tipo": "mensaje"} for item in req.items ]
    await cache.carga_masiva_catalogos(items_dict)
    return {"estado": "EXITO", "mensaje": f"Se procesaron {len(items_dict)} mensajes."}

@app.post("/api/v1/catalogos/ruts/batch")
async def batch_ruts(req: BatchRuts):
    items_dict = [ {**item.model_dump(by_alias=True, exclude_none=True), "tipo": "rut"} for item in req.items ]
    await cache.carga_masiva_catalogos(items_dict)
    return {"estado": "EXITO", "mensaje": f"Se procesaron {len(items_dict)} RUTs."}


# ==========================================
# INTEGRACIÓN EXTERNA Y PERSISTENCIA
# ==========================================

@app.post("/api/v1/exportar-csv")
async def exportar_csv_selenium(casos: List[CasoQA], at: int = Query(2026)):
    """
    Recibe la matriz JSON y genera un archivo CSV físico.
    Diseñado para integrarse directamente con el bot de Selenium (RPA).
    """
    mensajes_at = cache.mensajes.get(at, {})
    casos_dict = [caso.model_dump(exclude_none=True) for caso in casos]
    exportador = ExportadorCSV(mensajes_at)
    
    csv_str = await run_in_threadpool(exportador.generar_csv, casos_dict)
    
    return Response(
        content=csv_str, 
        media_type="text/csv", 
        headers={"Content-Disposition": "attachment; filename=casos_selenium.csv"}
    )

@app.post("/api/v1/reglas/guardar", response_model=GuardarReglaResponse)
async def guardar_regla_aprobada(req: GuardarReglaRequest):
    """
    Guarda el resultado final aceptado por el usuario.
    El RepositorioHistorial se encarga internamente de generar el hash de la fórmula
    y determinar si corresponde a una nueva versión o a la sobreescritura de la actual.
    """
    try:
        casos_dict = [c.model_dump(exclude_none=True) for c in req.casos]
        version_guardada = await repo_historial.guardar_regla_y_matriz(
            id_val=req.id_validacion, 
            formula=req.formula_cruda,
            texto_fmt=req.texto_formateado,
            casos=casos_dict,
            at=req.at,
            version_documento=req.version_documento,
            codigo_objetivo=req.codigo_objetivo,
            ast_json=req.ast_json
        )
        return GuardarReglaResponse(
            estado="EXITO", 
            mensaje=f"Fórmula y matriz guardadas (Versión {version_guardada}).", 
            version=version_guardada
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al guardar en Cosmos DB: {str(e)}")


@app.get("/api/v1/reglas/historial", response_model=List[HistorialItem])
async def obtener_historial_reglas(at: int = Query(2026, description="Año Tributario")):
    """
    Endpoint ligero para la UI. Devuelve todas las versiones históricas sin cargar los casos pesados.
    """
    try:
        resultados = await repo_historial.obtener_historial_metadatos(at)
        return resultados
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al consultar historial: {str(e)}")

@app.get("/api/v1/reglas/detalle/{id_validacion}", response_model=ReglaDetalleResponse)
async def obtener_detalle_regla(
    id_validacion: str,
    version: int = Query(..., description="Versión exacta a consultar"),
    at: int = Query(2026, description="Año Tributario")
):
    """
    Endpoint para la UI (Vista Detalle). Devuelve el JSON unificado de una regla histórica
    con sus textos originales y el arreglo completo de casos de prueba.
    """
    try:
        detalle_unificado = await repo_historial.obtener_detalle_completo(id_validacion, version, at)
        
        if detalle_unificado is None:
            raise HTTPException(
                status_code=404, 
                detail=f"No se encontró el detalle para la regla '{id_validacion}' (v{version}) en el AT {at}."
            )
            
        return detalle_unificado
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al obtener el detalle de la regla: {str(e)}")

@app.get("/api/v1/reglas/exportar-lote")
async def exportar_lote_csv(
    at: int = Query(2026, description="Año Tributario"), 
    prefijo: str = Query(..., description="Prefijo de la regla (ej. 'a.' o 'm.1')")
):
    """
    Endpoint para Selenium. Genera un CSV masivo con la última versión de todas las reglas de un prefijo.
    """
    try:
        # 1. Obtenemos la lista gigante de casos crudos desde Cosmos DB
        casos_totales = await repo_historial.obtener_lote_casos(at, prefijo)
        
        if not casos_totales:
            raise HTTPException(status_code=404, detail=f"No se encontraron casos para el prefijo '{prefijo}' en el AT {at}.")
        
        # 2. Reutilizamos tu ExportadorCSV existente
        mensajes_at = cache.mensajes.get(at, {})
        exportador = ExportadorCSV(mensajes_at)
        
        # 3. Generamos el CSV en un hilo separado para no bloquear FastAPI
        csv_str = await run_in_threadpool(exportador.generar_csv, casos_totales)
        
        # Limpiamos el nombre del archivo (ej. de 'a.' a 'lote_a_AT2026.csv')
        nombre_seguro = prefijo.replace('.', '_')
        if nombre_seguro.endswith('_'): nombre_seguro = nombre_seguro[:-1]
        
        return Response(
            content=csv_str, 
            media_type="text/csv", 
            headers={"Content-Disposition": f"attachment; filename=lote_{nombre_seguro}_AT{at}.csv"}
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al exportar lote masivo: {str(e)}")


@app.get("/api/v1/reglas/exportar/{id_validacion}")
async def exportar_matriz_individual(
    id_validacion: str,
    version: int = Query(..., description="Versión exacta a exportar"),
    at: int = Query(2026, description="Año Tributario")
):
    """
    Endpoint para la UI. Genera y descarga un CSV de una versión histórica específica.
    """
    try:
        # 1. Buscamos la matriz exacta en Cosmos DB
        casos = await repo_historial.obtener_matriz_especifica(id_validacion, version, at)
        
        if casos is None:
            raise HTTPException(
                status_code=404, 
                detail=f"No se encontró la matriz para la regla '{id_validacion}' (v{version}) en el AT {at}."
            )
        
        # 2. Reutilizamos tu ExportadorCSV existente
        mensajes_at = cache.mensajes.get(at, {})
        exportador = ExportadorCSV(mensajes_at)
        
        # 3. Generamos el CSV en un hilo separado
        csv_str = await run_in_threadpool(exportador.generar_csv, casos)
        
        # 4. Formateamos el nombre del archivo (Ej: casos_a_4_v2_AT2026.csv)
        nombre_seguro = id_validacion.replace('.', '_')
        nombre_archivo = f"casos_{nombre_seguro}_v{version}_AT{at}.csv"
        
        return Response(
            content=csv_str, 
            media_type="text/csv", 
            headers={"Content-Disposition": f"attachment; filename={nombre_archivo}"}
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al exportar matriz individual: {str(e)}")



# ==========================================
# MOTOR DE INGENIERÍA INVERSA (FASE 4 - PREPARACIÓN)
# ==========================================

@app.get("/api/v1/reglas/dependencias/{codigo}")
async def buscar_dependencias(codigo: str, at: int = Query(2026, description="Año Tributario")):
    """
    Dado un código (ej. 494), busca y devuelve todas las reglas de negocio (ASTs) que impactan sobre él.
    """
    codigo_limpio = f"[{codigo.replace('[', '').replace(']', '').strip()}]"
    reglas_asociadas = await repo_historial.buscar_dependencias_por_codigo(codigo_limpio, at)
    
    if not reglas_asociadas:
        return {"mensaje": f"No se encontraron reglas que afecten al código {codigo_limpio} en el AT {at}", "resultados": []}
        
    return {"codigo_objetivo": codigo_limpio, "at": at, "total_encontradas": len(reglas_asociadas), "resultados": reglas_asociadas}

@app.post("/api/v1/reglas/dependencias/batch")
async def buscar_dependencias_lote(req: BatchDependenciasRequest):
    """
    Consulta Masiva: Optimizada para reducir latencia de red.
    Obtiene múltiples dependencias en un solo viaje a Cosmos DB.
    """
    if not req.codigos: 
        raise HTTPException(status_code=400, detail="Debe proporcionar al menos un código.")
        
    codigos_limpios = [f"[{c.replace('[', '').replace(']', '').strip()}]" for c in req.codigos]
    resultados = await repo_historial.buscar_dependencias_batch(codigos_limpios, req.at)
    
    return {"at": req.at, "total_encontrados": len(resultados), "resultados": resultados}

@app.post("/api/v1/reglas/memoria/cargar-asts")
async def cargar_memoria_asts(req: CargarAstsRequest):
    """
    Endpoint de preparación On-Demand.
    Descarga todos los árboles AST desde Azure a la memoria RAM del servidor.
    Se utiliza como paso previo a ejecutar simulaciones masivas (Fase 4).
    """
    try:
        total_cargados = await cache.cargar_asts_masivos(req.at)
        return {"estado": "EXITO", "mensaje": f"Se cargaron {total_cargados} ASTs (AT {req.at}) a la memoria RAM."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al hidratar memoria con ASTs: {str(e)}")