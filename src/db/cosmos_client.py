import os
import asyncio
from azure.cosmos.aio import CosmosClient
from dotenv import load_dotenv
import hashlib
from datetime import datetime

load_dotenv()

class CatalogoCache:
    _instancia = None
    
    # Ahora la estructura será: {2026: {"P84": 1.05}, 2027: {"P84": 1.10}}
    parametros = {}
    ruts = {}
    codigos = {}
    mensajes = {}
    asts_latest = {}

    def __new__(cls):
        if cls._instancia is None:
            cls._instancia = super(CatalogoCache, cls).__new__(cls)
        return cls._instancia

    async def cargar_desde_cosmos(self):
        print("🔄 Sincronizando catálogos de todos los años desde Azure Cosmos DB...")
        URI = os.getenv("COSMOS_URI")
        KEY = os.getenv("COSMOS_KEY")
        DB_NAME = os.getenv("COSMOS_DB_NAME")

        async with CosmosClient(URI, credential=KEY) as client:
            db = client.get_database_client(DB_NAME)
            container = db.get_container_client("Catalogos")

            self.parametros.clear()
            self.codigos.clear()
            self.ruts.clear()
            self.mensajes.clear()

            # Consultamos la base de datos completa de un solo viaje
            async for item in container.query_items(query="SELECT * FROM c"):
                at = item.get("at")
                tipo = item.get("tipo")
                if not at or not tipo: continue
                
                # Inicializamos el año en la RAM si no existe
                if at not in self.parametros: self.parametros[at] = {}
                if at not in self.codigos: self.codigos[at] = {}
                if at not in self.ruts: self.ruts[at] = []
                if at not in self.mensajes: self.mensajes[at] = {}

                if tipo == 'parametro':
                    self.parametros[at][item["id"]] = item.get("valor", 0.0)
                elif tipo == 'codigo':
                    self.codigos[at][item["id"]] = {
                        "signo_permitido": item.get("signo_permitido", "+"),
                        "autocalculado": item.get("autocalculado", False),
                        "descripcion": item.get("descripcion", "")
                    }
                elif tipo == 'rut':
                    self.ruts[at].append(item)
                elif tipo == 'mensaje':
                    self.mensajes[at][item["id"]] = item.get("descripcion", "")
            
        print(f"✅ Memoria multi-año lista y cargada en RAM.")

    async def actualizar_parametro(self, id_param: str, nuevo_valor: float, at: int):
        URI = os.getenv("COSMOS_URI")
        KEY = os.getenv("COSMOS_KEY")
        DB_NAME = os.getenv("COSMOS_DB_NAME")

        async with CosmosClient(URI, credential=KEY) as client:
            db = client.get_database_client(DB_NAME)
            container = db.get_container_client("Catalogos")
            
            try:
                item = await container.read_item(item=id_param, partition_key=["parametro", at])
            except:
                item = {"id": id_param, "tipo": "parametro", "at": at}
                
            item["valor"] = nuevo_valor
            await container.upsert_item(item)
            
        if at not in self.parametros: self.parametros[at] = {}
        self.parametros[at][id_param] = nuevo_valor

    async def carga_masiva_catalogos(self, items: list):
        URI = os.getenv("COSMOS_URI")
        KEY = os.getenv("COSMOS_KEY")
        DB_NAME = os.getenv("COSMOS_DB_NAME")

        async with CosmosClient(URI, credential=KEY) as client:
            db = client.get_database_client(DB_NAME)
            container = db.get_container_client("Catalogos")
            
            for item in items:
                await container.upsert_item(item)
                
                tipo = item.get("tipo")
                id_item = item.get("id")
                at = item.get("at")
                
                if at not in self.parametros: self.parametros[at] = {}
                if at not in self.codigos: self.codigos[at] = {}
                if at not in self.ruts: self.ruts[at] = []
                if at not in self.mensajes: self.mensajes[at] = {}
                
                if tipo == "parametro":
                    self.parametros[at][id_item] = item.get("valor", 0.0)
                elif tipo == "codigo":
                    self.codigos[at][id_item] = {
                        "signo_permitido": item.get("signo_permitido", "+"),
                        "autocalculado": item.get("autocalculado", False)
                    }
                elif tipo == "mensaje":
                    self.mensajes[at][id_item] = item.get("descripcion", "")
                elif tipo == "rut":
                    self.ruts[at] = [r for r in self.ruts[at] if r.get("id") != id_item]
                    self.ruts[at].append(item)

    async def cargar_asts_masivos(self, at: int):
        print(f"🚀 Descargando árboles AST del AT {at} a la memoria RAM...")
        URI = os.getenv("COSMOS_URI")
        KEY = os.getenv("COSMOS_KEY")
        DB_NAME = os.getenv("COSMOS_DB_NAME")

        async with CosmosClient(URI, credential=KEY) as client:
            db = client.get_database_client(DB_NAME)
            cont_reglas = db.get_container_client("Reglas")

            query = f"SELECT c.id_validacion, c.version, c.codigo_objetivo, c.ast FROM c WHERE IS_DEFINED(c.codigo_objetivo) AND c.codigo_objetivo != null AND c.at = {at}"
            
            if at not in self.asts_latest:
                self.asts_latest[at] = {}
            self.asts_latest[at].clear()
            
            diccionario_temporal = {}

            async for item in cont_reglas.query_items(query=query):
                cod = item["codigo_objetivo"]
                if cod not in diccionario_temporal or item["version"] > diccionario_temporal[cod]["version"]:
                    diccionario_temporal[cod] = item

            for cod, datos in diccionario_temporal.items():
                self.asts_latest[at][cod] = datos["ast"]
                
        print(f"🧠 Memoria AST Masiva lista: {len(self.asts_latest[at])} árboles cacheados para el AT {at}.")
        return len(self.asts_latest[at])

