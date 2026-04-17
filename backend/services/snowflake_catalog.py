"""
Catálogo de tablas/vistas en el mart (por defecto DB_BT_TERPEL_COMBS.BT_TERPEL_COMBS_MART_ANALYTICS).
Solo identificadores en mayúsculas; el SQL se arma con comillas en el servicio.
"""
from __future__ import annotations

import os
import re
from typing import Dict, List, Sequence, Tuple

# (tabla_o_vista, keywords para scoring, peso base por match)
GOLD_DATASETS: List[Tuple[str, Sequence[str], float]] = [
    (
        "VW_DATATERPEL_PAUTA_METAS_VS_RESULTADOS",
        (
            "META",
            "METAS",
            "RESULTADO",
            "RESULTADOS",
            "PAUTA",
            "KPI",
            "TERPEL",
            "OBJETIVO",
            "TARGET",
            "BENCHMARK",
            "DESEMPE",
            "VS ",
        ),
        1.15,
    ),
    (
        "PAID_MEDIA_CHUNKS",
        ("PAID", "PAGAD", "MEDIA", "CHUNK", "PAUTA", "ANUNCIO", "CAMPAÑA", "CAMPAIGN", "DISPLAY"),
        1.05,
    ),
    (
        "PAID_MEDIA_TEXTO_RAW",
        ("REPORTE", "TEXTO", "PAID", "PDF", "MEDIOS", "INSIGHT"),
        0.95,
    ),
    (
        "ORGANIC_SM_CHUNKS",
        ("ORGÁNICO", "ORGANICO", "SOCIAL", "INSTAGRAM", "FACEBOOK", "COMMUNITY", "ORGANIC"),
        1.0,
    ),
    ("FCT_PERFORMANCE", ("ROAS", "GASTO", "COST", "PERFORMANCE", "PAUTA", "ADS", "ECOM", "INGRESO", "REVENUE", "CONVERSI", "CLICK", "IMPRESION", "CAMPAÑA", "CAMPAIGN", "FUENTE", "PLATAFORMA"), 1.0),
    ("GLD_PAID_MEDIA", ("PAID", "PAGAD", "MEDIA", "PAUTA", "CONSOLIDAD", "ATRIBU", "PERFORMANCE", "BRAND", "SCOPE"), 1.1),
    ("GLD_ATRIBUCION_CONSOLIDADA", ("ATRIBU", "ATTRIBUTION", "CONSOLIDAD", "ADOBE", "WEB"), 1.0),
    ("FCT_ATRIBUCION_CONSOLIDADA", ("ATRIBU", "MAESTR", "GRAIN", "SCOPE_STRATEGY"), 0.9),
    ("RESULTADOS_PLATAFORMA_SITIO_WEB", ("ADOBE", "SITIO", "WEB", "SESION", "VISIT", "BOUNCE", "PAGEVIEW", "ECOMMERCE", "ANALYTICS"), 1.0),
    ("FCT_BRAND_DETALLE", ("BRAND", "MARCA", "CPM", "CPC", "DETALLE", "DIARIO", "PLATAFORMA"), 0.95),
    ("FCT_BRAND_RESUMEN", ("BRAND", "MARCA", "MENSUAL", "RESUMEN", "TRACKER"), 0.95),
    ("GLD_BRAND_BUDGET", ("BRAND", "PRESUPUEST", "BUDGET", "OVERSPEND", "VIDEO", "AGENCY", "FEE"), 0.95),
    ("FCT_OTROS_CANALES", ("AFILIAD", "EMAIL", "SEO", "REFERID", "DIRECTO", "CRITEO", "SMS", "ORGÁNICO", "ORGANICO", "OTROS CANALES"), 1.0),
    ("GLD_ORGANIC_CHANNELS", ("ORGÁNICO", "ORGANICO", "SEO", "EMAIL", "AFILIAD", "NO PAGAD", "TRÁFICO", "TRAFICO"), 1.0),
    ("FB_BRAND_LIFT", ("BRAND LIFT", "RECALL", "FAVORABIL", "META BRAND", "FACEBOOK BRAND"), 1.0),
    ("FB_CONVERSION_LIFT", ("CONVERSION LIFT", "LIFT", "INCREMENTAL", "META CONVERSION"), 1.0),
    ("VENTAS_PRODUCTOS_FUENTE", ("PRODUCTO", "SKU", "ITEM", "VENTA", "UNIDAD", "INGRESO"), 1.0),
    ("VENTAS_CLIENTES_PLATAFORMA", ("CLIENTE", "USUARIO", "COMPORTAMIENTO", "FUNNEL", "CHECKOUT", "CARRITO"), 0.95),
    ("VENTAS_ORGANICAS_Y_ID_CLIENTE", ("ORGÁNICO", "ORGANICO", "CLIENTE", "SEO", "DIRECTO", "SIN PAGO"), 0.95),
    ("VW_COSTOS_CAMPANAS", ("COSTO", "INVERSI", "INVERSIÓN", "MEDIA COST", "AD SET"), 1.0),
    ("VW_ECOMM_DAILY_SOT", ("DAILY", "DIARIO", "SOT", "TARGET", "AGENCY", "ECOMM", "DASHBOARD"), 1.0),
    ("GSCC2_MRT_UA_BT_MX_MRKP", ("MARKUP", "MRKP", "FEE", "AGENCIA", "FACTUR"), 0.9),
    ("DQ_VALIDACION_DIARIA", ("CALIDAD", "QUALITY", "DQ", "RECONCILI", "BRONZE", "SILVER", "GOLD"), 1.0),
    ("GLD_UA_MX_HEALTH_INVENTORY", ("INVENTARIO", "STOCK", "DISPONIB", "PRECIO", "PRODUCTO", "HEALTH"), 0.95),
    ("GLD_SOCIAL_MEDIA_FOLLOWERS", ("FOLLOWER", "SEGUIDOR", "INSTAGRAM", "TIKTOK", "COMUNIDAD"), 1.0),
    ("GLD_SOCIAL_MEDIA_POSTS", ("POST", "CONTENIDO", "VIDEO", "REEL", "COMENTARIO", "SENTIMENT"), 1.0),
    ("GLD_SOCIAL_MEDIA_PROFILE_METRICS", ("PERFIL", "SOCIAL", "ALCANCE", "REACH", "INTERACCI"), 0.9),
    ("RESUMEN_RESULTADOS_FY26", ("FY26", "FISCAL", "INVERSION_BRAND", "INVERSION_ECOM", "MENSUAL"), 1.0),
    ("SV_SYNAPSE_UA_ANALYTICS", ("SYNAPSE", "RESUMEN", "ANALYTICS", "UA", "CONSOLIDAD"), 1.0),
    ("SYNAPSE_UA", ("SYNAPSE", "AGENTE", "DOCUMENTAC", "ALCANCE", "TABLAS"), 0.5),
    ("FORMULAS_MARKETING", ("FÓRMULA", "FORMULA", "KPI", "DEFINICI", "MÉTRICA", "METRICA"), 0.8),
    ("REPORTES_TEXTO_RAW", ("REPORTE", "PDF", "TEXTO", "CLIENTE"), 0.85),
    ("REPORTES_CHUNKS", ("REPORTE", "CHUNK", "CORTEX", "BÚSQUEDA"), 0.8),
    ("BUENTIPO_TEXTO_RAW", ("BUENTIPO", "BUEN TIPO", "PDF"), 0.9),
    ("BUENTIPO_CHUNKS", ("BUENTIPO", "CHUNK", "BÚSQUEDA", "CORTEX"), 0.85),
    ("ECOM_TEXTO_RAW", ("ECOM", "E-COMM", "PDF", "REPORTE ECOMM"), 0.85),
    ("ECOM_CHUNKS", ("ECOM", "CHUNK", "CORTEX", "BÚSQUEDA"), 0.8),
    ("SOV_CHUNKS", ("SOV", "SHARE OF VOICE", "PARTICIPACIÓN", "MERCADO"), 0.95),
]

