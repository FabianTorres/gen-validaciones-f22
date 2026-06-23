"""
Configuraciones Globales del Generador de Validaciones F22 (Fase 2)
"""

# --- TIPADO DE DATOS ---
# Define la naturaleza matemática de los inputs (variables/códigos) y el tratamiento de los resultados.
#
# True  = Utiliza precisión decimal estricta. Las variables y la semilla se instancian como punto 
#         flotante (Reales en Z3). Si la fórmula completa da decimales, el resultado se mantiene tal cual.
#
# False = Utiliza valores enteros estrictos. Las variables y la semilla se instancian como Enteros puros.
#         REGLA DE REDONDEO: Si el cálculo interno choca con un multiplicador decimal (ej. [123] * 0.5) 
#         y el resultado final produce fracciones, el motor redondeará el resultado final para 
#         devolverlo a su estado Entero normativo.
#
# PRIORIDAD ABSOLUTA: Las funciones explícitas redactadas en el documento del SII (ej. ROUND, MIN, MAX) 
# tienen autoridad máxima y sobreescriben esta configuración lógica.
USAR_DECIMALES = False

# --- MOTOR LÓGICO (Z3) ---
# Valor base que el motor SMT intentará alcanzar (Soft Constraint).
# Evita generar matrices de prueba con números matemáticamente triviales (ej. 1, 0, -1) 
# y fuerza la simulación de montos financieros reales.
# Nota: El motor adaptará automáticamente este valor a int (1000000) o float (1000000.x) 
# dependiendo del estado del interruptor USAR_DECIMALES.
SEMILLA_GENERACION = 1000000

# Margen de holgura (Varianza) para la generación de variables dependientes.
# Define qué tan lejos de la semilla (hacia arriba o hacia abajo) pueden fluctuar 
# los valores de las demás variables para lograr satisfacer la ecuación.
MARGEN_SEMILLA = 50000