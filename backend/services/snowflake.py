import snowflake.connector
import os
import uuid
from models.synapse import SynapseResponse, ChartConfig


SCHEMA = "BT_UA_MART_ANALYTICS"


class SnowflakeService:
    def __init__(self, tenant_id: str):
        self.conn = snowflake.connector.connect(
            user=os.getenv('SNOWFLAKE_USER'),
            password=os.getenv('SNOWFLAKE_PASSWORD'),
            account=os.getenv('SNOWFLAKE_ACCOUNT'),
            database=os.getenv('SNOWFLAKE_DATABASE', 'DB_BT_UA'),
            warehouse=os.getenv('SNOWFLAKE_WAREHOUSE', 'COMPUTE_WH'),
            schema=SCHEMA
        )

    def _get_relevant_context(self, cursor, query: str) -> str:
        """
        Recupera contexto relevante de las tablas RAG de Snowflake.
        Busca en REPORTES, ECOM, SOV y FORMULAS según la consulta.
        """
        context_parts = []

        # Tabla principal: REPORTES_TEXTO_RAW (reportes de marketing)
        try:
            cursor.execute(f"""
                SELECT CONTENIDO
                FROM {SCHEMA}.REPORTES_TEXTO_RAW
                LIMIT 3
            """)
            rows = cursor.fetchall()
            if rows:
                context_parts.append("=== REPORTES DE MARKETING ===")
                for row in rows:
                    context_parts.append(str(row[0])[:800])
        except Exception as e:
            print(f"REPORTES_TEXTO_RAW warning: {e}")

        # FORMULAS_MARKETING: definiciones de KPIs
        try:
            cursor.execute(f"""
                SELECT *
                FROM {SCHEMA}.FORMULAS_MARKETING
                LIMIT 10
            """)
            rows = cursor.fetchall()
            cols = [desc[0] for desc in cursor.description]
            if rows:
                context_parts.append("=== FÓRMULAS Y KPIs DE MARKETING ===")
                for row in rows:
                    row_dict = dict(zip(cols, row))
                    context_parts.append(str(row_dict))
        except Exception as e:
            print(f"FORMULAS_MARKETING warning: {e}")

        # SOV: Share of Voice (si la query lo menciona)
        if any(kw in query.upper() for kw in ["SOV", "SHARE", "VOZ", "PARTICIPACIÓN"]):
            try:
                cursor.execute(f"""
                    SELECT CONTENIDO
                    FROM {SCHEMA}.SOV_CHUNKS
                    LIMIT 3
                """)
                rows = cursor.fetchall()
                if rows:
                    context_parts.append("=== DATOS DE SHARE OF VOICE ===")
                    for row in rows:
                        context_parts.append(str(row[0])[:600])
            except Exception as e:
                print(f"SOV_CHUNKS warning: {e}")

        # ECOM: ecommerce
        if any(kw in query.upper() for kw in ["ECOM", "VENTAS", "TIENDA", "STORE", "CONVERSIÓN"]):
            try:
                cursor.execute(f"""
                    SELECT CONTENIDO
                    FROM {SCHEMA}.ECOM_TEXTO_RAW
                    LIMIT 3
                """)
                rows = cursor.fetchall()
                if rows:
                    context_parts.append("=== DATOS DE ECOMMERCE ===")
                    for row in rows:
                        context_parts.append(str(row[0])[:600])
            except Exception as e:
                print(f"ECOM_TEXTO_RAW warning: {e}")

        return "\n\n".join(context_parts) if context_parts else "No se encontraron datos relevantes en Snowflake."

    def process_query(self, query: str, history: list = []) -> SynapseResponse:
        cursor = self.conn.cursor()
        try:
            render_type = "text"
            chart_config = None
            raw_data = None

            # 1. Recuperar contexto de Snowflake (RAG)
            snowflake_context = self._get_relevant_context(cursor, query)

            # 2. Construir historial de conversación
            history_context = "\n".join(
                [f"Usuario: {h['q']}\nSynapse: {h['a']}" for h in history]
            ) if history else ""

            # 3. Construir prompt para Cortex
            prompt = f"""Eres Synapse, un Analista de Marketing Senior de la agencia Buentipo.
Tienes acceso a datos reales de Snowflake. Responde de forma ejecutiva, precisa y orientada a la acción.

{f"CONVERSACIÓN PREVIA:{chr(10)}{history_context}{chr(10)}" if history_context else ""}
DATOS DE SNOWFLAKE (contexto real):
{snowflake_context}

PREGUNTA DEL USUARIO:
{query}

INSTRUCCIONES:
- Usa los datos de Snowflake para fundamentar tu respuesta con cifras concretas cuando estén disponibles.
- Si detectas tendencias en los reportes, mencionarlas con contexto estratégico.
- Si la pregunta es de tipo estratégico, estructura tu respuesta en: Situación actual, Hallazgo clave y Recomendación.
- Sé conciso y directo. No uses saludos ni frases genéricas."""

            # Escapar $$ en el prompt para evitar conflictos SQL
            prompt_safe = prompt.replace("$$", "__DOBLEDOLAR__")

            cursor.execute(
                f"SELECT SNOWFLAKE.CORTEX.COMPLETE('mistral-large2', $${prompt_safe}$$)"
            )
            row = cursor.fetchone()
            narrative = row[0].replace("__DOBLEDOLAR__", "$$") if row else "No se pudo generar respuesta."

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
