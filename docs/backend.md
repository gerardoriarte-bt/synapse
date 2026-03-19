PROMPT PARA EL BACKEND (Python / FastAPI)
Nota tuya, Ger: Te sugiero Python con FastAPI para el backend porque es el estándar rey para manejar datos, IA y conexiones con Snowflake.

Cópialo así:

Rol: Actúa como un Arquitecto de Backend y Data Engineer Senior experto en Python, FastAPI, y seguridad en bases de datos.

Objetivo: Construir la API Gateway de "Synapse", que actuará como un puente seguro entre un Frontend en React y un Data Warehouse en Snowflake (usando Snowflake Cortex AI).

Regla Crítica de Seguridad: El backend NUNCA debe exponer credenciales de Snowflake al frontend. Debe operar bajo una arquitectura Multi-Tenant, aislando las consultas según el cliente.

Requerimientos de la API:

Endpoint Principal: Crea un endpoint POST /api/synapse/ask que reciba un payload con {"query": "string", "tenant_id": "string"}. (Asume que en producción el tenant_id vendrá decodificado de un token JWT en los headers, pero déjalo explícito por ahora para pruebas).

Connection Manager (Mock): Crea una clase o servicio SnowflakeService que tome el tenant_id para configurar el esquema (SCHEMA) correcto de conexión. Por ahora, mockea la conexión real a Snowflake, pero deja la estructura lista (usando el conector snowflake-connector-python).

Estructurador de Respuesta (El Contrato):
Independientemente de lo que responda el modelo de IA o la base de datos, el backend TIENE que formatear la respuesta para cumplir estrictamente con este contrato JSON Pydantic:

Python
class ChartConfig(BaseModel):
    type: str # "bar", "line", "donut"
    x_axis: list
    y_axis: list
    metrics_label: str

class SynapseResponse(BaseModel):
    response_id: str
    narrative: str
    render_type: str # "text", "chart", "table"
    chart_config: Optional[ChartConfig] = None
    raw_data: Optional[list[dict]] = None
Flujo Ficticio (Para pruebas del front):
Dentro del endpoint, si el usuario pregunta algo con la palabra "ROAS", devuelve un objeto SynapseResponse mockeado con un render_type="chart", un chart_config válido para un gráfico de barras, y raw_data. Si pregunta otra cosa, devuelve un render_type="text".

Genera el código limpio, usando inyección de dependencias de FastAPI y buenas prácticas de manejo de errores (HTTP 500, HTTP 401 si falla el tenant).