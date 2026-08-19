# src/generador/z3_core.py
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

        # ---> NUEVO: BLOQUEO DE DETERMINISMO ABSOLUTO DE Z3 <---
        # Obligamos al motor interno a tomar siempre las mismas decisiones en empates
        semilla_entera = int(self.semilla_objetivo)
        z3.set_param('smt.random_seed', semilla_entera)
        z3.set_param('sat.random_seed', semilla_entera)

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
                
                # Extraemos la bandera desde el catálogo
                es_autocalculado = info_codigo.get("autocalculado", False)
                
                if regla_signo == "+":
                    self.solver.add(var_z3 >= 0)
                elif regla_signo == "-":
                    self.solver.add(var_z3 <= 0)
                elif regla_signo == "X":
                    # Restricción binaria estricta para marcas/checkboxes
                    self.solver.add(z3.Or(var_z3 == 0, var_z3 == 1))

                # ---> FIX ARQUITECTURA (SHIFT-LEFT) + SPARSITY <---
                # En el nuevo paradigma, TODO recibe soft constraints, pero con pesos distintos.
                if regla_signo != "X" and not self.config_motor.get("modo_inverso", False):
                    es_principal = nombre_var in getattr(self, 'vars_principales', set())
                    
                    if es_principal:
                        # 1. ALTA PRIORIDAD: Alcanzar la semilla (Peso 1000)
                        self.solver.add_soft(var_z3 == self.semilla_objetivo, weight=1000)
                        
                        # 2. NUEVO ESCUDO QA (Anti-Zombies): Obligamos a testear todas las variables.
                        # Le damos peso 2000 para que Z3 prefiera "romper la semilla"
                        # antes que apagar la celda a 0.
                        self.solver.add_soft(var_z3 > 0, weight=2000)
                    else:
                        # SPARSITY (Peso 1): Las celdas inyectadas siguen queriendo ser 0.
                        self.solver.add_soft(var_z3 == 0, weight=1)
            else:
                # Si no es numérico (ej. parámetros o atributos), evaluamos la Fase
                if not self.config_motor.get("modo_inverso", False):
                    self.solver.add_soft(var_z3 == self.semilla_objetivo)
                
        return self.variables_memoria[nombre_var]

    def resolver_y_obtener_modelo(self):
        """Ejecuta la evaluación matemática."""
        if self.solver.check() == z3.sat:
            return self.solver.model()
        return None