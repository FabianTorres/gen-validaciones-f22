import z3
from src.generador.z3_core import MotorZ3
from src.generador.evaluator import EvaluadorAST

class GeneradorCasos:
    def __init__(self):
        self.motor = MotorZ3()
        self.evaluador = EvaluadorAST(self.motor)

    def generar_caso_positivo(self, ast_tree):
        """
        Genera el 'Happy Path': Un set de datos que hace que la regla se cumpla 
        perfectamente sin levantar errores en el formulario.
        """
        # 1. Traducimos el Árbol completo a una restricción Z3
        restriccion_principal = self.evaluador.evaluar(ast_tree)
        
        # 2. Le inyectamos la restricción al motor
        self.motor.solver.add(restriccion_principal)
        
        # 3. Resolvemos la matemática
        modelo = self.motor.resolver_y_obtener_modelo()
        
        if modelo is None:
            return {"Estado": "INSATISFACTIBLE", "Detalle": "La regla tiene una contradicción matemática imposible de resolver."}
            
        # 4. Extraemos los valores generados y los formateamos
        resultado = {"Estado": "EXITO", "Tipo_Caso": "Positivo Base (Happy Path)", "Datos": {}}
        
        for variable_z3 in modelo:
            nombre = variable_z3.name()
            # Obtenemos el valor numérico. Z3 devuelve fracciones nativas (ej. 10/3),
            # así que usamos eval() y as_string() para castearlo limpiamente a float o int.
            valor_crudo = modelo[variable_z3]
            
            if z3.is_real(valor_crudo) or z3.is_algebraic_value(valor_crudo):
                # Extraemos el valor decimal como string y lo pasamos a float
                valor_limpio = float(valor_crudo.as_decimal(4).rstrip('?'))
            else:
                valor_limpio = valor_crudo.as_long()
                
            resultado["Datos"][nombre] = valor_limpio
            
        return resultado