# src/enriquecedor/grafo_expansor.py
from collections import deque
from lark import Tree, Token
from src.generador.z3_core import MotorZ3
from src.generador.evaluator import EvaluadorAST
from src.enriquecedor.extractor_modelo import ExtractorModelo

class DependencyResolver:
    def __init__(self, cache_codigos: dict, cache_asts: dict, config_motor: dict = None):
        """
        Inicializa el resolutor inyectando los catálogos en RAM.
        Fuerza el 'modo_inverso' para apagar las semillas (Soft Constraints) en el MotorZ3.
        """
        self.cache_codigos = cache_codigos
        self.cache_asts = cache_asts
        
        self.config_motor = config_motor.copy() if config_motor else {}
        self.config_motor["modo_inverso"] = True
        
        self.extractor = ExtractorModelo(self.cache_codigos)

    def _deserializar_ast(self, nodo_dict):
        """
        Reconstruye recursivamente el objeto lark.Tree a partir del JSON serializado
        proveniente de la base de datos o la RAM.
        """
        if isinstance(nodo_dict, dict):
            tipo = nodo_dict.get("tipo")
            if tipo == "token":
                return Token(nodo_dict["nombre"], nodo_dict["valor"])
            elif tipo == "nodo":
                hijos = [self._deserializar_ast(h) for h in nodo_dict.get("hijos", [])]
                return Tree(nodo_dict["nombre"], hijos)
        
        return nodo_dict

    def resolver_dependencias(self, metas_autocalculadas: dict) -> dict:
        """
        Recibe las metas exigidas por la Fase 2.
        Expande el grafo hacia abajo y retorna un diccionario con las hojas resueltas.
        Levanta ValueError si hay inconsistencias de datos, traducción o matemáticas.
        """
        motor = MotorZ3(self.cache_codigos, self.config_motor)
        evaluador = EvaluadorAST(motor)
        
        cola = deque()
        visitados = set()

        for clave_corchetes, valor_objetivo in metas_autocalculadas.items():
            codigo_limpio = clave_corchetes.replace('[', '').replace(']', '').strip()
            
            # FIX: Inyectar meta a Z3 con los corchetes puestos para que coincida con el EvaluadorAST
            clave_exacta = f"[{codigo_limpio}]"
            var_z3 = motor.obtener_o_crear_variable(clave_exacta)
            motor.solver.add(var_z3 == valor_objetivo)
            
            cola.append(codigo_limpio)
            visitados.add(codigo_limpio)

        while cola:
            codigo_actual = cola.popleft()
            clave_ast = f"[{codigo_actual}]"
            
            # Obtenemos el diccionario JSON desde la RAM
            ast_json = self.cache_asts.get(clave_ast)
            
            if not ast_json:
                raise ValueError(f"Falta el arbol AST para el código {clave_ast}. Verifica que su validación haya sido procesada previamente.") 

            # Magia: Reconstruimos el objeto Tree antes de evaluar
            ast_tree = self._deserializar_ast(ast_json)

            try:
                # Evaluamos el AST, que nos devolverá la ecuación lógica completa
                restriccion_z3 = evaluador.evaluar(ast_tree)
                
                # Inyectamos la restricción directamente a Z3.
                motor.solver.add(restriccion_z3)
            except Exception as e:
                raise ValueError(f"Error al traducir el AST del código {clave_ast}: {str(e)}")

            for nombre_var in list(motor.variables_memoria.keys()):
                codigo_var_limpio = nombre_var.replace('[', '').replace(']', '').strip()
                
                if not codigo_var_limpio.isdigit():
                    continue
                    
                if codigo_var_limpio not in visitados:
                    info_codigo = self.cache_codigos.get(codigo_var_limpio, {})
                    if info_codigo.get("autocalculado", False):
                        cola.append(codigo_var_limpio)
                        visitados.add(codigo_var_limpio)

        modelo = motor.resolver_y_obtener_modelo()
        
        if not modelo:
            raise ValueError("Contradicción Matemática: Imposible alcanzar los valores exigidos con las fórmulas subyacentes.")
            
        return self.extractor.procesar_modelo(modelo)