"""
Consultas Snowflake para el tablero de seguimiento diario (capa Repository).
Identificadores de tablas/columnas configurables vía variables de entorno.
"""

from __future__ import annotations

import os
from datetime import date
from typing import Any, Dict, List, Optional, Tuple

from services.snowflake import connect_snowflake
from services.snowflake_catalog import is_allowed_identifier
from exceptions.dashboard_exceptions import DailyDashboardSnowflakeError
from observability.structured_log import structured_log


def _gold_fq_ident(name: str, default: str) -> str:
    raw = os.getenv(name, default).strip().upper()
    if not is_allowed_identifier(raw):
        raise DailyDashboardSnowflakeError(
            f"Identificador inválido en {name}: debe coincidir con [A-Z][A-Z0-9_]*"
        )
    return raw


def _product_sales_date_column() -> Optional[str]:
    """Por defecto DATE; use NONE para desactivar el filtro por fecha en ventas por producto."""
    raw = os.getenv("SYNAPSE_DASHBOARD_PRODUCT_SALES_DATE_COLUMN", "DATE").strip().upper()
    if raw == "NONE":
        return None
    if not is_allowed_identifier(raw):
        raise DailyDashboardSnowflakeError(
            "Identificador inválido en SYNAPSE_DASHBOARD_PRODUCT_SALES_DATE_COLUMN"
        )
    return raw


def _fq_table(db: str, schema: str, table: str) -> str:
    for part, label in ((db, "SNOWFLAKE_GOLD_DATABASE"), (schema, "SNOWFLAKE_GOLD_SCHEMA"), (table, "tabla")):
        if not is_allowed_identifier(part):
            raise DailyDashboardSnowflakeError(f"Identificador inválido para {label}: {part}")
    return f"{db}.{schema}.{table}"


def _rows(cursor) -> List[Dict[str, Any]]:
    rows = cursor.fetchall()
    if not rows:
        return []
    cols = [d[0] for d in cursor.description]
    return [dict(zip(cols, r)) for r in rows]


