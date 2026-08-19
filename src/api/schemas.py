from pydantic import BaseModel, Field
from typing import Dict, Any, Optional, List, Union

# ==========================================
# 1. ESQUEMAS DE ENTRADA (Catálogos y Requests)
# ==========================================

class ConfigMotor(BaseModel):
    usar_decimales: bool = Field(False, description="True para mantener decimales, False para truncar a enteros.")
    semilla_generacion: float = Field(1000000.0, description="Valor base que el motor Z3 intentará alcanzar.")
    margen_semilla: float = Field(50000.0, description="Margen de varianza permitido.")

class FormulaRequest(BaseModel):
    at: int = Field(..., description="Año Tributario (ej. 2026)")
    id_validacion: str = Field(..., description="ID de la validación, ej: m.1.1")
    formula_cruda: str = Field(..., description="Texto extraído directamente del Excel del SII")
    version_documento: str = Field("1.0", description="Versión del documento de origen (ej. 1.1)") 
    config_motor: Optional[ConfigMotor] = Field(default_factory=ConfigMotor, description="Configuración dinámica de Z3")

# --- Esquemas Individuales ---

class ParametroItem(BaseModel):
    at: int = Field(..., description="Año Tributario")
    id: str = Field(..., description="ID del parámetro (ej. P84)")
    valor: float = Field(..., description="Valor numérico")
    descripcion: Optional[str] = ""

class CodigoItem(BaseModel):
    at: int = Field(..., description="Año Tributario")
    id: str = Field(..., description="ID del código (ej. [494])")
    signo_permitido: str = Field(..., description="+ , - o +/-")
    autocalculado: bool = Field(False, description="Indica si el código es autocalculado")
    descripcion: Optional[str] = ""

class MensajeItem(BaseModel):
    at: int = Field(..., description="Año Tributario")
    id: str = Field(..., description="ID del mensaje (ej. c.4)")
    descripcion: str = Field(..., description="Texto del mensaje de error")

class RutItem(BaseModel):
    at: int = Field(..., description="Año Tributario")
    id: str = Field(..., description="El mismo RUT (ej. 11.111.111-1)")
    rut: str = Field(..., description="El RUT del contribuyente")
    tipo_contribuyente: Union[int, str] = Field(..., description="Tipo principal del contribuyente")
    subtipo: Optional[Union[int, str]] = None
    es_formulario_universal: bool = Field(False, description="True si el RUT despliega el formulario universal F22.14 completo")
    atributos: List[str] = Field(default_factory=list)

# --- Esquemas de Carga Masiva (Batch) ---

class BatchParametros(BaseModel):
    items: List[ParametroItem]

class BatchCodigos(BaseModel):
    items: List[CodigoItem]

class BatchMensajes(BaseModel):
    items: List[MensajeItem]

class BatchRuts(BaseModel):
    items: List[RutItem]

# ==========================================
# 2. ESQUEMAS INTERMEDIOS
# ==========================================

class PerfilRut(BaseModel):
    tipo: Union[int, str] = "CUALQUIERA"
    subtipo: Union[int, str] = "CUALQUIERA"
    requiere_formulario_universal: bool = True # Actualizado
    atributos_requeridos: List[str] = []
    atributos_prohibidos: List[str] = []

class ObjetivoCalculo(BaseModel):
    codigo: str
    valor: Any

class DetalleInputs(BaseModel):
    editables_originales: Dict[str, Any] = Field(default_factory=dict)
    autocalculados_originales: Dict[str, Any] = Field(default_factory=dict)
    editables_inyectados: Dict[str, Any] = Field(default_factory=dict)

# ==========================================
# 3. ESQUEMA DEL CASO DE PRUEBA (Salida de Fase 2 y 3)
# ==========================================
class CasoQA(BaseModel):
    id_validacion: str
    tipo_escenario: Optional[str] = None
    descripcion_qa: Optional[str] = None
    rut: Optional[str] = None
    inputs_matematicos: Optional[Dict[str, Any]] = None # <--- 1. Bóveda de auditoría
    inputs: Optional[Dict[str, Any]] = None             # <--- 2. Plano para Selenium
    detalle_inputs: Optional[DetalleInputs] = None      # <--- 3. Desglose para el Frontend
    vectores: Optional[Dict[str, Any]] = None
    parametros: Optional[Dict[str, Any]] = None
    parametros_anteriores: dict = Field(default_factory=dict)
    resultado_esperado: Optional[str] = None
    huella_logica: Optional[Dict[str, str]] = None
    perfil_rut_requerido: Optional[Union[PerfilRut, str]] = None
    objetivo: Optional[ObjetivoCalculo] = None
    error: Optional[str] = None
    estado_interno: Optional[str] = None

# ==========================================
# 4. ESQUEMAS DE RESPUESTA (Responses)
# ==========================================

class NormalizacionResponse(BaseModel):
    estado: str = Field(..., description="EXITO o ERROR")
    texto_formateado: Optional[str] = None
    tipo_error: Optional[str] = None
    mensaje: Optional[str] = None

class GeneracionResponse(BaseModel):
    estado: str
    id_validacion: str
    mensaje: str
    texto_formateado: str = Field(..., description="La fórmula normalizada generada por la Fase 1")
    codigo_objetivo: Optional[str] = Field(None, description="Código F22 afectado (ej. [494])")
    ast_json: Optional[Dict[str, Any]] = Field(None, description="Árbol AST serializado")
    total_casos_generados: int
    total_casos_optimizados: int
    porcentaje_reduccion: float
    casos_completos: List[CasoQA] = Field(..., description="Matriz original completa enriquecida") # <--- NUEVO NOMBRE
    casos_optimizados: List[CasoQA] 

class HistorialItem(BaseModel):
    id_validacion: str
    version: int
    version_documento: str
    fecha: str
    total_casos: int

class ReglaDetalleResponse(BaseModel):
    id_validacion: str
    version: int
    version_documento: str
    formula_cruda: Optional[str] = None
    texto_formateado: Optional[str] = None
    casos: List[CasoQA] = []


# ==========================================
# 5. ESQUEMAS DE GUARDADO Y BÚSQUEDA
# ==========================================

class GuardarReglaRequest(BaseModel):
    at: int = Field(..., description="Año Tributario (ej. 2026)")
    id_validacion: str = Field(..., description="ID de la validación, ej: a.4")
    formula_cruda: str = Field(..., description="La fórmula original extraída")
    texto_formateado: str = Field(..., description="El texto normalizado (Fase 1)")
    version_documento: str = Field("1.0", description="Versión del Excel de origen")
    codigo_objetivo: Optional[str] = Field(None, description="Código F22 afectado")
    ast_json: Optional[Dict[str, Any]] = Field(None, description="Árbol AST serializado")
    casos: List[CasoQA] = Field(..., description="La matriz de casos aprobada por el usuario")

class GuardarReglaResponse(BaseModel):
    estado: str
    mensaje: str
    version: int

class BatchDependenciasRequest(BaseModel):
    at: int = Field(..., description="Año Tributario (ej. 2026)")
    codigos: List[str] = Field(..., description="Lista de códigos objetivo, ej: ['[494]', '[123]']")

class CargarAstsRequest(BaseModel):
    at: int = Field(..., description="Año Tributario a cargar en memoria")