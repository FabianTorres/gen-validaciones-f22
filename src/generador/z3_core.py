import z3

class MotorZ3:
    def __init__(self, cache_codigos: dict, config_motor: dict = None):
        """
        Recibe el catálogo de signos directamente desde la memoria RAM.
        """
        self.solver = z3.Optimize()
        self.variables_memoria = {}
        self.config_motor = config_motor or {}
        self._configurar_semilla_base()
        
        # Guardamos el catálogo inyectado desde la RAM
        self.catalogo_signos = cache_codigos

    def _configurar_semilla_base(self):
        """
        Convertimos la semilla a float para mantener la 
        compatibilidad absoluta con el dominio Real.
        """
        # Extraemos la semilla dinámicamente con un valor de 1,000,000 por defecto
        semilla = self.config_motor.get("semilla_generacion", 1000000)
        self.semilla_objetivo = float(semilla)

    def obtener_o_crear_variable(self, nombre_var):
        """
        Todo se instancia como z3.Real() para evitar 'parser error'
        al multiplicar códigos con parámetros decimales (ej. P84 = 1.05).
        """
        if nombre_var not in self.variables_memoria:
            var_z3 = z3.Real(nombre_var)
            self.variables_memoria[nombre_var] = var_z3
            
            # 1. Extraer el código y aplicar restricción de signo/dominio
            codigo_limpio = nombre_var.replace("[", "").replace("]", "")
            
            if codigo_limpio.isdigit():
                # Obtenemos el objeto del código. Si no existe, asumimos un dict vacío
                info_codigo = self.catalogo_signos.get(codigo_limpio, {})
                regla_signo = info_codigo.get("signo_permitido", "+")
                
                if regla_signo == "+":
                    self.solver.add(var_z3 >= 0)
                elif regla_signo == "-":
                    self.solver.add(var_z3 <= 0)
                elif regla_signo == "X":
                    # Restricción binaria estricta para marcas/checkboxes
                    self.solver.add(z3.Or(var_z3 == 0, var_z3 == 1))
                # Si la regla es "+/-", no agregamos restricción matemática

                # 2. Le pedimos al motor que se acerque a la semilla
                if regla_signo != "X":
                    self.solver.add_soft(var_z3 == self.semilla_objetivo)
            else:
                # Si no es numérico (ej. parámetros o atributos), aplicamos semilla por defecto
                self.solver.add_soft(var_z3 == self.semilla_objetivo)
                
        return self.variables_memoria[nombre_var]

    def resolver_y_obtener_modelo(self):
        """Ejecuta la evaluación matemática."""
        if self.solver.check() == z3.sat:
            return self.solver.model()
        return None