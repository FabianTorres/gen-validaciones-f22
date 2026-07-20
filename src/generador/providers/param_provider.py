import os
import z3

class ParamProvider:
    def __init__(self, ruta_txt="data/catalogo_parametros.txt"):
        self.ruta_txt = ruta_txt
        self.parametros = self._cargar_datos()

    def _cargar_datos(self):
        parametros = {}
        
        if not os.path.exists(self.ruta_txt):
            print(f"⚠️ Advertencia: No se encontró el catálogo de parámetros en {self.ruta_txt}")
            return parametros

        with open(self.ruta_txt, 'r', encoding='utf-8') as f:
            for linea in f:
                linea = linea.strip()
                
                # Ignorar encabezados o líneas vacías
                if not linea or linea.startswith("PARAMETRO"):
                    continue
                
                partes = linea.split('|')
                if len(partes) >= 2:
                    nombre = partes[0].strip().upper()
                    # Reemplazamos la coma por punto para que float() de Python no colapse
                    valor_str = partes[1].strip().replace(',', '.')
                    
                    try:
                        parametros[nombre] = float(valor_str)
                    except ValueError:
                        print(f"⚠️ Advertencia: Valor inválido para el parámetro {nombre}: '{valor_str}'")
                        parametros[nombre] = 0.0
                        
        return parametros

    def inyectar_en_motor(self, motor_z3):
        """
        Inyecta todos los parámetros blindados contra errores tipográficos.
        """
        for nombre, valor in self.parametros.items():
            motor_z3.variables_memoria[nombre] = z3.RealVal(valor)