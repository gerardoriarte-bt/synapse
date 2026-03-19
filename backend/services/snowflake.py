import snowflake.connector
import os
import uuid
from models.synapse import SynapseResponse, ChartConfig

class SnowflakeService:
    def __init__(self, tenant_id: str):
        self.tenant_id = tenant_id
        # Configuración Multi-tenant dinámica basada en esquema del cliente
        self.conn = snowflake.connector.connect(
            user=os.getenv('SNOWFLAKE_USER'),
            password=os.getenv('SNOWFLAKE_PASSWORD'),
            account=os.getenv('SNOWFLAKE_ACCOUNT'),
            warehouse=os.getenv('SNOWFLAKE_WAREHOUSE'),
            database=os.getenv('SNOWFLAKE_DATABASE'),
            schema=os.getenv(f'SCHEMA_{tenant_id.upper()}', 'PUBLIC')
        )

    def process_query(self, query: str) -> SynapseResponse:
        cursor = self.conn.cursor()
        try:
            # 1. Recuperación de Datos Reales (Data Fetching)
            raw_data = None
            chart_config = None
            render_type = "text"

            # Simulación de detección de intención (Keyword check rápido)
            if any(keyword in query.upper() for keyword in ["ROAS", "PAUTA", "GASTO"]):
                # SQL Real en tu tabla (Asumiendo FACT_MARKETING según backend.md)
                cursor.execute("SELECT SEMANA, ROAS, GASTO FROM FACT_MARKETING ORDER BY SEMANA DESC LIMIT 5")
                rows = cursor.fetchall()
                
                # Transformamos a JSON plano para que la IA lo entienda
                raw_data = [{"semana": str(row[0]), "roas": float(row[1]), "gasto": float(row[2])} for row in rows]
                render_type = "chart"
                chart_config = ChartConfig(
                    type="bar",
                    x_axis=[d["semana"] for d in raw_data],
                    y_axis=[d["roas"] for d in raw_data],
                    metrics_label="ROAS"
                )

            # 2. Análisis del Datos con Cortex AI (Analytic Reasoning)
            # Pasamos los DATOS REALES como contexto al modelo para que la respuesta no sea alucinada.
            data_context = f"DATOS REALES RECUPERADOS: {raw_data}" if raw_data else "Sin datos adicionales detectados."
            
            prompt = f"""
            Actúa como un Analista de Marketing Senior en el equipo de Synapse.
            CONTEXTO DE DATOS: {data_context}
            PREGUNTA DEL USUARIO: {query}
            
            INSTRUCCIONES:
            - Si hay datos disponibles, descríbelos y destaca tendencias o anomalías.
            - Si el ROAS es bajo (menor a 2.0), sugiere una acción correctiva.
            - Sé ejecutivo, directo y evita introducciones genéricas.
            - Tu respuesta poblará el campo 'narrative' de una UI avanzada.
            """
            
            cursor.execute(f"SELECT SNOWFLAKE.CORTEX.COMPLETE('mistral-large', '{prompt}')")
            narrative = cursor.fetchone()[0]

            return SynapseResponse(
                response_id=str(uuid.uuid4()),
                narrative=narrative,
                render_type=render_type,
                chart_config=chart_config,
                raw_data=raw_data
            )
        finally:
            cursor.close()
            self.conn.close()
