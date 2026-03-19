import snowflake.connector
import os
import uuid
from models.synapse import SynapseResponse, ChartConfig


class SnowflakeService:
    def __init__(self, tenant_id: str):
        self.conn = snowflake.connector.connect(
            user=os.getenv('SNOWFLAKE_USER'),
            password=os.getenv('SNOWFLAKE_PASSWORD'),
            account=os.getenv('SNOWFLAKE_ACCOUNT'),
            database=os.getenv(f'DATABASE_{tenant_id.upper()}', os.getenv('SNOWFLAKE_DATABASE', 'SYNAPSE_DB')),
            warehouse=os.getenv('SNOWFLAKE_WAREHOUSE', 'COMPUTE_WH'),
            schema=os.getenv(f'SCHEMA_{tenant_id.upper()}', 'PUBLIC')
        )

    def process_query(self, query: str, history: list = []) -> SynapseResponse:
        cursor = self.conn.cursor()
        try:
            raw_data = None
            chart_config = None
            render_type = "text"

            keywords_chart = ["ROAS", "PAUTA", "GASTO", "ESTRATEGIA", "ANALYSE", "ANALIZA", "ANALI"]
            if any(kw in query.upper() for kw in keywords_chart):
                try:
                    cursor.execute(
                        "SELECT SEMANA, ROAS, GASTO FROM FACT_MARKETING ORDER BY SEMANA DESC LIMIT 5"
                    )
                    rows = cursor.fetchall()
                    if rows:
                        raw_data = [
                            {"semana": str(row[0]), "roas": float(row[1]), "gasto": float(row[2])}
                            for row in rows
                        ]
                        render_type = "chart"
                        chart_config = ChartConfig(
                            type="bar",
                            x_axis=[d["semana"] for d in raw_data],
                            y_axis=[d["roas"] for d in raw_data],
                            metrics_label="ROAS"
                        )
                except Exception as sql_err:
                    print(f"SQL fetch warning (non-fatal): {sql_err}")

            # Build history context
            history_context = "\n".join(
                [f"User: {h['q']}\nAssistant: {h['a']}" for h in history]
            ) if history else "No previous context."

            data_context = f"DATOS REALES RECUPERADOS: {raw_data}" if raw_data else "No hay datos adicionales disponibles en Snowflake para esta consulta."

            prompt = f"""
Actúa como un Analista de Marketing Senior especializado en rendimiento de pauta digital para la plataforma Synapse by Buentipo.
Solo responde con la narrativa ejecutiva. Sé directo, enfocado en datos y orientado a la acción.

HISTORIAL DE CONVERSACIÓN:
{history_context}

CONTEXTO DE DATOS ACTUALES (Snowflake):
{data_context}

PREGUNTA O SOLICITUD DEL USUARIO:
{query}

INSTRUCCIONES:
- Si hay historial, mantén total coherencia con lo conversado anteriormente.
- Si hay datos de Snowflake, menciona cifras concretas y tendencias detectadas.
- Si el ROAS es bajo (menor a 2.0), sugiere una acción correctiva específica.
- Si es un reporte estratégico, estructura la respuesta en: Problema detectado, Evidencia de datos y Recomendación ejecutiva.
- Sé conciso pero preciso. Evita saludos genéricos.
""".strip().replace("'", "\\'")

            cursor.execute(
                f"SELECT SNOWFLAKE.CORTEX.COMPLETE('mistral-large', $${prompt}$$)"
            )
            row = cursor.fetchone()
            narrative = row[0] if row else "No se pudo generar una narrativa en este momento."

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
