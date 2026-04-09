import snowflake.connector
import os
import re
import uuid
from datetime import date, datetime, timedelta
from typing import Optional, Union, List, Tuple, Dict, Any
from models.synapse import SynapseResponse, ChartConfig, DecisionMeta
from services.snowflake_catalog import (
    HEAVY_TABLES_SAMPLE_SQL,
    is_allowed_identifier,
    max_catalog_fetches,
    rank_datasets_for_query,
    sample_row_limit,
)

RAG_DB     = "DB_BT_UA"
RAG_SCHEMA = "BT_UA_MART_ANALYTICS"
GOLD_DB    = "DB_BT_UA"
GOLD_SCHEMA = "BT_UA_MART_ANALYTICS"


def build_snowflake_connection_params() -> Dict[str, Any]:
    """Parámetros de conexión (PAT o password); reutilizable por Cortex Analyst y SnowflakeService."""
    token = os.getenv("SNOWFLAKE_TOKEN", "").strip()
    user = os.getenv("SNOWFLAKE_USER", "").strip().upper()
    account = os.getenv("SNOWFLAKE_ACCOUNT", "").strip().upper()
    role = os.getenv("SNOWFLAKE_ROLE", "SYNAPSE_APP_ROLE").strip().upper()
    warehouse = os.getenv("SNOWFLAKE_WAREHOUSE", "COMPUTE_WH").strip().upper()
    schema = os.getenv("SNOWFLAKE_SCHEMA", RAG_SCHEMA).strip().upper()

    login_timeout = int(os.getenv("SNOWFLAKE_LOGIN_TIMEOUT_SEC", "15"))
    network_timeout = int(os.getenv("SNOWFLAKE_NETWORK_TIMEOUT_SEC", "60"))
    statement_timeout = int(os.getenv("SNOWFLAKE_STATEMENT_TIMEOUT_SEC", "90"))

    conn_params: Dict[str, Any] = {
        "user": user,
        "account": account,
        "database": os.getenv("SNOWFLAKE_DATABASE", RAG_DB),
        "warehouse": warehouse,
        "schema": schema,
        "role": role,
        "client_prefetch_mfa_token": False,
        "client_request_mfa_token": False,
        "login_timeout": login_timeout,
        "network_timeout": network_timeout,
        "session_parameters": {
            "STATEMENT_TIMEOUT_IN_SECONDS": statement_timeout,
        },
    }

    if token:
        conn_params.pop("role", None)
        print(f"[Snowflake] Connecting via Token (User: {user}, Account: {account})")
        conn_params["authenticator"] = "PROGRAMMATIC_ACCESS_TOKEN"
        conn_params["token"] = token
    else:
        print("[Snowflake] Connecting via Password")
        conn_params["password"] = os.getenv("SNOWFLAKE_PASSWORD")

    return conn_params


def connect_snowflake():
    return snowflake.connector.connect(**build_snowflake_connection_params())


