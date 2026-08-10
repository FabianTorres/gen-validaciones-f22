import os
import json
import asyncio
from azure.cosmos.aio import CosmosClient
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

URI = os.getenv("COSMOS_URI")
KEY = os.getenv("COSMOS_KEY")
DB_NAME = os.getenv("COSMOS_DB_NAME", "db-f22-generador")
CONT_CATALOGOS = "Catalogos"
ANO_TRIBUTARIO = 2026

# --- PARSERS PERSONALIZADOS PARA TUS DATOS ---

def parsear_codigos(ruta):
    items = []
    try:
        with open(ruta, "r", encoding="utf-8") as f:
            lineas = f.readlines()
            for linea in lineas[1:]: # Saltamos la cabecera
                if not linea.strip(): continue
                partes = linea.split("|")
                if len(partes) >= 2:
                    items.append({
                        "id": partes[0].strip(),
                        "signo_permitido": partes[1].strip(),
                        "descripcion": partes[2].strip() if len(partes) > 2 else ""
                    })
    except Exception as e: print(f"Error leyendo {ruta}: {e}")
    return items

def parsear_mensajes(ruta):
    items = []
    try:
        with open(ruta, "r", encoding="utf-8") as f:
            lineas = f.readlines()
            for linea in lineas[1:]:
                if not linea.strip(): continue
                partes = linea.split("|")
                if len(partes) >= 2:
                    items.append({
                        "id": partes[0].strip(),
                        "descripcion": partes[1].strip()
                    })
    except Exception as e: print(f"Error leyendo {ruta}: {e}")
    return items

def parsear_parametros(ruta):
    items = []
    try:
        with open(ruta, "r", encoding="utf-8") as f:
            lineas = f.readlines()
            for linea in lineas[1:]:
                if not linea.strip(): continue
                partes = linea.split("|")
                if len(partes) >= 2:
                    # Convertir la coma a punto para que Python entienda el decimal
                    valor_str = partes[1].strip().replace(",", ".")
                    try:
                        valor_num = float(valor_str)
                    except ValueError:
                        valor_num = 0.0
                    
                    items.append({
                        "id": partes[0].strip(),
                        "valor": valor_num,
                        "descripcion": partes[2].strip() if len(partes) > 2 else ""
                    })
    except Exception as e: print(f"Error leyendo {ruta}: {e}")
    return items

def parsear_ruts(ruta):
    try:
        with open(ruta, "r", encoding="utf-8") as f:
            data = json.load(f)
            # Cosmos DB exige el campo 'id', copiamos el rut ahí
            for item in data:
                item["id"] = item["rut"]
                
                # SOLUCIÓN: Renombramos 'tipo' a 'tipo_contribuyente' 
                # para evitar colisión con la Partition Key de Cosmos DB
                if "tipo" in item:
                    item["tipo_contribuyente"] = item.pop("tipo")
                    
            return data
    except Exception as e: 
        print(f"Error leyendo {ruta}: {e}")
        return []

# --- MOTOR DE MIGRACIÓN ---

async def migrar_datos():
    print(f"🚀 Iniciando migración a Cosmos DB (AT {ANO_TRIBUTARIO})...")

    # 1. Extraemos los datos locales
    datos_codigos = parsear_codigos("./data/catalogo_codigos.txt")
    datos_mensajes = parsear_mensajes("./data/catalogo_mensajes.txt")
    datos_parametros = parsear_parametros("./data/catalogo_parametros.txt")
    datos_ruts = parsear_ruts("./data/mock_ruts_qa.json")

    async with CosmosClient(URI, credential=KEY) as client:
        db = client.get_database_client(DB_NAME)
        container = db.get_container_client(CONT_CATALOGOS)

        async def procesar_y_subir(items, tipo_esperado):
            if not items: return
            contador = 0
            for item in items:
                # INYECCIÓN OBLIGATORIA PARA PARTICIÓN JERÁRQUICA
                item["tipo"] = tipo_esperado
                item["at"] = ANO_TRIBUTARIO 
                
                await container.upsert_item(item)
                contador += 1
            print(f"✅ Subidos {contador} registros de '{tipo_esperado}'.")

        # 2. Subimos a Azure
        print("-" * 40)
        await procesar_y_subir(datos_codigos, "codigo")
        await procesar_y_subir(datos_mensajes, "mensaje")
        await procesar_y_subir(datos_parametros, "parametro")
        await procesar_y_subir(datos_ruts, "rut")
        print("-" * 40)

    print("🎉 ¡Migración completada exitosamente!")

if __name__ == "__main__":
    asyncio.run(migrar_datos())