# Cuando la pregunta no matchea keywords, se priorizan objetos presentes en el mart Terpel por defecto.
DEFAULT_DATASET_ORDER: Tuple[str, ...] = (
    "VW_DATATERPEL_PAUTA_METAS_VS_RESULTADOS",
    "PAID_MEDIA_CHUNKS",
    "PAID_MEDIA_TEXTO_RAW",
    "FORMULAS_MARKETING",
    "ORGANIC_SM_CHUNKS",
    "FCT_PERFORMANCE",
    "GLD_PAID_MEDIA",
)

# Tablas muy grandes: muestreo para no full-scan.
HEAVY_TABLES_SAMPLE_SQL: Dict[str, str] = {
    "VENTAS_PRODUCTOS_FUENTE": (
        "SELECT * FROM {fq} TABLESAMPLE BERNOULLI (0.02) LIMIT {limit}"
    ),
}

IDENT_RE = re.compile(r"^[A-Z][A-Z0-9_]*$")


def is_allowed_identifier(name: str) -> bool:
    return bool(name and IDENT_RE.match(name))


def rank_datasets_for_query(query: str, max_tables: int) -> List[str]:
    """Devuelve nombres de dataset ordenados por relevancia."""
    q = query.upper()
    scores: Dict[str, float] = {}

    for table, keywords, base_weight in GOLD_DATASETS:
        s = 0.0
        for kw in keywords:
            if kw.upper() in q:
                s += base_weight
        if s > 0:
            scores[table] = scores.get(table, 0.0) + s

    if not scores:
        ordered = [t for t in DEFAULT_DATASET_ORDER if is_allowed_identifier(t)]
        return ordered[:max_tables]

    ranked = sorted(scores.keys(), key=lambda t: scores[t], reverse=True)
    # Asegurar diversidad: incluir al menos un default si el top es muy estrecho
    out: List[str] = []
    for t in ranked:
        if t not in out and is_allowed_identifier(t):
            out.append(t)
        if len(out) >= max_tables:
            break
    for t in DEFAULT_DATASET_ORDER:
        if len(out) >= max_tables:
            break
        if t not in out and is_allowed_identifier(t):
            out.append(t)
    return out[:max_tables]


def max_catalog_fetches() -> int:
    try:
        return max(3, min(12, int(os.getenv("SNOWFLAKE_CATALOG_MAX_TABLES", "8"))))
    except ValueError:
        return 8


def sample_row_limit() -> int:
    try:
        return max(5, min(50, int(os.getenv("SNOWFLAKE_CATALOG_ROW_LIMIT", "18"))))
    except ValueError:
        return 18
