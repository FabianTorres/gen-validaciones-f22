from src.generador.z3_core import MotorZ3
from src.generador.evaluator import EvaluadorAST
from src.generador.providers.param_provider import ParamProvider
from src.generador.providers.rut_provider import RutProvider
from src.generador.strategies.boundary_builder import BoundaryBuilder
from src.generador.strategies.implication_builder import ImplicationBuilder
from src.generador.strategies.calculation_builder import CalculationBuilder
from lark import Tree, Token

class TestMatrixBuilder:
    def __init__(self, cache_parametros: dict, cache_ruts: list, cache_codigos: dict, cache_asts: dict, config_motor: dict = None):
        """
        Recibe los catálogos directamente de la RAM, incluyendo los ASTs.
        """
        self.param_provider = ParamProvider(cache_parametros)
        self.rut_provider = RutProvider(cache_ruts)
        self.cache_codigos = cache_codigos
        self.cache_asts = cache_asts  # Diccionario JSON con los AST guardados
        self.config_motor = config_motor or {}

    def generar_matriz_pruebas(self, ast_tree, id_val):
        tipo_regla = self._identificar_familia_logica(ast_tree)
        
        # 1. BARRIDO DE MEMORIA
        self.motor = MotorZ3(self.cache_codigos, self.config_motor)
        self.evaluador = EvaluadorAST(self.motor)

        # ---> SPARSITY: REGISTRO DE VARIABLES PRINCIPALES <---
        # Registramos las variables del árbol principal para que Z3 sepa a cuáles 
        # aplicarles la semilla de 1M y a cuáles aplicarles la semilla de 0 (Sparsity).
        vars_principales = set()
        def pre_scan(n):
            if not hasattr(n, 'data'):
                v = str(n).replace('"', '').strip().upper()
                if v.isdigit(): vars_principales.add(f"[{v}]")
                elif v.startswith('[') and v.endswith(']'): vars_principales.add(v)
                return
            for h in getattr(n, 'children', []): pre_scan(h)
        pre_scan(ast_tree)
        self.motor.vars_principales = vars_principales

        # ---> FIX: PREVENIR AUTO-REFERENCIA <---
        # Extraemos el código objetivo de la regla actual para que el escáner no lo busque
        visitados_inicial = set()
        for hijo in getattr(ast_tree, 'children', []):
            if getattr(hijo, 'data', '') == 'autocalculado':
                cod_obj = str(hijo.children[0]).replace('[', '').replace(']', '').strip()
                visitados_inicial.add(cod_obj)
                break
        
        # ---> ESCUDO FAIL-FAST (CAPTURA) <---
        try:
            # Le pasamos la lista inicial con el código objetivo ya "visitado"
            restricciones_leyes_universo, asts_dep = self._resolver_dependencias_autocalculados(ast_tree, visitados_inicial)
        except ValueError as e:
            return [{"id_validacion": id_val, "error": str(e), "estado_interno": "ERROR_AST_FALTANTE"}]
            
        for restriccion in restricciones_leyes_universo:
            self.motor.solver.add(restriccion)

        # 2. Instanciamos la estrategia pasándole el motor Y LAS DEPENDENCIAS DIRECTAMENTE
        estrategia = self._seleccionar_estrategia(tipo_regla, asts_dep)
        
        if not estrategia:
            return [{"id_validacion": id_val, "error": f"Aún no hay estrategia para: {tipo_regla}"}]
            
        # 3. Inyectamos las constantes al motor (Con Radar Pre-emptivo)
        # Convertimos el AST principal a texto
        ast_completo_str = str(ast_tree).upper() if ast_tree else ""
        
        # Sumamos los ASTs de las dependencias si es que existen en esta clase
        if hasattr(self, 'asts_dependencias') and self.asts_dependencias:
            ast_completo_str += " " + " ".join([str(a).upper() for a in self.asts_dependencias if a])
            
        # Enviamos el motor Y el radar de texto al proveedor
        self.param_provider.inyectar_en_motor(self.motor, ast_completo_str)
        
        # 4. Delegamos al experto
        return estrategia.generar_casos(ast_tree, id_val)

    def _resolver_dependencias_autocalculados(self, nodo_raiz, visitados: set):
        restricciones = []
        asts_encontrados = [] 
        
        def escanear(n):
            if not hasattr(n, 'data'):
                tipo = getattr(n, 'type', '')
                if tipo in ('CODIGO', 'VARIABLE_CORCHETE'):
                    val_str = str(n).replace('"', '').strip().upper()
                    cod_limpio = val_str.replace('[', '').replace(']', '')
                    
                    if cod_limpio.isdigit() and cod_limpio not in visitados:
                        visitados.add(cod_limpio)
                        info_cod = self.cache_codigos.get(cod_limpio, {})
                        
                        if info_cod.get("autocalculado", False):
                            clave_ast = f"[{cod_limpio}]"
                            ast_dict = self.cache_asts.get(clave_ast)
                            
                            # ---> ESCUDO FAIL-FAST (DETECCIÓN) <---
                            if not ast_dict:
                                raise ValueError(f"Falta el arbol AST para el código {clave_ast}. Verifica que su validación haya sido procesada previamente.")
                                
                            ast_real = self._deserializar_ast(ast_dict)
                            asts_encontrados.append(ast_real) 
                            z3_expr = self.evaluador.evaluar(ast_real)
                            restricciones.append(z3_expr)
                            escanear(ast_real)
                return
            for hijo in getattr(n, 'children', []):
                escanear(hijo)

        escanear(nodo_raiz)
        return restricciones, asts_encontrados 

    def _deserializar_ast(self, nodo_dict):
        """
        Reconstruye el JSON plano de Cosmos DB devuelta a un objeto nativo de Lark
        para que el EvaluadorAST pueda leerlo sin problemas.
        """
        if isinstance(nodo_dict, str):
            return nodo_dict
        if nodo_dict.get("tipo") == "token":
            return Token(nodo_dict["nombre"], nodo_dict["valor"])
        if nodo_dict.get("tipo") == "nodo":
            hijos = [self._deserializar_ast(h) for h in nodo_dict.get("hijos", [])]
            return Tree(nodo_dict["nombre"], hijos)
        return nodo_dict

    def _identificar_familia_logica(self, ast_tree):
        for hijo in ast_tree.children:
            if hasattr(hijo, 'data'):
                if hijo.data in ['autocalculado', 'cota', 'implicacion', 'validacion_libre']:
                    return hijo.data
        return "DESCONOCIDO"

    def _seleccionar_estrategia(self, tipo_regla, asts_dep):
        if tipo_regla == 'cota':
            return BoundaryBuilder(self.evaluador, self.motor, self.param_provider, self.rut_provider, self.config_motor, asts_dep)
        elif tipo_regla in ['implicacion', 'validacion_libre']:
            return ImplicationBuilder(self.evaluador, self.motor, self.param_provider, self.rut_provider, self.config_motor, asts_dep)
        elif tipo_regla == 'autocalculado':
            return CalculationBuilder(self.evaluador, self.motor, self.param_provider, self.rut_provider, self.config_motor, asts_dep)
        return None