import snowflake.connector
import os
import uuid
from datetime import date, datetime, timedelta
from typing import Optional, Union, List, Tuple, Dict, Any
from models.synapse import SynapseResponse, ChartConfig, DecisionMeta, RecommendedAction

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
        cursor.execute(f"""
            SELECT
                COALESCE(SUM(TRY_TO_DECIMAL(REGEXP_REPLACE(DAILY_BUDGET_GROSS_TARGET, '[^0-9.-]', ''))), 0) AS GASTO_TARGET,
                COALESCE(SUM(TRY_TO_DECIMAL(REGEXP_REPLACE(REVENUE_USD_TOTAL_TARGET, '[^0-9.-]', ''))), 0) AS REVENUE_TARGET,
                COALESCE(SUM(TRY_TO_DECIMAL(REGEXP_REPLACE(ORDERS_TOTAL_TARGET, '[^0-9.-]', ''))), 0) AS ORDENES_TARGET,
                COALESCE(SUM(TRY_TO_DECIMAL(REGEXP_REPLACE(UNITS_TOTAL_TARGET, '[^0-9.-]', ''))), 0) AS UNIDADES_TARGET
            FROM UA_DATABASE.UA_ECOMM.UA_TARGETS_ECOMM
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

    def _build_recommended_actions(
        self,
        intent: str,
        comparisons: Dict[str, Any],
        confidence: float,
    ) -> List[RecommendedAction]:
        actions: List[RecommendedAction] = []
        wow_metrics = ((comparisons.get("week_over_week") or {}).get("metrics") or {})
        roas_delta = (wow_metrics.get("roas") or {}).get("delta_pct")
        spend_delta = (wow_metrics.get("gasto") or {}).get("delta_pct")
        revenue_delta = (wow_metrics.get("revenue") or {}).get("delta_pct")
        target_metrics = ((comparisons.get("vs_target") or {}).get("metrics") or {})
        revenue_target_gap = (target_metrics.get("revenue") or {}).get("gap_pct")

        if intent in {"budget_reallocation", "performance", "diagnostic"}:
            actions.append(
                RecommendedAction(
                    action="Reasignar 10-15% del presupuesto desde campañas con ROAS bajo al top cuartil de ROAS.",
                    owner="medios",
                    horizon="24h",
                    expected_impact="Mejora esperada de 3-8% en ROAS semanal.",
                    priority_score=round(0.85 * confidence, 2),
                )
            )
            actions.append(
                RecommendedAction(
                    action="Configurar alerta diaria de desvío de gasto y ROAS por campaña (umbral +/-20%).",
                    owner="planning",
                    horizon="7d",
                    expected_impact="Reduce sobreinversión y acelera correcciones tácticas.",
                    priority_score=round(0.78 * confidence, 2),
                )
            )
            actions.append(
                RecommendedAction(
                    action="Ejecutar experimento A/B de segmentación/creatividad en canal con caída relativa.",
                    owner="estrategia",
                    horizon="30d",
                    expected_impact="Incremento potencial de 5-12% en revenue incremental.",
                    priority_score=round(0.7 * confidence, 2),
                )
            )
        elif intent == "forecast":
            actions.append(
                RecommendedAction(
                    action="Construir forecast semanal de ROAS/Revenue con baseline de últimas 8 semanas.",
                    owner="planning",
                    horizon="7d",
                    expected_impact="Mayor precisión para pacing y cierre de mes.",
                    priority_score=round(0.8 * confidence, 2),
                )
            )
            actions.append(
                RecommendedAction(
                    action="Definir bandas de acción automática (congelar/escalar) según desviación del forecast.",
                    owner="medios",
                    horizon="24h",
                    expected_impact="Menor volatilidad y respuesta táctica más rápida.",
                    priority_score=round(0.74 * confidence, 2),
                )
            )
            actions.append(
                RecommendedAction(
                    action="Revisar supuestos de estacionalidad y eventos comerciales con negocio.",
                    owner="estrategia",
                    horizon="30d",
                    expected_impact="Menor error de pronóstico en picos promocionales.",
                    priority_score=round(0.66 * confidence, 2),
                )
            )
        else:
            actions.append(
                RecommendedAction(
                    action="Consolidar KPIs por canal/campaña en tablero semanal con owner definido.",
                    owner="planning",
                    horizon="7d",
                    expected_impact="Mejor gobernanza y consistencia de decisiones.",
                    priority_score=round(0.72 * confidence, 2),
                )
            )
            actions.append(
                RecommendedAction(
                    action="Priorizar 3 oportunidades de mayor impacto y ejecutar test controlados.",
                    owner="estrategia",
                    horizon="30d",
                    expected_impact="Aprendizaje continuo y lift incremental sostenido.",
                    priority_score=round(0.68 * confidence, 2),
                )
            )
            actions.append(
                RecommendedAction(
                    action="Alinear pauta diaria con objetivo semanal de revenue y eficiencia.",
                    owner="medios",
                    horizon="24h",
                    expected_impact="Mejor pacing y menor desvío al cierre semanal.",
                    priority_score=round(0.7 * confidence, 2),
                )
            )

        # Ajuste contextual simple por deltas observados.
        if roas_delta is not None and roas_delta < -10:
            actions[0].priority_score = round(min(0.99, actions[0].priority_score + 0.08), 2)
        if spend_delta is not None and spend_delta > 20:
            actions[1].priority_score = round(min(0.99, actions[1].priority_score + 0.05), 2)
        if revenue_delta is not None and revenue_delta < 0:
            actions[2].priority_score = round(min(0.99, actions[2].priority_score + 0.05), 2)
        if revenue_target_gap is not None and revenue_target_gap < -10:
            # Si viene debajo de target, priorizar ejecución táctica en el corto plazo.
            actions[0].priority_score = round(min(0.99, actions[0].priority_score + 0.07), 2)
            actions[1].priority_score = round(min(0.99, actions[1].priority_score + 0.04), 2)

        return sorted(actions, key=lambda a: a.priority_score, reverse=True)[:3]

    def _render_required_sections(self, decision_meta: DecisionMeta) -> str:
        comparisons = decision_meta.comparisons
        wow_metrics = ((comparisons.get("week_over_week") or {}).get("metrics") or {})
        roas = (wow_metrics.get("roas") or {}).get("delta_pct")
        spend = (wow_metrics.get("gasto") or {}).get("delta_pct")
        revenue = (wow_metrics.get("revenue") or {}).get("delta_pct")
        target_metrics = ((comparisons.get("vs_target") or {}).get("metrics") or {})
        yoy_metrics = ((comparisons.get("vs_last_year") or {}).get("metrics") or {})
        rev_target_gap = (target_metrics.get("revenue") or {}).get("gap_pct")
        rev_yoy = (yoy_metrics.get("revenue") or {}).get("delta_pct")
        comps_txt = (
            f"ROAS vs semana previa: {roas}% | "
            f"Gasto: {spend}% | Revenue: {revenue}%"
            if (comparisons.get("week_over_week") or {}).get("status") == "ok"
            else "Comparativo semanal no disponible con la data actual."
        )
        target_txt = (
            f"Revenue vs target: {rev_target_gap}%"
            if (comparisons.get("vs_target") or {}).get("status") == "ok"
            else "Comparativo vs target no disponible."
        )
        yoy_txt = (
            f"Revenue vs LY: {rev_yoy}%"
            if (comparisons.get("vs_last_year") or {}).get("status") == "ok"
            else "Comparativo vs last year no disponible."
        )
        risks_txt = " | ".join(decision_meta.guardrails) if decision_meta.guardrails else "Sin riesgos críticos detectados."

        actions_lines = []
        for idx, a in enumerate(decision_meta.actions, start=1):
            actions_lines.append(
                f"{idx}) [{a.owner} - {a.horizon}] {a.action} "
                f"(Impacto: {a.expected_impact}; Prioridad: {a.priority_score})"
            )

        return (
            "Situación actual:\n"
            f"- Intento detectado: {decision_meta.intent}\n"
            f"- Freshness: {decision_meta.data_freshness}\n"
            f"- Confianza: {decision_meta.confidence_score}\n"
            f"- {comps_txt}\n"
            f"- {target_txt}\n"
            f"- {yoy_txt}\n\n"
            "Causa raíz probable:\n"
            "- Variabilidad de eficiencia por canal/campaña y/o cobertura de datos parcial.\n\n"
            "Acciones concretas priorizadas:\n"
            + "\n".join(actions_lines)
            + "\n\n"
            "Impacto estimado:\n"
            "- Ejecución disciplinada de las 3 acciones debería mejorar eficiencia y control de pacing semanal.\n\n"
            "Riesgos y guardrails:\n"
            f"- {risks_txt}"
        )

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
            intent = self._classify_intent(query)

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

            freshness = self._get_data_freshness(raw_data)
            comparisons = self._compute_gold_comparisons(cursor, raw_data)
            guardrails = self._build_guardrails(raw_data, comparisons)
            confidence = self._compute_confidence(raw_data, freshness, guardrails)
            actions = self._build_recommended_actions(intent, comparisons, confidence)
            decision_meta = DecisionMeta(
                intent=intent,
                confidence_score=confidence,
                data_freshness=freshness,
                guardrails=guardrails,
                comparisons=comparisons,
                actions=actions,
            )

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
- Incluye comparativo obligatorio vs semana previa cuando exista data.
- Cita riesgos/guardrails cuando la muestra o calidad de datos sea limitada.
- Formato obligatorio:
  1) Situación actual
  2) Causa raíz probable
  3) Acciones concretas priorizadas (exactamente 3)
     - Cada acción debe incluir: owner (medios/planning/estrategia), ventana (24h/7d/30d), impacto estimado.
  4) Impacto estimado
  5) Riesgos y guardrails
- Respuesta concisa, sin saludos."""

            prompt_safe = prompt.replace("$$", "__DD__")
            cursor.execute(
                f"SELECT SNOWFLAKE.CORTEX.COMPLETE('mistral-large2', $${prompt_safe}$$)"
            )
            row = cursor.fetchone()
            narrative = row[0].replace("__DD__", "$$") if row else "No se pudo generar respuesta."

            required_markers = [
                "Situación", "Causa", "Acciones", "Impacto", "Riesgo"
            ]
            if not all(marker.lower() in narrative.lower() for marker in required_markers):
                narrative = f"{narrative}\n\n{self._render_required_sections(decision_meta)}"

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
