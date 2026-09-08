"""
DEBUG b.82 - FALTA_RUT con Tipo=8 + 14D1.
SOLO LECTURA: no modifica src/, solo instancia RutProvider y loguea.
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.generador.providers.rut_provider import RutProvider

# Catalogo minimo que replica tu caso Cosmos:
# - Un tipo 8 int pero sin 14D1 (no sirve)
# - El candidato real con tipos como STRING (como viene de Cosmos/API Union[int,str])
catalogo = [
    {
        "rut": "70.000.500-3",
        "tipo_contribuyente": 8,  # int
        "subtipo": 817,  # int
        "es_formulario_universal": False,
        "atributos": ["M14A"],
    },
    {
        "rut": "59.494.257-4",
        "tipo_contribuyente": "8",  # STRING como en tu JSON de Azure
        "subtipo": "816",  # STRING como en tu JSON de Azure
        "es_formulario_universal": False,
        "atributos": ["14D1"],
    },
]

print("=== DEBUG b.82 ===")
print(f"Python {sys.version.split()[0]}")
print(f"Comparacion directa '8' != 8 -> {'8' != 8}")
print(f"Comparacion directa '816' != 816 -> {'816' != 816}")
print()

# Lo que BaseStrategy produce para tu caso (base_strategy.py:92):
tipo_req = int(8)
subtipo_req = None  # tu error dice "Subtipo: Cualquiera"
atributos_req = ["14D1"]
atributos_prohibidos = []

print(f"Requerido: tipo={tipo_req!r} ({type(tipo_req).__name__}), "
      f"subtipo={subtipo_req!r}, attrs={atributos_req}")
print()

# Traza manual por cada RUT (misma logica que rut_provider.py:36-38, sin tocarla)
for mock in catalogo:
    tipo_mock = mock.get("tipo_contribuyente")
    atr_mock = set(mock.get("atributos", []))
    check_tipo = (tipo_req is not None and tipo_mock != tipo_req)
    check_attr = not all(a in atr_mock for a in atributos_req)
    print(f"RUT {mock['rut']}: tipo_mock={tipo_mock!r} ({type(tipo_mock).__name__}) "
          f"-> descartado_por_tipo={check_tipo}, descartado_por_attr={check_attr}")

print()
provider = RutProvider(catalogo)
resultado = provider.obtener_rut(atributos_req, atributos_prohibidos, tipo_req, subtipo_req)
print(f"Resultado RutProvider.obtener_rut -> {resultado!r}")
print()

if resultado == "SIN_RUT_VALIDO":
    print("HIPOTESIS CONFIRMADA: el candidato '59.494.257-4' fue descartado solo por "
          "'8'(str) != 8(int). Es bug de comparacion estricta, no falta de datos.")
    # Demostracion de que normalizando si matchea (solo en este script, sin tocar src/)
    def norm_tipo(x):
        try:
            return int(str(x).strip())
        except (ValueError, TypeError, AttributeError):
            return x
    print(f"Con normalizacion: norm('8')={norm_tipo('8')!r} == norm(8)={norm_tipo(8)!r} "
          f"-> {norm_tipo('8') == norm_tipo(8)} (ahi SI matchearia + 14D1)")
else:
    print(f"HIPOTESIS REFUTADA: devolvio {resultado!r}, hay que buscar otra causa.")
