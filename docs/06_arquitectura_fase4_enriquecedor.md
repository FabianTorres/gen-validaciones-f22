# 06. Arquitectura Fase 4: Motor Enriquecedor (Resolución de Dependencias)

## 1. Propósito y Visión General
La Fase 4 es un motor de **Backward Chaining** (Encadenamiento hacia atrás). Su objetivo es tomar la matriz de QA optimizada de la Fase 3 y "enriquecerla".
Dado que el bot de Selenium no puede digitar en campos de solo lectura (`autocalculado: true`), la Fase 4 toma el valor objetivo de un código autocalculado, rastrea su árbol matemático (AST) en profundidad, y delega a Z3 el cálculo de los valores "hoja" (campos digitables) exactos para que el formulario llegue automáticamente al resultado esperado.

## 2. Estructura de Directorios (Módulo `enriquecedor`)
El módulo se ubicará en `src/enriquecedor/` y se dividirá en 3 archivos principales para garantizar bajo acoplamiento (menos de 200 líneas por archivo):

*   `orquestador.py`: Director de orquesta. Recibe la matriz completa, itera sobre los casos y maneja los bloques `try/except`. Devuelve la matriz enriquecida o marca los errores.
*   `grafo_expansor.py`: El corazón algorítmico. Contiene la clase `DependencyResolver`. Su única responsabilidad es recibir un caso, aplicar el algoritmo BFS (Búsqueda en Anchura) consultando los ASTs en RAM, e inyectar las ecuaciones al motor Z3.
*   `extractor_modelo.py`: Limpiador de datos. Toma el modelo crudo de Z3, filtra las variables temporales (alfanuméricas como "Alfa"), castea los resultados reales a enteros (`int`), y los empaqueta para el JSON.

## 3. Comportamiento de Z3 en Fase 4
A diferencia de la Fase 2, donde Z3 actúa como optimizador buscando valores límite o cercanos a una semilla, en la Fase 4 Z3 opera en **Modo Inverso (Satisfiability Puro)**:
*   Se desactiva la inyección de `add_soft` (semilla objetivo).
*   Se inyectan **Hard Constraints** (restricciones duras) iniciales basadas en el caso de prueba (Ej. `[1704] == 1500`).
*   Z3 evalúa el grafo aplanado y devuelve la primera combinación válida de valores hoja.

## 4. Flujo de Datos (Pipeline de un Caso)

1.  **Detección:** El `orquestador` lee `caso.inputs`. Si encuentra códigos autocalculados (según el catálogo en RAM), los separa en una lista de *metas*. Si no hay autocalculados, el caso se omite y pasa limpio.
2.  **Instanciación:** Se crea un `MotorZ3` limpio con el flag `modo_inverso = True` y un `EvaluadorAST` nuevo.
3.  **Inyección Inicial:** Las *metas* se agregan al solver como verdades absolutas.
4.  **Aplanamiento (BFS):**
    *   Mientras haya códigos en la cola de expansión, se busca su AST en `cache.asts_latest`.
    *   El `EvaluadorAST` traduce el AST a Z3.
    *   Si la traducción revela nuevas variables autocalculadas, se añaden a la cola.
5.  **Cosecha:** Se invoca `motor.resolver_y_obtener_modelo()`.
6.  **Limpieza:** El `extractor_modelo` descarta los autocalculados del JSON original y añade los nuevos nodos hoja (como números enteros).
7.  **Manejo de Errores (UNSAT):** Si las reglas matemáticas subyacentes contradicen el valor objetivo, Z3 retornará vacío. El caso se marca con `caso.error = "Fallo de ingeniería inversa (UNSAT)"`.