class SnowflakeService:
    def __init__(self, tenant_id: str):
        _ = tenant_id
        self.conn = connect_snowflake()
        self.gold_db = os.getenv("SNOWFLAKE_GOLD_DATABASE", GOLD_DB).strip().upper()
        self.gold_schema = os.getenv("SNOWFLAKE_GOLD_SCHEMA", GOLD_SCHEMA).strip().upper()

    def _wants_chart(self, query: str) -> bool:
        chart_terms = [
            "GRAF", "CHART", "TENDENCIA", "EVOLUC", "HISTOR", "COMPAR",
            "ROAS", "CTR", "CPC", "CPM", "GASTO", "REVENUE", "CONVERSION",
            "DESEMPE", "RENDIMIENTO",
        ]
        q = query.upper()
        return any(term in q for term in chart_terms)

    def _wants_campaign_inventory(self, query: str) -> bool:
        """Listados de campañas por periodo / activas (no mezclar con muestras genéricas del catálogo)."""
        q = query.upper()
        if not any(t in q for t in ("CAMPAÑA", "CAMPAIGNS", "CAMPAIGN", "CAMPANA")):
            return False
        return any(
            t in q
            for t in (
                "ACTIVA",
                "ACTIVAS",
                "ACTIVO",
                "LISTADO",
                "LISTA",
                "CUÁLES",
                "CUALES",
                "QUÉ CAMPA",
                "QUE CAMPA",
                "NOMBRE",
                "HUBO",
                "HAY",
                "FUERON",
                "ESTUVIERON",
                "DURANTE",
                "AÑO",
                "ANIO",
                "PERIODO",
                "PERÍODO",
            )
        )

    def _campaign_year_bounds(self, query: str) -> Optional[Tuple[int, int]]:
        """Años calendario 20xx en la pregunta; (inicio, fin) inclusive. None si no hay año explícito."""
        years = sorted({int(y) for y in re.findall(r"\b(20[2-3]\d)\b", query)})
        if not years:
            return None
        return (years[0], years[-1])

    def _get_campaigns_active_in_range(
        self, cursor, year_start: int, year_end: int
    ) -> Tuple[List[Dict], Optional[ChartConfig]]:
        """
        Campañas con actividad (gasto, clicks, impresiones u órdenes) en FCT_PERFORMANCE
        dentro del rango de años [year_start, year_end].
        """
        if year_start < 2000 or year_end > 2100 or year_start > year_end:
            return [], None
        d0 = f"{year_start}-01-01"
        d1 = f"{year_end + 1}-01-01"
        try:
            cursor.execute(f"""
                SELECT
                    COALESCE(CAMPAIGN_PRIMARIO, 'SIN_CAMPAÑA')     AS CAMPAIGN_PRIMARIO,
                    COALESCE(FUENTE, 'SIN_FUENTE')                AS FUENTE,
                    MIN(DATE)                                     AS FECHA_PRIMERA_ACTIVIDAD,
                    MAX(DATE)                                     AS FECHA_ULTIMA_ACTIVIDAD,
                    SUM(COALESCE(COST_USD, 0))                    AS GASTO_USD_PERIODO,
                    SUM(COALESCE(CLICKS, 0))                      AS CLICKS_PERIODO,
                    SUM(COALESCE(IMPRESSIONS, 0))                 AS IMPRESIONES_PERIODO,
                    SUM(COALESCE(ORDENES_VENDIDAS, 0))            AS ORDENES_PERIODO,
                    SUM(COALESCE(INGRESOS_USD, 0))                AS INGRESOS_USD_PERIODO
                FROM {self.gold_db}.{self.gold_schema}.FCT_PERFORMANCE
                WHERE DATE >= '{d0}' AND DATE < '{d1}'
                GROUP BY 1, 2
                HAVING SUM(COALESCE(COST_USD, 0)) > 0
                    OR SUM(COALESCE(CLICKS, 0)) > 0
                    OR SUM(COALESCE(IMPRESSIONS, 0)) > 0
                    OR SUM(COALESCE(ORDENES_VENDIDAS, 0)) > 0
                ORDER BY GASTO_USD_PERIODO DESC NULLS LAST, CLICKS_PERIODO DESC
                LIMIT 400
            """)
            rows = cursor.fetchall()
            cols = [d[0] for d in cursor.description]
            data = [dict(zip(cols, r)) for r in rows] if rows else []
            return data, None
        except Exception as e:
            print(f"campaign inventory warning: {e}")
            return [], None

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

    def _classify_intent(self, query: str) -> str:
        q = query.upper()
        intent_rules = {
            "budget_reallocation": ["REASIGN", "PRESUPUEST", "BUDGET", "INVERT", "ESCALAR", "PAUSAR"],
            "forecast": ["FORECAST", "PROYECC", "PREDICC", "ESTIM", "CERRAR MES", "PRONOST"],
            "diagnostic": ["ANOMAL", "POR QUÉ", "PORQUE", "CAUSA", "CAIDA", "BAJÓ", "SUBIÓ", "RIESGO"],
            "product_mix": ["PRODUCTO", "PRODUCTOS", "SKU", "ITEM", "PORTAFOLIO"],
            "performance": ["ROAS", "CTR", "CPC", "CPM", "REVENUE", "CONVERSION", "RENDIMIENTO", "DESEMPE"],
        }
        for intent, terms in intent_rules.items():
            if any(t in q for t in terms):
                return intent
        return "general_strategy"

    def _to_date(self, value: Any) -> Optional[date]:
        if isinstance(value, datetime):
            return value.date()
        if isinstance(value, date):
            return value
        if isinstance(value, str):
            for fmt in ("%Y-%m-%d", "%Y/%m/%d"):
                try:
                    return datetime.strptime(value[:10], fmt).date()
                except ValueError:
                    continue
        return None

    def _get_data_freshness(self, raw_data: List[Dict]) -> str:
        dates = [self._to_date(row.get("DATE")) for row in raw_data if "DATE" in row]
        dates = [d for d in dates if d is not None]
        if not dates:
            return "unknown"
        lag_days = (datetime.utcnow().date() - max(dates)).days
        if lag_days <= 1:
            return "fresh_24h"
        if lag_days <= 7:
            return "fresh_weekly"
        return f"stale_{lag_days}d"

    def _compute_comparisons(self, raw_data: List[Dict]) -> Dict[str, Any]:
        # Deprecated: kept for compatibility. Real comparisons now use Gold layer queries.
        return {
            "week_over_week": {"status": "unavailable", "reason": "deprecated_local_mode"},
            "vs_target": {"status": "unavailable", "reason": "deprecated_local_mode"},
            "vs_last_year": {"status": "unavailable", "reason": "deprecated_local_mode"},
        }

    def _safe_div(self, a: float, b: float) -> Optional[float]:
        if b in (0, 0.0, None):
            return None
        return round((a / b), 4)

    def _delta_pct(self, current: Optional[float], previous: Optional[float]) -> Optional[float]:
        if current is None or previous in (None, 0, 0.0):
            return None
        return round(((current - previous) / previous) * 100, 2)

    def _get_window_from_data(self, cursor, raw_data: List[Dict]) -> Tuple[date, date]:
        dates = [self._to_date(r.get("DATE")) for r in raw_data if "DATE" in r]
        dates = sorted([d for d in dates if d is not None])
        if dates:
            end = dates[-1]
            start = max(dates[0], end - timedelta(days=6))
            return start, end

        # fallback: usar última fecha disponible en Gold
        try:
            cursor.execute("""
                SELECT MAX(DATE) AS MAX_DATE
                FROM DB_BT_UA.BT_UA_MART_ANALYTICS.FCT_PERFORMANCE
            """)
            row = cursor.fetchone()
            if row and row[0]:
                end = self._to_date(row[0]) or datetime.utcnow().date()
                return end - timedelta(days=6), end
        except Exception:
            pass

        end = datetime.utcnow().date()
        return end - timedelta(days=6), end

    def _aggregate_performance_window(self, cursor, start: date, end: date) -> Dict[str, float]:
        cursor.execute(f"""
            SELECT
                COALESCE(SUM(COST_USD), 0) AS GASTO,
                COALESCE(SUM(INGRESOS_USD), 0) AS REVENUE,
                COALESCE(SUM(ORDENES_VENDIDAS), 0) AS ORDENES,
                COALESCE(SUM(UNIDADES_VENDIDAS), 0) AS UNIDADES
            FROM DB_BT_UA.BT_UA_MART_ANALYTICS.FCT_PERFORMANCE
            WHERE DATE BETWEEN '{start}' AND '{end}'
        """)
        row = cursor.fetchone() or (0, 0, 0, 0)
        spend = float(row[0] or 0)
        revenue = float(row[1] or 0)
        orders = float(row[2] or 0)
        units = float(row[3] or 0)
        roas = self._safe_div(revenue, spend)
        return {
            "gasto": round(spend, 2),
            "revenue": round(revenue, 2),
            "ordenes": round(orders, 2),
            "unidades": round(units, 2),
            "roas": round(roas, 4) if roas is not None else None,
        }

    def _aggregate_target_window(self, cursor, start: date, end: date) -> Dict[str, float]:
        # Guardrail estricto: solo capa Gold.
        # Si no existe tabla de targets en Gold, se mantiene en 0 para marcar unavailable.
        target_table = os.getenv("SNOWFLAKE_GOLD_TARGET_TABLE", "").strip()
        if not target_table:
            return {
                "gasto_target": 0.0,
                "revenue_target": 0.0,
                "ordenes_target": 0.0,
                "unidades_target": 0.0,
            }

        cursor.execute(f"""
            SELECT
                COALESCE(SUM(TRY_TO_DECIMAL(REGEXP_REPLACE(GASTO_TARGET, '[^0-9.-]', ''))), 0) AS GASTO_TARGET,
                COALESCE(SUM(TRY_TO_DECIMAL(REGEXP_REPLACE(REVENUE_TARGET, '[^0-9.-]', ''))), 0) AS REVENUE_TARGET,
                COALESCE(SUM(TRY_TO_DECIMAL(REGEXP_REPLACE(ORDENES_TARGET, '[^0-9.-]', ''))), 0) AS ORDENES_TARGET,
                COALESCE(SUM(TRY_TO_DECIMAL(REGEXP_REPLACE(UNIDADES_TARGET, '[^0-9.-]', ''))), 0) AS UNIDADES_TARGET
            FROM {target_table}
            WHERE DATE BETWEEN '{start}' AND '{end}'
        """)
        row = cursor.fetchone() or (0, 0, 0, 0)
        return {
            "gasto_target": round(float(row[0] or 0), 2),
            "revenue_target": round(float(row[1] or 0), 2),
            "ordenes_target": round(float(row[2] or 0), 2),
            "unidades_target": round(float(row[3] or 0), 2),
        }

    def _compute_gold_comparisons(self, cursor, raw_data: List[Dict]) -> Dict[str, Any]:
        output: Dict[str, Any] = {
            "week_over_week": {"status": "unavailable"},
            "vs_target": {"status": "unavailable"},
            "vs_last_year": {"status": "unavailable"},
        }
        try:
            start, end = self._get_window_from_data(cursor, raw_data)
            days = max(1, (end - start).days + 1)
            prev_end = start - timedelta(days=1)
            prev_start = prev_end - timedelta(days=days - 1)
            ly_start = date(start.year - 1, start.month, start.day)
            ly_end = date(end.year - 1, end.month, end.day)

            current = self._aggregate_performance_window(cursor, start, end)
            previous = self._aggregate_performance_window(cursor, prev_start, prev_end)
            target = self._aggregate_target_window(cursor, start, end)
            last_year = self._aggregate_performance_window(cursor, ly_start, ly_end)

            wow_metrics = {}
            for key in ["roas", "gasto", "revenue", "ordenes", "unidades"]:
                wow_metrics[key] = {
                    "current": current.get(key),
                    "previous": previous.get(key),
                    "delta_pct": self._delta_pct(current.get(key), previous.get(key)),
                }
            if all((previous.get(k) or 0) == 0 for k in ["gasto", "revenue", "ordenes", "unidades"]):
                output["week_over_week"] = {
                    "status": "unavailable",
                    "reason": "La ventana previa no tiene base de comparación (>0).",
                    "window": {"current_start": str(start), "current_end": str(end)},
                }
            else:
                output["week_over_week"] = {
                    "status": "ok",
                    "window": {"current_start": str(start), "current_end": str(end)},
                    "metrics": wow_metrics,
                }

            target_metrics = {}
            mapping = {
                "gasto": "gasto_target",
                "revenue": "revenue_target",
                "ordenes": "ordenes_target",
                "unidades": "unidades_target",
            }
            for actual_key, target_key in mapping.items():
                actual = current.get(actual_key)
                tgt = target.get(target_key)
                target_metrics[actual_key] = {
                    "actual": actual,
                    "target": tgt,
                    "gap_pct": self._delta_pct(actual, tgt),
                }
            if all((target.get(k) or 0) == 0 for k in ["gasto_target", "revenue_target", "ordenes_target", "unidades_target"]):
                output["vs_target"] = {
                    "status": "unavailable",
                    "reason": "No hay targets cargados para la ventana analizada.",
                    "window": {"start": str(start), "end": str(end)},
                }
            else:
                output["vs_target"] = {
                    "status": "ok",
                    "window": {"start": str(start), "end": str(end)},
                    "metrics": target_metrics,
                }

            yoy_metrics = {}
            for key in ["roas", "gasto", "revenue", "ordenes", "unidades"]:
                yoy_metrics[key] = {
                    "current": current.get(key),
                    "last_year": last_year.get(key),
                    "delta_pct": self._delta_pct(current.get(key), last_year.get(key)),
                }
            if all((last_year.get(k) or 0) == 0 for k in ["gasto", "revenue", "ordenes", "unidades"]):
                output["vs_last_year"] = {
                    "status": "unavailable",
                    "reason": "No hay datos del mismo periodo del año anterior.",
                    "window": {
                        "current_start": str(start),
                        "current_end": str(end),
                        "last_year_start": str(ly_start),
                        "last_year_end": str(ly_end),
                    },
                }
            else:
                output["vs_last_year"] = {
                    "status": "ok",
                    "window": {
                        "current_start": str(start),
                        "current_end": str(end),
                        "last_year_start": str(ly_start),
                        "last_year_end": str(ly_end),
                    },
                    "metrics": yoy_metrics,
                }
            return output
        except Exception as e:
            output["week_over_week"]["reason"] = f"error: {str(e)}"
            output["vs_target"]["reason"] = f"error: {str(e)}"
            output["vs_last_year"]["reason"] = f"error: {str(e)}"
            return output

    def _build_guardrails(self, raw_data: List[Dict], comparisons: Dict[str, Any]) -> List[str]:
        guardrails = []
        if len(raw_data) < 5:
            guardrails.append("Muestra baja (<5 registros): validar antes de escalar inversión.")
        week = comparisons.get("week_over_week") or {}
        if week.get("status") != "ok":
            guardrails.append("Comparativo semanal incompleto: faltan datos para vs semana previa.")
        zero_cost = sum(1 for r in raw_data if float(r.get("GASTO") or 0) == 0)
        if zero_cost > 0:
            guardrails.append(f"Se detectaron {zero_cost} filas con gasto cero; revisar tracking/atribución.")
        high_roas = [float(r.get("ROAS") or 0) for r in raw_data if r.get("ROAS") is not None]
        if high_roas and max(high_roas) > 80:
            guardrails.append("Outliers de ROAS detectados (>80x): validar calidad de datos antes de reasignar.")
        return guardrails

    def _compute_confidence(self, raw_data: List[Dict], freshness: str, guardrails: List[str]) -> float:
        score = 0.5
        if len(raw_data) >= 10:
            score += 0.2
        if freshness in {"fresh_24h", "fresh_weekly"}:
            score += 0.2
        penalty = min(0.3, 0.07 * len(guardrails))
        score -= penalty
        return round(max(0.1, min(0.95, score)), 2)

    def _get_top_products_by_source(self, cursor, limit: int = 5) -> Tuple[List[Dict], Optional[ChartConfig]]:
        """
        Usa capa Gold para top productos por fuente.
        """
        try:
            cursor.execute(f"""
                SELECT
                    NOMBRE_PRODUCTO_POR_ID_PRODUCTO            AS PRODUCTO,
                    COALESCE(FUENTE, 'SIN_FUENTE')             AS FUENTE,
                    COUNT(DISTINCT ID_CLIENTE)                 AS ORDENES,
                    SUM(UNIDADES_VENDIDAS)                     AS UNIDADES,
                    SUM(INGRESOS_USD)                          AS REVENUE
                FROM {self.gold_db}.{self.gold_schema}.VENTAS_PRODUCTOS_FUENTE
                WHERE NOMBRE_PRODUCTO_POR_ID_PRODUCTO IS NOT NULL
                GROUP BY NOMBRE_PRODUCTO_POR_ID_PRODUCTO, COALESCE(FUENTE, 'SIN_FUENTE')
                ORDER BY SUM(UNIDADES_VENDIDAS) DESC
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
        """Obtiene métricas reales desde capa Gold FCT_PERFORMANCE."""
        try:
            cursor.execute(f"""
                SELECT
                    DATE,
                    COALESCE(CAMPAIGN_PRIMARIO, 'SIN_CAMPAÑA')            AS CAMPAIGN_ID,
                    SUM(COST_USD)                                         AS GASTO,
                    SUM(ORDENES_VENDIDAS)                                 AS CONVERSIONES,
                    SUM(INGRESOS_USD)                                     AS REVENUE,
                    SUM(CLICKS)                                           AS CLICKS,
                    SUM(IMPRESSIONS)                                      AS IMPRESIONES,
                    ROUND(SUM(INGRESOS_USD) / NULLIF(SUM(COST_USD), 0), 2) AS ROAS
                FROM {self.gold_db}.{self.gold_schema}.FCT_PERFORMANCE
                WHERE UPPER(COALESCE(FUENTE, '')) LIKE '%{platform}%'
                GROUP BY DATE, COALESCE(CAMPAIGN_PRIMARIO, 'SIN_CAMPAÑA')
                ORDER BY DATE DESC
                LIMIT 30
            """)
            rows = cursor.fetchall()
            cols = [desc[0] for desc in cursor.description]
            return [dict(zip(cols, row)) for row in rows] if rows else []
        except Exception as e:
            print(f"{platform} metrics gold warning: {e}")
            return []

    def _get_sales_data(self, cursor) -> List[Dict]:
        """Obtiene datos de ventas reales desde capa Gold."""
        try:
            cursor.execute(f"""
                SELECT
                    DATE,
                    COALESCE(FUENTE, 'SIN_FUENTE')                    AS FUENTE,
                    SUM(ORDENES_VENDIDAS)                             AS ORDENES,
                    SUM(UNIDADES_VENDIDAS)                            AS UNIDADES,
                    SUM(INGRESOS_USD)                                 AS REVENUE
                FROM {self.gold_db}.{self.gold_schema}.FCT_PERFORMANCE
                GROUP BY DATE, COALESCE(FUENTE, 'SIN_FUENTE')
                ORDER BY DATE DESC
                LIMIT 20
            """)
            rows = cursor.fetchall()
            cols = [desc[0] for desc in cursor.description]
            return [dict(zip(cols, row)) for row in rows] if rows else []
        except Exception as e:
            print(f"VENTAS gold warning: {e}")
            return []

    def _fetch_dataset_sample(self, cursor, table: str) -> List[Dict]:
        """Muestra segura (whitelist) de una tabla/vista Gold del catálogo."""
        if not is_allowed_identifier(table):
            return []
        limit = sample_row_limit()
        fq = f"{self.gold_db}.{self.gold_schema}.{table}"
        tpl = HEAVY_TABLES_SAMPLE_SQL.get(table)
        if tpl:
            sql = tpl.format(fq=fq, limit=limit)
        else:
            sql = f"SELECT * FROM {fq} LIMIT {limit}"
        try:
            cursor.execute(sql)
            rows = cursor.fetchall()
            cols = [d[0] for d in cursor.description]
            return [dict(zip(cols, r)) for r in rows] if rows else []
        except Exception as e:
            print(f"[Snowflake] sample {table}: {e}")
            try:
                cursor.execute(f"SELECT * FROM {fq} LIMIT {limit}")
                rows = cursor.fetchall()
                cols = [d[0] for d in cursor.description]
                return [dict(zip(cols, r)) for r in rows] if rows else []
            except Exception as e2:
                print(f"[Snowflake] sample fallback {table}: {e2}")
                return []

    def _build_ads_context(self, cursor, query: str) -> Tuple[str, List, Optional[ChartConfig]]:
        """Contexto Gold: catálogo completo (DATA_STRUCTURE) + métricas por plataforma cuando aplique."""
        context_parts = []
        raw_data = []
        chart_config = None
        q_upper = query.upper()

        platforms = []
        if any(k in q_upper for k in ["GOOGLE", "SEM", "SEARCH"]):
            platforms.append("GOOGLE")
        if any(k in q_upper for k in ["FACEBOOK", "META", "FB", "INSTAGRAM"]):
            platforms.append("FACEBOOK")
        if any(k in q_upper for k in ["CRITEO", "RETARGETING", "DISPLAY"]):
            platforms.append("CRITEO")

        if any(k in q_upper for k in ["ROAS", "GENERAL", "TODAS", "RESUMEN", "ESTRATEG", "RENDIMIENTO", "TENDENCIA"]):
            platforms = ["GOOGLE", "FACEBOOK", "CRITEO"]

        max_tables = max_catalog_fetches()
        ranked = rank_datasets_for_query(query, max_tables)

        for table in ranked:
            rows = self._fetch_dataset_sample(cursor, table)
            if not rows:
                continue
            for r in rows:
                r["_source_dataset"] = table
            context_parts.append(f"=== {table} (muestra autorizada Gold) ===")
            context_parts.append(str(rows[:2]))
            raw_data.extend(rows)

        for platform in platforms:
            metrics = self._get_platform_metrics(cursor, platform)
            if metrics:
                for r in metrics:
                    r["_source_dataset"] = f"FCT_PERFORMANCE_{platform}"
                context_parts.append(f"=== {platform} ADS (filtrado FCT_PERFORMANCE) ===")
                context_parts.append(str(metrics[:3]))
                raw_data.extend(metrics[:5])

        if not raw_data:
            sales = self._get_sales_data(cursor)
            if sales:
                for r in sales:
                    r["_source_dataset"] = "FCT_PERFORMANCE_VENTAS_RESUMEN"
                context_parts.append("=== VENTAS POR FUENTE (Gold, fallback) ===")
                context_parts.append(str(sales[:3]))
                raw_data.extend(sales[:5])

        # Gráfico ROAS solo si el usuario pidió visualización / tendencia / ROAS explícitamente.
        if (
            chart_config is None
            and self._wants_chart(query)
            and raw_data
            and len(raw_data) >= 2
        ):
            from collections import defaultdict

            date_roas: dict = defaultdict(list)
            for row in raw_data:
                date_val = str(row.get("DATE", ""))
                roas_val = row.get("ROAS")
                if date_val and roas_val is not None:
                    date_roas[date_val].append(float(roas_val))

            if date_roas:
                sorted_dates = sorted(date_roas.keys())[-14:]
                avg_roas = [round(sum(date_roas[d]) / len(date_roas[d]), 2) for d in sorted_dates]
                chart_config = ChartConfig(
                    type="line",
                    x_axis=sorted_dates,
                    y_axis=avg_roas,
                    metrics_label="ROAS (CONVERSION_VALUE / COST)",
                )

        if any(k in q_upper for k in ["VENTA", "REVENUE", "INGRESO", "ECOMMERCE", "ROAS", "ESTRATEG"]) and raw_data:
            sales = self._get_sales_data(cursor)
            if sales:
                context_parts.append("=== VENTAS POR PLATAFORMA (refuerzo) ===")
                context_parts.append(str(sales[:3]))

        return "\n\n".join(context_parts), raw_data, chart_config

    def _build_no_data_response(self, query: str, intent: str) -> SynapseResponse:
        narrative = (
            "Con la evidencia operativa disponible hoy no puedo sustentar una respuesta fiable a esta pregunta. "
            "Te sugiero acotar por periodo, canal o tipo de métrica (por ejemplo: ROAS, gasto, ingresos, órdenes, "
            "campaña o producto) para que el análisis sea accionable."
        )
        decision_meta = DecisionMeta(
            intent=intent,
            confidence_score=0.0,
            data_freshness="unknown",
            guardrails=[
                "Respuesta restringida a evidencia cuantitativa disponible para el equipo.",
                f"Consulta sin muestra suficiente: '{query[:120]}'",
            ],
            comparisons={
                "week_over_week": {"status": "unavailable", "reason": "Sin muestra comparable para esta consulta."},
                "vs_target": {"status": "unavailable", "reason": "Sin muestra comparable para esta consulta."},
                "vs_last_year": {"status": "unavailable", "reason": "Sin muestra comparable para esta consulta."},
            },
            actions=[],
        )
        return SynapseResponse(
            response_id=str(uuid.uuid4()),
            narrative=narrative,
            render_type="text",
            chart_config=None,
            raw_data=None,
            decision_meta=decision_meta,
        )

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

        qu = query.upper()
        if any(k in qu for k in ["BUENTIPO", "BUEN TIPO"]):
            try:
                cursor.execute(f"SELECT * FROM {RAG_DB}.{RAG_SCHEMA}.BUENTIPO_CHUNKS LIMIT 4")
                rows = cursor.fetchall()
                cols = [desc[0] for desc in cursor.description]
                if rows:
                    parts.append("=== BUENTIPO CHUNKS ===")
                    parts.append(str([dict(zip(cols, r)) for r in rows])[:4000])
            except Exception as e:
                print(f"BUENTIPO_CHUNKS warning: {e}")

        if any(k in qu for k in ["ECOM CHUNK", "REPORTE ECOMM", "PDF ECOMM"]) or (
            "ECOM" in qu and "CHUNK" in qu
        ):
            try:
                cursor.execute(f"SELECT * FROM {RAG_DB}.{RAG_SCHEMA}.ECOM_CHUNKS LIMIT 4")
                rows = cursor.fetchall()
                cols = [desc[0] for desc in cursor.description]
                if rows:
                    parts.append("=== ECOM CHUNKS ===")
                    parts.append(str([dict(zip(cols, r)) for r in rows])[:4000])
            except Exception as e:
                print(f"ECOM_CHUNKS warning: {e}")

        if any(k in qu for k in ["REPORTE CHUNK", "CHUNK REPORTE"]) or (
            "REPORTES" in qu and "CHUNK" in qu
        ):
            try:
                cursor.execute(f"SELECT * FROM {RAG_DB}.{RAG_SCHEMA}.REPORTES_CHUNKS LIMIT 4")
                rows = cursor.fetchall()
                cols = [desc[0] for desc in cursor.description]
                if rows:
                    parts.append("=== REPORTES CHUNKS ===")
                    parts.append(str([dict(zip(cols, r)) for r in rows])[:4000])
            except Exception as e:
                print(f"REPORTES_CHUNKS warning: {e}")

        return "\n\n".join(parts) if parts else ""

    # ------------------------------------------------------------------
    # PROCESO PRINCIPAL
    # ------------------------------------------------------------------

    def process_query(self, query: str, history: List = []) -> SynapseResponse:
        cursor = self.conn.cursor()
        try:
            intent = self._classify_intent(query)

            # 1. Datos reales según intención de consulta
            if self._wants_campaign_inventory(query):
                bounds = self._campaign_year_bounds(query)
                if bounds is None:
                    bounds = (datetime.utcnow().year, datetime.utcnow().year)
                ys, ye = bounds
                raw_data, chart_config = self._get_campaigns_active_in_range(cursor, ys, ye)
                for r in raw_data:
                    r["_source_dataset"] = "FCT_PERFORMANCE_CAMPAIGN_INVENTORY"
                periodo = str(ys) if ys == ye else f"{ys}–{ye}"
                ads_context = (
                    f"=== INVENTARIO DE CAMPAÑAS CON ACTIVIDAD EN {periodo} (performance UA) ===\n"
                    "Instrucción: el cliente pidió campañas en ese periodo. Responde con la lista y "
                    "desglose por fuente según las filas; no cambies de tema a ROAS ni gráficos de "
                    "tendencia si no los pidió. No inventes campañas fuera de esta evidencia.\n"
                )
                if raw_data:
                    ads_context += str(raw_data[:30])
            elif self._wants_top_products(query):
                top_n = self._extract_top_n(query, default=5)
                raw_data, chart_config = self._get_top_products_by_source(cursor, limit=top_n)
                ads_context = ""
                if raw_data:
                    ads_context = "=== TOP PRODUCTOS (TRACKING_CODE) Y FUENTE ===\n" + str(raw_data[:5])
            else:
                ads_context, raw_data, chart_config = self._build_ads_context(cursor, query)

            if not chart_config and self._wants_chart(query):
                chart_config = self._build_fallback_chart(raw_data)

            # Guardrail estricto: sin evidencia en capa Gold no se responde con narrativa inventada.
            if not raw_data:
                return self._build_no_data_response(query=query, intent=intent)

            render_type = "chart" if chart_config else ("table" if raw_data else "text")

            freshness = self._get_data_freshness(raw_data)
            comparisons = self._compute_gold_comparisons(cursor, raw_data)
            guardrails = self._build_guardrails(raw_data, comparisons)
            confidence = self._compute_confidence(raw_data, freshness, guardrails)
            decision_meta = DecisionMeta(
                intent=intent,
                confidence_score=confidence,
                data_freshness=freshness,
                guardrails=guardrails,
                comparisons=comparisons,
                actions=[],
            )

            # 2. Contexto RAG de reportes y fórmulas
            rag_context = self._get_rag_context(cursor, query)

            # 3. Historial conversacional
            history_context = "\n".join(
                [f"Usuario: {h['q']}\nSynapse: {h['a']}" for h in history]
            ) if history else ""

            # 4. Prompt al modelo (salida = narrativa que se entrega tal cual al cliente)
            prompt = f"""Eres Synapse, consejero analista senior en medios y ecommerce para Under Armour México (agencia Buentipo).

Dispones de evidencia cuantitativa y definiciones en bloques marcados abajo (uso interno). Las filas pueden traer el campo _source_dataset solo como referencia interna: si lo usas, tradúcelo a lenguaje de negocio (p. ej. "resumen de medios pagados", "detalle por campaña") sin mencionar proveedores de datos, nombres de bases, almacenes ni motores de IA.

Tono: como director de insights ante el cliente —claro, directo, con juicio y recomendaciones accionables. Sin saludos largos ni relleno.

{f"HISTORIAL:{chr(10)}{history_context}{chr(10)}" if history_context else ""}
{f"EVIDENCIA CUANTITATIVA (UA México):{chr(10)}{ads_context}{chr(10)}" if ads_context else ""}
{f"DEFINICIONES Y TEXTO DE APOYO:{chr(10)}{rag_context}{chr(10)}" if rag_context else ""}
PREGUNTA DEL CLIENTE: {query}

Instrucciones:
- Basa conclusiones en cifras presentes en la evidencia; no inventes métricas.
- Si la muestra es delgada o incompleta, dilo como riesgo para la decisión (no como fallo técnico).
- Incluye comparativos (vs periodo previo, vs meta, vs año anterior) solo cuando la evidencia lo permita; si no, dilo explícitamente.
- Estructura libre con titulares claros (puedes usar ##) y viñetas; prioriza "qué implica" y "qué haría el equipo".

Responde únicamente con el análisis para el cliente (sin metacomentarios sobre el prompt)."""

            prompt_safe = prompt.replace("$$", "__DD__")
            # COMPLETE devuelve la respuesta completa en un round-trip; streaming al cliente
            # requeriría SNOWFLAKE.CORTEX.COMPLETE ... con streaming en SQL API o orquestación aparte.
            cursor.execute(
                f"SELECT SNOWFLAKE.CORTEX.COMPLETE('mistral-large2', $${prompt_safe}$$)"
            )
            row = cursor.fetchone()
            narrative = (row[0].replace("__DD__", "$$") if row else "") or ""
            narrative = narrative.strip()
            if not narrative:
                narrative = (
                    "No pude generar el análisis en este momento. "
                    "Intenta reformular la pregunta o acotar periodo y canal."
                )

            return SynapseResponse(
                response_id=str(uuid.uuid4()),
                narrative=narrative,
                render_type=render_type,
                chart_config=chart_config,
                raw_data=raw_data if raw_data else None,
                decision_meta=decision_meta,
            )
        finally:
            cursor.close()
            self.conn.close()
