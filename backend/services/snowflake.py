import snowflake.connector
import os
import uuid
from typing import Optional, Union, List, Tuple, Dict
from models.synapse import SynapseResponse, ChartConfig

RAG_DB     = "DB_BT_UA"
RAG_SCHEMA = "BT_UA_MART_ANALYTICS"
ADS_DB     = "UA_ECOMM"


class SnowflakeService:
    def __init__(self, tenant_id: str):
        token = os.getenv('SNOWFLAKE_TOKEN', '').strip()
        user = os.getenv('SNOWFLAKE_USER', '').strip().upper()
        account = os.getenv('SNOWFLAKE_ACCOUNT', '').strip().upper()
        
        conn_params = {
            "user": user,
            "account": account,
            "database": os.getenv('SNOWFLAKE_DATABASE', RAG_DB),
            "warehouse": os.getenv('SNOWFLAKE_WAREHOUSE', 'COMPUTE_WH').strip().upper(),
            "schema": RAG_SCHEMA,
            "role": "SYSADMIN", # Forzamos el rol que vimos en la captura
            "client_prefetch_mfa_token": False,
            "client_request_mfa_token": False
        }

        if token:
            print(f"[Snowflake] Connecting via Token (User: {user}, Account: {account})")
            conn_params["authenticator"] = "PROGRAMMATIC_ACCESS_TOKEN"
            conn_params["token"] = token
        else:
            print("[Snowflake] Connecting via Password")
            conn_params["password"] = os.getenv('SNOWFLAKE_PASSWORD')

        self.conn = snowflake.connector.connect(**conn_params)

    # ------------------------------------------------------------------
    # DATOS DE PAUTA REAL (UA_ECOMM)
    # ------------------------------------------------------------------

    def _get_platform_metrics(self, cursor, platform: str) -> List[Dict]:
        """Obtiene métricas reales con ROAS calculado (CONVERSION_VALUE / COST)."""
        try:
            # Google Ads usa DATE, COST, CONVERSION_VALUE, CLICKS, CONVERSIONS
            # Facebook y Criteo presumiblemente tienen columnas similares
            cursor.execute(f"""
                SELECT
                    DATE,
                    CAMPAIGN_ID,
                    SUM(COST)                                          AS GASTO,
                    SUM(CONVERSIONS)                                   AS CONVERSIONES,
                    SUM(CONVERSION_VALUE)                              AS REVENUE,
                    SUM(CLICKS)                                        AS CLICKS,
                    SUM(IMPRESSIONS)                                   AS IMPRESIONES,
                    ROUND(
                        SUM(CONVERSION_VALUE) / NULLIF(SUM(COST), 0), 2
                    )                                                  AS ROAS
                FROM {ADS_DB}.PUBLIC.{platform}_ADS_METRICAS
                GROUP BY DATE, CAMPAIGN_ID
                ORDER BY DATE DESC
                LIMIT 30
            """)
            rows = cursor.fetchall()
            cols = [desc[0] for desc in cursor.description]
            return [dict(zip(cols, row)) for row in rows] if rows else []
        except Exception as e:
            print(f"{platform} metrics warning: {e}")
            return []

    def _get_sales_data(self, cursor) -> List[Dict]:
        """Obtiene datos de ventas reales desde UA_ECOMM."""
        try:
            cursor.execute(f"""
                SELECT *
                FROM {ADS_DB}.PUBLIC.VENTAS_POR_PLATAFORMA_Y_ID_CLIENTE
                ORDER BY 1 DESC
                LIMIT 10
            """)
            rows = cursor.fetchall()
            cols = [desc[0] for desc in cursor.description]
            return [dict(zip(cols, row)) for row in rows] if rows else []
        except Exception as e:
            print(f"VENTAS warning: {e}")
            return []

    def _build_ads_context(self, cursor, query: str) -> Tuple[str, List, Optional[ChartConfig]]:
        """Construye contexto de datos de pauta con detección de plataforma."""
        context_parts = []
        raw_data = []
        chart_config = None

        # Detectar plataformas relevantes en la consulta
        platforms = []
        if any(k in query.upper() for k in ["GOOGLE", "SEM", "SEARCH"]):
            platforms.append("GOOGLE")
        if any(k in query.upper() for k in ["FACEBOOK", "META", "FB", "INSTAGRAM"]):
            platforms.append("FACEBOOK")
        if any(k in query.upper() for k in ["CRITEO", "RETARGETING", "DISPLAY"]):
            platforms.append("CRITEO")

        # Si no se detecta plataforma o pregunta por ROAS general, traer todas
        if not platforms or any(k in query.upper() for k in ["ROAS", "GENERAL", "TODAS", "RESUMEN", "ESTRATEG"]):
            platforms = ["GOOGLE", "FACEBOOK", "CRITEO"]

        for platform in platforms:
            metrics = self._get_platform_metrics(cursor, platform)
            if metrics:
                context_parts.append(f"=== {platform} ADS (últimas filas) ===")
                context_parts.append(str(metrics[:3]))
                raw_data.extend(metrics[:5])

        # Construir chart_config con columnas exactas: DATE y ROAS
        if raw_data and len(raw_data) >= 2:
            # Agrupar por fecha (puede haber múltiples campañas por fecha)
            from collections import defaultdict
            date_roas: dict = defaultdict(list)
            for row in raw_data:
                date_val = str(row.get("DATE", ""))
                roas_val = row.get("ROAS")
                if date_val and roas_val is not None:
                    date_roas[date_val].append(float(roas_val))

            if date_roas:
                sorted_dates = sorted(date_roas.keys())[-14:]  # últimas 2 semanas
                avg_roas = [round(sum(date_roas[d]) / len(date_roas[d]), 2) for d in sorted_dates]
                chart_config = ChartConfig(
                    type="line",
                    x_axis=sorted_dates,
                    y_axis=avg_roas,
                    metrics_label="ROAS (CONVERSION_VALUE / COST)"
                )

        # Ventas reales
        if any(k in query.upper() for k in ["VENTA", "REVENUE", "INGRESO", "ECOMMERCE", "ROAS", "ESTRATEG"]):
            sales = self._get_sales_data(cursor)
            if sales:
                context_parts.append("=== VENTAS POR PLATAFORMA ===")
                context_parts.append(str(sales[:3]))
                if not raw_data:
                    raw_data = sales

        return "\n\n".join(context_parts), raw_data, chart_config

    # ------------------------------------------------------------------
    # CONTEXTO RAG (DB_BT_UA)
    # ------------------------------------------------------------------

    def _get_rag_context(self, cursor, query: str) -> str:
        """Recupera contexto de los reportes y fórmulas de marketing (RAG)."""
        parts = []

        # FORMULAS_MARKETING siempre
        try:
            cursor.execute(f"SELECT * FROM {RAG_DB}.{RAG_SCHEMA}.FORMULAS_MARKETING LIMIT 8")
            rows = cursor.fetchall()
            cols = [desc[0] for desc in cursor.description]
            if rows:
                parts.append("=== FÓRMULAS Y KPIs DEFINIDOS ===")
                parts.append(str([dict(zip(cols, r)) for r in rows]))
        except Exception as e:
            print(f"FORMULAS warning: {e}")

        # REPORTES_TEXTO_RAW si es consulta estratégica o de reportes
        if any(k in query.upper() for k in ["REPORTE", "ESTRATEG", "ANALIZ", "ROAS", "RENDIMIENTO", "INSIGHT"]):
            try:
                cursor.execute(f"SELECT * FROM {RAG_DB}.{RAG_SCHEMA}.REPORTES_TEXTO_RAW LIMIT 3")
                rows = cursor.fetchall()
                cols = [desc[0] for desc in cursor.description]
                if rows:
                    parts.append("=== REPORTES DE MARKETING ===")
                    for r in rows:
                        parts.append(str(dict(zip(cols, r)))[:600])
            except Exception as e:
                print(f"REPORTES warning: {e}")

        # SOV
        if any(k in query.upper() for k in ["SOV", "SHARE", "PARTICIPACIÓN", "MERCADO"]):
            try:
                cursor.execute(f"SELECT * FROM {RAG_DB}.{RAG_SCHEMA}.SOV_CHUNKS LIMIT 3")
                rows = cursor.fetchall()
                cols = [desc[0] for desc in cursor.description]
                if rows:
                    parts.append("=== SHARE OF VOICE ===")
                    for r in rows:
                        parts.append(str(dict(zip(cols, r)))[:500])
            except Exception as e:
                print(f"SOV warning: {e}")

        return "\n\n".join(parts) if parts else ""

    # ------------------------------------------------------------------
    # PROCESO PRINCIPAL
    # ------------------------------------------------------------------

    def process_query(self, query: str, history: List = []) -> SynapseResponse:
        cursor = self.conn.cursor()
        try:
            # 1. Datos reales de pauta (UA_ECOMM)
            ads_context, raw_data, chart_config = self._build_ads_context(cursor, query)
            render_type = "chart" if chart_config else ("table" if raw_data else "text")

            # 2. Contexto RAG de reportes y fórmulas
            rag_context = self._get_rag_context(cursor, query)

            # 3. Historial conversacional
            history_context = "\n".join(
                [f"Usuario: {h['q']}\nSynapse: {h['a']}" for h in history]
            ) if history else ""

            # 4. Prompt para Cortex
            prompt = f"""Eres Synapse, Analista de Marketing Senior de la agencia Buentipo.
Tienes acceso a datos reales de Snowflake de campañas digitales en Google, Facebook y Criteo.
Responde de forma ejecutiva, directa y orientada a la acción estratégica.

{f"HISTORIAL:{chr(10)}{history_context}{chr(10)}" if history_context else ""}
{f"DATOS DE PAUTA REAL (Snowflake UA_ECOMM):{chr(10)}{ads_context}{chr(10)}" if ads_context else ""}
{f"CONTEXTO Y FÓRMULAS (Snowflake DB_BT_UA):{chr(10)}{rag_context}{chr(10)}" if rag_context else ""}
PREGUNTA: {query}

INSTRUCCIONES:
- Usa cifras concretas de los datos cuando estén disponibles.
- Si hay datos de ROAS, compara plataformas y destaca la más eficiente.
- Si es consulta estratégica: Situación actual → Hallazgo clave → Recomendación ejecutiva.
- Respuesta concisa, sin saludos."""

            prompt_safe = prompt.replace("$$", "__DD__")
            cursor.execute(
                f"SELECT SNOWFLAKE.CORTEX.COMPLETE('mistral-large2', $${prompt_safe}$$)"
            )
            row = cursor.fetchone()
            narrative = row[0].replace("__DD__", "$$") if row else "No se pudo generar respuesta."

            return SynapseResponse(
                response_id=str(uuid.uuid4()),
                narrative=narrative,
                render_type=render_type,
                chart_config=chart_config,
                raw_data=raw_data if raw_data else None
            )
        finally:
            cursor.close()
            self.conn.close()
