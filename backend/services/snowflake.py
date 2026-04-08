import snowflake.connector
import os
import uuid
from typing import Optional, Union, List, Tuple, Dict
from models.synapse import SynapseResponse, ChartConfig

RAG_DB     = "DB_BT_UA"
RAG_SCHEMA = "BT_UA_MART_ANALYTICS"
ADS_DB     = "UA_DATABASE"


class SnowflakeService:
    def __init__(self, tenant_id: str):
        token = os.getenv('SNOWFLAKE_TOKEN', '').strip()
        user = os.getenv('SNOWFLAKE_USER', '').strip().upper()
        account = os.getenv('SNOWFLAKE_ACCOUNT', '').strip().upper()
        role = os.getenv("SNOWFLAKE_ROLE", "SYNAPSE_APP_ROLE").strip().upper()
        warehouse = os.getenv('SNOWFLAKE_WAREHOUSE', 'COMPUTE_WH').strip().upper()
        schema = os.getenv("SNOWFLAKE_SCHEMA", RAG_SCHEMA).strip().upper()

        conn_params = {
            "user": user,
            "account": account,
            "database": os.getenv('SNOWFLAKE_DATABASE', RAG_DB),
            "warehouse": warehouse,
            "schema": schema,
            "role": role,
            "client_prefetch_mfa_token": False,
            "client_request_mfa_token": False,
        }

        if token:
            # PAT (Programmatic Access Token): no enviar `role` en el connect string.
            # Aunque el usuario tenga GRANT USAGE ON ROLE, el conector puede rechazarlo;
            # la sesión usa el DEFAULT_ROLE del usuario (debe ser SYNAPSE_APP_ROLE).
            conn_params.pop("role", None)
            print(f"[Snowflake] Connecting via Token (User: {user}, Account: {account})")
            conn_params["authenticator"] = "PROGRAMMATIC_ACCESS_TOKEN"
            conn_params["token"] = token
        else:
            print("[Snowflake] Connecting via Password")
            conn_params["password"] = os.getenv('SNOWFLAKE_PASSWORD')

        self.conn = snowflake.connector.connect(**conn_params)
        self.ads_db = os.getenv("SNOWFLAKE_ADS_DATABASE", ADS_DB).strip().upper()
        self.ads_schema = os.getenv("SNOWFLAKE_ADS_SCHEMA", "UA_ECOMM").strip().upper()

    def _wants_chart(self, query: str) -> bool:
        chart_terms = [
            "GRAF", "CHART", "TENDENCIA", "EVOLUC", "HISTOR", "COMPAR",
            "ROAS", "CTR", "CPC", "CPM", "GASTO", "REVENUE", "CONVERSION",
            "DESEMPE", "RENDIMIENTO",
        ]
        q = query.upper()
        return any(term in q for term in chart_terms)

    def _wants_top_products(self, query: str) -> bool:
        q = query.upper()
        product_terms = ["PRODUCTO", "PRODUCTOS", "PRODUCT", "ITEM", "SKU"]
        top_terms = ["TOP", "MÁS", "MAS", "VEND", "SELL", "RANK", "RANKING"]
        source_terms = ["FUENTE", "FUENTES", "SOURCE", "CANAL", "ORIGEN"]
        return any(t in q for t in product_terms) and any(t in q for t in top_terms + source_terms)

    def _extract_top_n(self, query: str, default: int = 5) -> int:
        import re

        q = query.upper()
        digit_match = re.search(r"\b(\d{1,2})\b", q)
        if digit_match:
            n = int(digit_match.group(1))
            return max(1, min(n, 20))

        words_to_num = {
            "UNO": 1, "DOS": 2, "TRES": 3, "CUATRO": 4, "CINCO": 5,
            "SEIS": 6, "SIETE": 7, "OCHO": 8, "NUEVE": 9, "DIEZ": 10
        }
        for word, num in words_to_num.items():
            if word in q:
                return num
        return default

    def _get_top_products_by_source(self, cursor, limit: int = 5) -> Tuple[List[Dict], Optional[ChartConfig]]:
        """
        Usa ADOBE_SESSION para aproximar 'productos' por TRACKING_CODE, con fuente en DATA_SOURCE_NAME.
        """
        try:
            cursor.execute(f"""
                SELECT
                    TRACKING_CODE                              AS PRODUCTO,
                    DATA_SOURCE_NAME                           AS FUENTE,
                    SUM(ORDERS)                                AS ORDENES,
                    SUM(UNITS)                                 AS UNIDADES,
                    SUM(REVENUE)                               AS REVENUE
                FROM {self.ads_db}.{self.ads_schema}.ADOBE_SESSION
                WHERE TRACKING_CODE IS NOT NULL
                GROUP BY TRACKING_CODE, DATA_SOURCE_NAME
                ORDER BY SUM(UNITS) DESC
                LIMIT {limit}
            """)
            rows = cursor.fetchall()
            cols = [d[0] for d in cursor.description]
            data = [dict(zip(cols, r)) for r in rows] if rows else []
            if not data:
                return [], None

            chart = ChartConfig(
                type="bar",
                x_axis=[row["PRODUCTO"] for row in data],
                y_axis=[float(row.get("UNIDADES") or 0) for row in data],
                metrics_label="UNIDADES"
            )
            return data, chart
        except Exception as e:
            print(f"TOP PRODUCTOS warning: {e}")
            return [], None

    def _build_fallback_chart(self, raw_data: List[Dict]) -> Optional[ChartConfig]:
        if not raw_data:
            return None

        preferred_x_keys = ["DATE", "FECHA", "CAMPAIGN_ID", "CAMPAIGN", "PLATAFORMA", "PLATFORM"]
        preferred_y_keys = ["ROAS", "REVENUE", "GASTO", "CONVERSIONES", "CLICKS", "IMPRESIONES"]

        sample = raw_data[0]
        keys = list(sample.keys())

        x_key = next((k for k in preferred_x_keys if k in keys), None)
        if not x_key:
            x_key = next((k for k in keys if isinstance(sample.get(k), (str, int))), None)

        y_key = next((k for k in preferred_y_keys if k in keys), None)
        if not y_key:
            y_key = next((k for k in keys if isinstance(sample.get(k), (int, float))), None)

        if not x_key or not y_key:
            return None

        series = {}
        for row in raw_data:
            x = row.get(x_key)
            y = row.get(y_key)
            if x is None or y is None:
                continue
            try:
                y_num = float(y)
            except (TypeError, ValueError):
                continue
            label = str(x)
            series[label] = series.get(label, 0.0) + y_num

        if not series:
            return None

        x_axis = sorted(series.keys())[-14:]
        y_axis = [round(series[x], 2) for x in x_axis]
        return ChartConfig(
            type="line",
            x_axis=x_axis,
            y_axis=y_axis,
            metrics_label=y_key
        )

    # ------------------------------------------------------------------
    # DATOS DE PAUTA REAL (UA_ECOMM)
    # ------------------------------------------------------------------

    def _get_platform_metrics(self, cursor, platform: str) -> List[Dict]:
        """Obtiene métricas reales con ROAS calculado (CONVERSION_VALUE / COST)."""
        platform_sources = {
            "GOOGLE": [
                {"table": "GOOGLE_ADS_METRICAS", "revenue_col": "CONVERSION_VALUE", "conv_col": "CONVERSIONS"},
                {"table": "GOOGLEADS_UA_MX_GOOGLE_ADS_METRICS", "revenue_col": "CONVERSION_VALUE", "conv_col": "CONVERSIONS"},
            ],
            "FACEBOOK": [
                {"table": "FACEBOOK_ADS_METRICAS", "revenue_col": "CONVERSION_VALUE", "conv_col": "CONVERSIONS"},
                {"table": "FBADS_UA_MX_FB_ADS_METRICS", "revenue_col": "CONVERSION_VALUE", "conv_col": "OFFSITE_CONVERSIONS_FB_PIXEL_PURCHASE"},
            ],
            "CRITEO": [
                {"table": "CRITEO_ADS_METRICAS", "revenue_col": "CONVERSION_VALUE", "conv_col": "CONVERSIONS"},
                {"table": "CRI_UA_MX_CRITEO_METRICS", "revenue_col": "REVENUE", "conv_col": "SALES_COUNT"},
            ],
        }

        for src in platform_sources.get(platform, []):
            table = src["table"]
            revenue_col = src["revenue_col"]
            conv_col = src["conv_col"]
            try:
                cursor.execute(f"""
                    SELECT
                        DATE,
                        CAMPAIGN_ID,
                        SUM(COST)                                          AS GASTO,
                        SUM({conv_col})                                    AS CONVERSIONES,
                        SUM({revenue_col})                                 AS REVENUE,
                        SUM(CLICKS)                                        AS CLICKS,
                        SUM(IMPRESSIONS)                                   AS IMPRESIONES,
                        ROUND(
                            SUM({revenue_col}) / NULLIF(SUM(COST), 0), 2
                        )                                                  AS ROAS
                    FROM {self.ads_db}.{self.ads_schema}.{table}
                    GROUP BY DATE, CAMPAIGN_ID
                    ORDER BY DATE DESC
                    LIMIT 30
                """)
                rows = cursor.fetchall()
                cols = [desc[0] for desc in cursor.description]
                if rows:
                    return [dict(zip(cols, row)) for row in rows]
            except Exception as e:
                print(f"{platform} metrics source warning ({table}): {e}")
                continue

        print(f"{platform} metrics warning: no se encontraron fuentes compatibles.")
        return []

    def _get_sales_data(self, cursor) -> List[Dict]:
        """Obtiene datos de ventas reales desde UA_ECOMM."""
        sales_sources = [
            "VENTAS_POR_PLATAFORMA_Y_ID_CLIENTE",
            "UA_TARGETS_ECOMM",
            "ADOBE_SESSION",
        ]
        for table in sales_sources:
            try:
                cursor.execute(f"""
                    SELECT *
                    FROM {self.ads_db}.{self.ads_schema}.{table}
                    ORDER BY 1 DESC
                    LIMIT 10
                """)
                rows = cursor.fetchall()
                cols = [desc[0] for desc in cursor.description]
                if rows:
                    return [dict(zip(cols, row)) for row in rows]
            except Exception as e:
                print(f"VENTAS source warning ({table}): {e}")
                continue
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

        # Traer todas solo si la consulta apunta a performance/ROAS.
        if any(k in query.upper() for k in ["ROAS", "GENERAL", "TODAS", "RESUMEN", "ESTRATEG", "RENDIMIENTO", "TENDENCIA"]):
            platforms = ["GOOGLE", "FACEBOOK", "CRITEO"]
        elif not platforms:
            # Para consultas no-performance (ej. productos/fuentes), no forzar ROAS.
            return "", [], None

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
            # 1. Datos reales según intención de consulta
            if self._wants_top_products(query):
                top_n = self._extract_top_n(query, default=5)
                raw_data, chart_config = self._get_top_products_by_source(cursor, limit=top_n)
                ads_context = ""
                if raw_data:
                    ads_context = "=== TOP PRODUCTOS (TRACKING_CODE) Y FUENTE ===\n" + str(raw_data[:5])
            else:
                ads_context, raw_data, chart_config = self._build_ads_context(cursor, query)

            if not chart_config and self._wants_chart(query):
                chart_config = self._build_fallback_chart(raw_data)

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
