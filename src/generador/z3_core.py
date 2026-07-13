import z3
import os
from src.config import settings

class MotorZ3:
    def __init__(self):
        self.solver = z3.Optimize()
        self.variables_memoria = {}
        self._configurar_semilla_base()
        
        # Cargamos el catálogo en memoria apenas arranca el motor
        self.catalogo_signos = self._cargar_catalogo()

    def _configurar_semilla_base(self):
        """
        Convertimos la semilla a float para mantener la 
        compatibilidad absoluta con el dominio Real.
        """
        self.semilla_objetivo = float(settings.SEMILLA_GENERACION)

    def _cargar_catalogo(self):
        """
        Lee el catálogo TXT para saber qué dominio matemático aplicar a cada código.
        """
        ruta_catalogo = "data/catalogo_codigos.txt"
        catalogo = {}
        
        if os.path.exists(ruta_catalogo):
            with open(ruta_catalogo, 'r', encoding='utf-8') as f:
                for linea in f:
                    linea_limpia = linea.strip()
                    # Ignorar líneas vacías o la cabecera
                    if not linea_limpia or linea_limpia.startswith("CODIGO") or "|" not in linea_limpia:
                        continue
                    
                    partes = linea_limpia.split("|")
                    if len(partes) >= 2:
                        codigo = partes[0].strip()
                        signo = partes[1].strip()
                        catalogo[codigo] = signo
        else:
            print(f"⚠️ MotorZ3 no encontró {ruta_catalogo}. Se asumirá signo positivo por defecto.")
            
        return catalogo

    def obtener_o_crear_variable(self, nombre_var):
        """
        ¡LA CLAVE DEL ÉXITO! 
        Todo se instancia como z3.Real() para evitar 'parser error'
        al multiplicar códigos con parámetros decimales (ej. P84 = 1.05).
        """
        if nombre_var not in self.variables_memoria:
            var_z3 = z3.Real(nombre_var)
            self.variables_memoria[nombre_var] = var_z3
            
            # 1. Le pedimos al motor que se acerque a la semilla
            self.solver.add_soft(var_z3 == self.semilla_objetivo)
            
            # 2. Extraer el código y aplicar restricción de signo
            codigo_limpio = nombre_var.replace("[", "").replace("]", "")
            
            if codigo_limpio.isdigit():
                # Obtenemos la regla del diccionario. Si no existe, asumimos "+" (Opción B)
                regla_signo = self.catalogo_signos.get(codigo_limpio, "+") 
                
                if regla_signo == "+":
                    self.solver.add(var_z3 >= 0)
                elif regla_signo == "-":
                    self.solver.add(var_z3 <= 0)
                # Si la regla es "+/-", no agregamos restricción matemática
                
        return self.variables_memoria[nombre_var]

    def resolver_y_obtener_modelo(self):
        """Ejecuta la evaluación matemática."""
        if self.solver.check() == z3.sat:
            return self.solver.model()
        return None