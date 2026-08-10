from src.generador.z3_core import MotorZ3
from src.generador.evaluator import EvaluadorAST
from src.generador.providers.param_provider import ParamProvider
from src.generador.providers.rut_provider import RutProvider
from src.generador.strategies.boundary_builder import BoundaryBuilder
from src.generador.strategies.implication_builder import ImplicationBuilder
from src.generador.strategies.calculation_builder import CalculationBuilder

class TestMatrixBuilder:
    def __init__(self, cache_parametros: dict, cache_ruts: list, cache_codigos: dict, config_motor: dict = None):
        """
        Recibe los catálogos directamente de la RAM y la configuración de sesión (inyectados por FastAPI).
        """
        self.param_provider = ParamProvider(cache_parametros)
        self.rut_provider = RutProvider(cache_ruts)
        self.cache_codigos = cache_codigos
        self.config_motor = config_motor or {}

    def generar_matriz_pruebas(self, ast_tree, id_val):
        tipo_regla = self._identificar_familia_logica(ast_tree)
        
        # 1. BARRIDO DE MEMORIA: Instanciamos un motor matemático pasándole los códigos en RAM y la configuración SMT
        self.motor = MotorZ3(self.cache_codigos, self.config_motor)
        self.evaluador = EvaluadorAST(self.motor)
        
        # 2. Instanciamos la estrategia pasándole el motor limpio y la configuración
        estrategia = self._seleccionar_estrategia(tipo_regla)
        
        if not estrategia:
            return [{"id_validacion": id_val, "error": f"Aún no hay estrategia para: {tipo_regla}"}]
            
        # 3. Inyectamos las constantes (P84, P736) al motor limpio
        self.param_provider.inyectar_en_motor(self.motor)
        
        # 4. Delegamos al experto
        return estrategia.generar_casos(ast_tree, id_val)

    def _identificar_familia_logica(self, ast_tree):
        for hijo in ast_tree.children:
            if hasattr(hijo, 'data'):
                if hijo.data in ['autocalculado', 'cota', 'implicacion', 'validacion_libre']:
                    return hijo.data
        return "DESCONOCIDO"

    def _seleccionar_estrategia(self, tipo_regla):
        if tipo_regla == 'cota':
            return BoundaryBuilder(self.evaluador, self.motor, self.param_provider, self.rut_provider, self.config_motor)
            
        # Agrupamos las Implicaciones (D, E) y las Validaciones de Lógica Libre (M)
        elif tipo_regla in ['implicacion', 'validacion_libre']:
            return ImplicationBuilder(self.evaluador, self.motor, self.param_provider, self.rut_provider, self.config_motor)
            
        # Dejamos solo los autocalculados (A, B) para el CalculationBuilder
        elif tipo_regla == 'autocalculado':
            return CalculationBuilder(self.evaluador, self.motor, self.param_provider, self.rut_provider, self.config_motor)
            
        return None