class RepositorioHistorial:
    
    def _generar_hash(self, texto: str) -> str:
        texto_limpio = " ".join(texto.split())
        return hashlib.sha256(texto_limpio.encode('utf-8')).hexdigest()

    async def guardar_regla_y_matriz(self, id_val: str, formula: str, texto_fmt: str, casos: list, at: int,version_documento: str = "1.0", codigo_objetivo: str = None, ast_json: dict = None) -> int:
        URI = os.getenv("COSMOS_URI")
        KEY = os.getenv("COSMOS_KEY")
        DB_NAME = os.getenv("COSMOS_DB_NAME")

        async with CosmosClient(URI, credential=KEY) as client:
            db = client.get_database_client(DB_NAME)
            cont_reglas = db.get_container_client("Reglas")
            cont_matrices = db.get_container_client("MatricesQA")

            # Consulta parametrizada limpia
            query = "SELECT * FROM c WHERE c.id_validacion = @id_val AND c.at = @at"
            parametros = [
                {"name": "@id_val", "value": id_val},
                {"name": "@at", "value": at}
            ]
            
            items = [item async for item in cont_reglas.query_items(
                query=query, 
                parameters=parametros
            )]
            
            nueva_version = 1
            nuevo_hash = self._generar_hash(f"{texto_fmt}_{version_documento}")

            if items:
                ultima_regla = max(items, key=lambda x: x.get("version", 1))
                if ultima_regla.get("hash_formula") == nuevo_hash:
                    nueva_version = ultima_regla["version"]
                else:
                    nueva_version = ultima_regla["version"] + 1

            id_registro = f"{id_val}-v{nueva_version}"
            fecha_actual = datetime.utcnow().isoformat()

            doc_regla = {
                "id": id_registro,
                "id_validacion": id_val,
                "at": at,
                "version": nueva_version,
                "version_documento": version_documento,
                "codigo_objetivo": codigo_objetivo,
                "formula_cruda": formula,
                "texto_formateado": texto_fmt,
                "hash_formula": nuevo_hash,
                "ast": ast_json,
                "fecha_actualizacion": fecha_actual
            }
            await cont_reglas.upsert_item(doc_regla)

            doc_matriz = {
                "id": id_registro,
                "id_validacion": id_val,
                "at": at,
                "version": nueva_version,
                "version_documento": version_documento,
                "fecha_generacion": fecha_actual,
                "total_casos": len(casos),
                "casos": casos
            }
            await cont_matrices.upsert_item(doc_matriz)

            return nueva_version

    async def buscar_dependencias_por_codigo(self, codigo: str, at: int) -> list:
        URI = os.getenv("COSMOS_URI")
        KEY = os.getenv("COSMOS_KEY")
        DB_NAME = os.getenv("COSMOS_DB_NAME")

        async with CosmosClient(URI, credential=KEY) as client:
            db = client.get_database_client(DB_NAME)
            cont_reglas = db.get_container_client("Reglas")

            query = """
                SELECT c.id_validacion, c.version, c.texto_formateado, c.fecha_actualizacion, c.ast 
                FROM c 
                WHERE c.codigo_objetivo = @codigo_buscado AND c.at = @at
            """
            parametros = [
                {"name": "@codigo_buscado", "value": codigo},
                {"name": "@at", "value": at}
            ]
            
            resultados = []
            async for item in cont_reglas.query_items(query=query, parameters=parametros):
                resultados.append(item)
                
            return resultados

    async def buscar_dependencias_batch(self, codigos: list, at: int) -> list:
        URI = os.getenv("COSMOS_URI")
        KEY = os.getenv("COSMOS_KEY")
        DB_NAME = os.getenv("COSMOS_DB_NAME")

        async with CosmosClient(URI, credential=KEY) as client:
            db = client.get_database_client(DB_NAME)
            cont_reglas = db.get_container_client("Reglas")

            codigos_str = ", ".join([f"'{c}'" for c in codigos])
            
            query = f"""
                SELECT c.id_validacion, c.version, c.texto_formateado, c.codigo_objetivo, c.ast 
                FROM c 
                WHERE c.codigo_objetivo IN ({codigos_str}) AND c.at = {at}
            """
            
            resultados_brutos = []
            async for item in cont_reglas.query_items(query=query):
                resultados_brutos.append(item)
                
            ultimas_versiones = {}
            for item in resultados_brutos:
                cod = item["codigo_objetivo"]
                if cod not in ultimas_versiones or item["version"] > ultimas_versiones[cod]["version"]:
                    ultimas_versiones[cod] = item
                    
            return list(ultimas_versiones.values())

    async def obtener_historial_metadatos(self, at: int) -> list:
        """Obtiene solo los metadatos ligeros para construir la tabla del frontend."""
        URI = os.getenv("COSMOS_URI")
        KEY = os.getenv("COSMOS_KEY")
        DB_NAME = os.getenv("COSMOS_DB_NAME")

        async with CosmosClient(URI, credential=KEY) as client:
            db = client.get_database_client(DB_NAME)
            cont_matrices = db.get_container_client("MatricesQA")

            # Proyección SQL: Solo pedimos los 4 campos exactos que necesita la UI
            query = """
                SELECT c.id_validacion, c.version, c.version_documento, c.fecha_generacion AS fecha, c.total_casos 
                FROM c 
                WHERE c.at = @at
            """
            parametros = [{"name": "@at", "value": at}]
            
            resultados = []
            async for item in cont_matrices.query_items(query=query, parameters=parametros):
                resultados.append(item)
                
            return resultados

    async def obtener_lote_casos(self, at: int, prefijo: str) -> list:
        """Busca validaciones por prefijo, extrae la última versión y fusiona todos los casos."""
        URI = os.getenv("COSMOS_URI")
        KEY = os.getenv("COSMOS_KEY")
        DB_NAME = os.getenv("COSMOS_DB_NAME")

        async with CosmosClient(URI, credential=KEY) as client:
            db = client.get_database_client(DB_NAME)
            cont_matrices = db.get_container_client("MatricesQA")

            # Buscamos todo lo que empiece con el prefijo (ej. 'a.')
            query = """
                SELECT c.id_validacion, c.version, c.casos 
                FROM c 
                WHERE c.at = @at AND STARTSWITH(c.id_validacion, @prefijo)
            """
            parametros = [
                {"name": "@at", "value": at},
                {"name": "@prefijo", "value": prefijo}
            ]
            
            resultados_brutos = []
            async for item in cont_matrices.query_items(query=query, parameters=parametros):
                resultados_brutos.append(item)
                
            # Filtramos en Python para quedarnos solo con la versión más alta de cada regla
            ultimas_versiones = {}
            for item in resultados_brutos:
                cod = item["id_validacion"]
                if cod not in ultimas_versiones or item["version"] > ultimas_versiones[cod]["version"]:
                    ultimas_versiones[cod] = item
                    
            # Aplanamos todos los casos en una sola lista gigante
            casos_totales = []
            for item in ultimas_versiones.values():
                casos_totales.extend(item.get("casos", []))
                
            return casos_totales

    async def obtener_matriz_especifica(self, id_val: str, version: int, at: int) -> list:
        """Busca y retorna los casos de una versión específica de una validación."""
        URI = os.getenv("COSMOS_URI")
        KEY = os.getenv("COSMOS_KEY")
        DB_NAME = os.getenv("COSMOS_DB_NAME")

        async with CosmosClient(URI, credential=KEY) as client:
            db = client.get_database_client(DB_NAME)
            cont_matrices = db.get_container_client("MatricesQA")

            query = """
                SELECT c.casos 
                FROM c 
                WHERE c.id_validacion = @id_val 
                AND c.version = @version 
                AND c.at = @at
            """
            parametros = [
                {"name": "@id_val", "value": id_val},
                {"name": "@version", "value": version},
                {"name": "@at", "value": at}
            ]
            
            async for item in cont_matrices.query_items(query=query, parameters=parametros):
                return item.get("casos", [])
                
            return None # Si no encuentra nada

    async def obtener_detalle_completo(self, id_val: str, version: int, at: int) -> dict:
        """
        Busca los metadatos en 'Reglas' y los casos en 'MatricesQA' 
        y los fusiona en un solo diccionario para la Vista de Detalle.
        """
        URI = os.getenv("COSMOS_URI")
        KEY = os.getenv("COSMOS_KEY")
        DB_NAME = os.getenv("COSMOS_DB_NAME")

        async with CosmosClient(URI, credential=KEY) as client:
            db = client.get_database_client(DB_NAME)
            cont_reglas = db.get_container_client("Reglas")
            cont_matrices = db.get_container_client("MatricesQA")

            parametros = [
                {"name": "@id_val", "value": id_val},
                {"name": "@version", "value": version},
                {"name": "@at", "value": at}
            ]

            # 1. Obtenemos los textos de la fórmula
            query_reglas = """
                SELECT c.id_validacion, c.version, c.version_documento, c.formula_cruda, c.texto_formateado 
                FROM c 
                WHERE c.id_validacion = @id_val AND c.version = @version AND c.at = @at
            """
            
            detalle = None
            async for item in cont_reglas.query_items(query=query_reglas, parameters=parametros):
                detalle = item
                break # Solo necesitamos el primero
                
            if not detalle:
                return None
                
            # 2. Obtenemos los casos
            query_matrices = """
                SELECT c.casos 
                FROM c 
                WHERE c.id_validacion = @id_val AND c.version = @version AND c.at = @at
            """
            
            casos_encontrados = []
            async for item in cont_matrices.query_items(query=query_matrices, parameters=parametros):
                casos_encontrados = item.get("casos", [])
                break
                
            # 3. Fusionamos y retornamos
            detalle["casos"] = casos_encontrados
            return detalle