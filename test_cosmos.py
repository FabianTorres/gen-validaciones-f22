import os
from dotenv import load_dotenv
from azure.cosmos import CosmosClient

load_dotenv()

# Inicializar cliente
URL = os.getenv("COSMOS_URI")
KEY = os.getenv("COSMOS_KEY")
DB_NAME = os.getenv("COSMOS_DB_NAME")

client = CosmosClient(URL, credential=KEY)
database = client.get_database_client(DB_NAME)
container_catalogos = database.get_container_client("Catalogos")

# 1. Insertar un parámetro de prueba (Ejemplo P01)
parametro_p01 = {
    "id": "P01",
    "tipo": "parametro",
    "valor": 834504,
    "descripcion": "Valor UTM/UTA referencia"
}

container_catalogos.upsert_item(parametro_p01)
print("✅ Parámetro P01 guardado con éxito en Cosmos DB!")

# 2. Leer un elemento por su ID y Partition Key
item = container_catalogos.read_item(item="P01", partition_key="parametro")
print(f"📄 Leído desde Azure: {item['id']} = {item['valor']}")