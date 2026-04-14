"""Errores de dominio para el tablero de analítica diaria."""


class DailyDashboardError(Exception):
    """Fallo recuperable o no en la carga del tablero (capa de dominio)."""


class DailyDashboardSnowflakeError(DailyDashboardError):
    """Snowflake rechazó la consulta o la conexión falló."""
