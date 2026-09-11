import z3


class MotorZ3:
    def __init__(self, cache_codigos: dict, config_motor: dict = None):
        self.variables_memoria = {}
        self.config_motor = config_motor or {}
        self._configurar_semilla_base()
        self.catalogo_signos = cache_codigos

        # Bóvedas inmutables para clonación limpia
        self.hard_constraints_base = []
        self.soft_constraints_base = []
        self.solver = z3.Optimize()

        # ---> TIMEOUT DE SEGURIDAD (15 SEGUNDOS) <---
        self.solver.set("timeout", 15000)

    def _configurar_semilla_base(self):
        semilla = self.config_motor.get("semilla_generacion", 1000000)
        self.semilla_objetivo = float(semilla)
        semilla_entera = int(self.semilla_objetivo)
        z3.set_param("smt.random_seed", semilla_entera)
        z3.set_param("sat.random_seed", semilla_entera)

    def agregar_restriccion_base(self, restriccion):
        """Registra restricciones duras universales."""
        self.hard_constraints_base.append(restriccion)
        self.solver.add(restriccion)

    def obtener_o_crear_variable(self, nombre_var):
        if nombre_var not in self.variables_memoria:
            var_z3 = z3.Real(nombre_var)
            self.variables_memoria[nombre_var] = var_z3

            codigo_limpio = nombre_var.replace("[", "").replace("]", "").strip()

            if codigo_limpio.isdigit():
                info_codigo = self.catalogo_signos.get(codigo_limpio, {})
                regla_signo = info_codigo.get("signo_permitido", "+")

                if regla_signo == "+":
                    self.agregar_restriccion_base(var_z3 >= 0)
                elif regla_signo == "-":
                    self.agregar_restriccion_base(var_z3 <= 0)
                elif regla_signo == "X":
                    self.agregar_restriccion_base(z3.Or(var_z3 == 0, var_z3 == 1))

                if regla_signo != "X" and not self.config_motor.get(
                    "modo_inverso", False
                ):
                    es_principal = nombre_var in getattr(
                        self, "vars_principales", set()
                    )

                    if es_principal:
                        self.soft_constraints_base.append(
                            (var_z3 == self.semilla_objetivo, 1000)
                        )
                        self.solver.add_soft(
                            var_z3 == self.semilla_objetivo, weight=1000
                        )

                        self.soft_constraints_base.append((var_z3 > 0, 2000))
                        self.solver.add_soft(var_z3 > 0, weight=2000)
                    else:
                        self.soft_constraints_base.append((var_z3 == 0, 1))
                        self.solver.add_soft(var_z3 == 0, weight=1)
            else:
                if not self.config_motor.get("modo_inverso", False):
                    self.soft_constraints_base.append(
                        (var_z3 == self.semilla_objetivo, 1)
                    )
                    self.solver.add_soft(var_z3 == self.semilla_objetivo)

        return self.variables_memoria[nombre_var]

    def crear_solver_aislado(self, restricciones_extra=None):
        """Crea un solver 100% virgen para el escenario, eliminando push/pop corruptos."""
        nuevo_solver = z3.Optimize()
        # ---> TIMEOUT DE SEGURIDAD (20 SEGUNDOS) <---
        nuevo_solver.set("timeout", 15000)
        semilla_entera = int(self.semilla_objetivo)
        z3.set_param("smt.random_seed", semilla_entera)
        z3.set_param("sat.random_seed", semilla_entera)

        for h in self.hard_constraints_base:
            nuevo_solver.add(h)

        for expr, w in self.soft_constraints_base:
            nuevo_solver.add_soft(expr, weight=w)

        if restricciones_extra:
            for r in restricciones_extra:
                nuevo_solver.add(r)

        return nuevo_solver

    def resolver_y_obtener_modelo(self):
        if self.solver.check() == z3.sat:
            return self.solver.model()
        return None