class SnowflakeDailyAnalyticsRepository:
    """Lecturas agregadas desde Gold para el dashboard operativo diario."""

    def __init__(self) -> None:
        self._gold_db = _gold_fq_ident("SNOWFLAKE_GOLD_DATABASE", "DB_BT_UA")
        self._gold_schema = _gold_fq_ident("SNOWFLAKE_GOLD_SCHEMA", "BT_UA_MART_ANALYTICS")
        self._fct = _gold_fq_ident("SYNAPSE_DASHBOARD_FCT_TABLE", "FCT_PERFORMANCE")
        self._product_table = _gold_fq_ident(
            "SYNAPSE_DASHBOARD_PRODUCT_SALES_TABLE", "VENTAS_PRODUCTOS_FUENTE"
        )
        self._product_name_col = _gold_fq_ident(
            "SYNAPSE_DASHBOARD_PRODUCT_NAME_COLUMN", "NOMBRE_PRODUCTO_POR_ID_PRODUCTO"
        )
        self._product_date_col = _product_sales_date_column()
        self._fct_fq = _fq_table(self._gold_db, self._gold_schema, self._fct)
        self._product_fq = _fq_table(self._gold_db, self._gold_schema, self._product_table)

    def fetch_summary(self, start: date, end: date) -> Dict[str, Any]:
        sql = f"""
            SELECT
                COALESCE(SUM(COST_USD), 0) AS GASTO_USD,
                COALESCE(SUM(INGRESOS_USD), 0) AS REVENUE_USD,
                COALESCE(SUM(ORDENES_VENDIDAS), 0) AS ORDENES,
                COALESCE(SUM(UNIDADES_VENDIDAS), 0) AS UNIDADES,
                COALESCE(SUM(CLICKS), 0) AS CLICKS,
                COALESCE(SUM(IMPRESSIONS), 0) AS IMPRESIONES,
                ROUND(
                    COALESCE(SUM(INGRESOS_USD), 0) / NULLIF(SUM(COST_USD), 0),
                    4
                ) AS ROAS
            FROM {self._fct_fq}
            WHERE DATE >= %s AND DATE <= %s
        """
        return self._one_row(sql, (start, end), "fetch_summary")

    def fetch_top_products_by_units(
        self, start: date, end: date, limit: int
    ) -> Tuple[List[Dict[str, Any]], bool]:
        """
        Top productos por unidades vendidas en el rango.
        Si no hay columna de fecha configurada, agrega todo el histórico disponible en la tabla
        (sigue siendo datos reales de Snowflake; el front muestra meta.date_filter_applied).
        """
        name_col = self._product_name_col
        date_col = self._product_date_col
        date_filtered = date_col is not None

        if date_filtered:
            where_date = f"AND {date_col} >= %s AND {date_col} <= %s"
            params: Tuple[Any, ...] = (start, end)
            sql = f"""
                SELECT
                    {name_col} AS PRODUCTO,
                    COALESCE(SUM(UNIDADES_VENDIDAS), 0) AS UNIDADES_VENDIDAS,
                    COALESCE(SUM(INGRESOS_USD), 0) AS REVENUE_USD,
                    COUNT(DISTINCT ID_CLIENTE) AS ORDENES
                FROM {self._product_fq}
                WHERE {name_col} IS NOT NULL
                  {where_date}
                GROUP BY 1
                ORDER BY UNIDADES_VENDIDAS DESC NULLS LAST
                LIMIT {limit}
            """
        else:
            params = ()
            sql = f"""
                SELECT
                    {name_col} AS PRODUCTO,
                    COALESCE(SUM(UNIDADES_VENDIDAS), 0) AS UNIDADES_VENDIDAS,
                    COALESCE(SUM(INGRESOS_USD), 0) AS REVENUE_USD,
                    COUNT(DISTINCT ID_CLIENTE) AS ORDENES
                FROM {self._product_fq}
                WHERE {name_col} IS NOT NULL
                GROUP BY 1
                ORDER BY UNIDADES_VENDIDAS DESC NULLS LAST
                LIMIT {limit}
            """

        data = self._all_rows(sql, params, "fetch_top_products_by_units")
        return data, date_filtered

    def fetch_product_sales_period_totals(self, start: date, end: date) -> Dict[str, Any]:
        """
        Suma de unidades e ingresos en VENTAS_PRODUCTOS_FUENTE para el mismo rango de fechas
        que el ranking (todas las líneas con producto no nulo), no solo el top N.
        """
        name_col = self._product_name_col
        date_col = self._product_date_col

        if date_col:
            sql = f"""
                SELECT
                    COALESCE(SUM(UNIDADES_VENDIDAS), 0) AS UNIDADES_VENDIDAS,
                    COALESCE(SUM(INGRESOS_USD), 0) AS REVENUE_USD,
                    COUNT(DISTINCT {name_col}) AS PRODUCTOS_DISTINTOS
                FROM {self._product_fq}
                WHERE {name_col} IS NOT NULL
                  AND {date_col} >= %s AND {date_col} <= %s
            """
            params: Tuple[Any, ...] = (start, end)
        else:
            sql = f"""
                SELECT
                    COALESCE(SUM(UNIDADES_VENDIDAS), 0) AS UNIDADES_VENDIDAS,
                    COALESCE(SUM(INGRESOS_USD), 0) AS REVENUE_USD,
                    COUNT(DISTINCT {name_col}) AS PRODUCTOS_DISTINTOS
                FROM {self._product_fq}
                WHERE {name_col} IS NOT NULL
            """
            params = ()

        return self._one_row(sql, params, "fetch_product_sales_period_totals")

    def fetch_active_campaigns_period_totals(self, start: date, end: date) -> Dict[str, Any]:
        """Agregado del periodo sobre el mismo universo que campañas activas (sin límite de filas)."""
        sql = f"""
            SELECT
                COALESCE(SUM(ingresos), 0) AS INGRESOS_USD_PERIODO,
                COALESCE(SUM(gasto), 0) AS GASTO_USD_PERIODO,
                COALESCE(SUM(ordenes), 0) AS ORDENES_PERIODO,
                ROUND(
                    COALESCE(SUM(ingresos), 0) / NULLIF(SUM(gasto), 0),
                    4
                ) AS ROAS,
                COUNT(*) AS CAMPANAS_DISTINTAS
            FROM (
                SELECT
                    COALESCE(SUM(INGRESOS_USD), 0) AS ingresos,
                    COALESCE(SUM(COST_USD), 0) AS gasto,
                    COALESCE(SUM(ORDENES_VENDIDAS), 0) AS ordenes
                FROM {self._fct_fq}
                WHERE DATE >= %s AND DATE <= %s
                GROUP BY COALESCE(FUENTE, 'SIN_FUENTE'), COALESCE(CAMPAIGN_PRIMARIO, 'SIN_CAMPAÑA')
                HAVING SUM(COALESCE(COST_USD, 0)) > 0
                    OR SUM(COALESCE(CLICKS, 0)) > 0
                    OR SUM(COALESCE(IMPRESSIONS, 0)) > 0
                    OR SUM(COALESCE(ORDENES_VENDIDAS, 0)) > 0
            ) t
        """
        return self._one_row(sql, (start, end), "fetch_active_campaigns_period_totals")

    def fetch_top_campaigns_by_revenue(
        self, start: date, end: date, limit: int
    ) -> List[Dict[str, Any]]:
        sql = f"""
            SELECT
                COALESCE(CAMPAIGN_PRIMARIO, 'SIN_CAMPAÑA') AS CAMPAIGN_PRIMARIO,
                COALESCE(FUENTE, 'SIN_FUENTE') AS FUENTE,
                COALESCE(SUM(INGRESOS_USD), 0) AS REVENUE_USD,
                COALESCE(SUM(ORDENES_VENDIDAS), 0) AS ORDENES,
                COALESCE(SUM(COST_USD), 0) AS GASTO_USD,
                COALESCE(SUM(CLICKS), 0) AS CLICKS,
                COALESCE(SUM(IMPRESSIONS), 0) AS IMPRESIONES,
                ROUND(
                    COALESCE(SUM(INGRESOS_USD), 0) / NULLIF(SUM(COST_USD), 0),
                    4
                ) AS ROAS
            FROM {self._fct_fq}
            WHERE DATE >= %s AND DATE <= %s
            GROUP BY 1, 2
            ORDER BY REVENUE_USD DESC NULLS LAST
            LIMIT {limit}
        """
        return self._all_rows(sql, (start, end), "fetch_top_campaigns_by_revenue")

    def fetch_active_campaigns_detail(
        self, start: date, end: date, row_cap: int
    ) -> List[Dict[str, Any]]:
        """Campañas con actividad en el rango (misma lógica de 'activas' que el servicio legacy)."""
        sql = f"""
            SELECT
                COALESCE(FUENTE, 'SIN_FUENTE') AS FUENTE,
                COALESCE(CAMPAIGN_PRIMARIO, 'SIN_CAMPAÑA') AS CAMPAIGN_PRIMARIO,
                MIN(DATE) AS FECHA_PRIMERA_ACTIVIDAD,
                MAX(DATE) AS FECHA_ULTIMA_ACTIVIDAD,
                COALESCE(SUM(INGRESOS_USD), 0) AS INGRESOS_USD_PERIODO,
                COALESCE(SUM(COST_USD), 0) AS GASTO_USD_PERIODO,
                COALESCE(SUM(ORDENES_VENDIDAS), 0) AS ORDENES_PERIODO,
                COALESCE(SUM(UNIDADES_VENDIDAS), 0) AS UNIDADES_PERIODO,
                COALESCE(SUM(CLICKS), 0) AS CLICKS_PERIODO,
                COALESCE(SUM(IMPRESSIONS), 0) AS IMPRESIONES_PERIODO,
                ROUND(
                    COALESCE(SUM(INGRESOS_USD), 0) / NULLIF(SUM(COST_USD), 0),
                    4
                ) AS ROAS
            FROM {self._fct_fq}
            WHERE DATE >= %s AND DATE <= %s
            GROUP BY 1, 2
            HAVING SUM(COALESCE(COST_USD, 0)) > 0
                OR SUM(COALESCE(CLICKS, 0)) > 0
                OR SUM(COALESCE(IMPRESSIONS, 0)) > 0
                OR SUM(COALESCE(ORDENES_VENDIDAS, 0)) > 0
            ORDER BY INGRESOS_USD_PERIODO DESC NULLS LAST, GASTO_USD_PERIODO DESC NULLS LAST
            LIMIT {row_cap}
        """
        return self._all_rows(sql, (start, end), "fetch_active_campaigns_detail")

    def _all_rows(
        self, sql: str, params: Tuple[Any, ...], function: str
    ) -> List[Dict[str, Any]]:
        try:
            conn = connect_snowflake()
            try:
                cur = conn.cursor()
                try:
                    cur.execute(sql, params)
                    return _rows(cur)
                finally:
                    cur.close()
            finally:
                conn.close()
        except Exception as e:
            structured_log(
                "error",
                module=__name__,
                function=function,
                message="snowflake_query_failed",
                fields={"error": str(e)},
            )
            raise DailyDashboardSnowflakeError(str(e)) from e

    def _one_row(
        self, sql: str, params: Tuple[Any, ...], function: str
    ) -> Dict[str, Any]:
        rows = self._all_rows(sql, params, function)
        return rows[0] if rows else {}
