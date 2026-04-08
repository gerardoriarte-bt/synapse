from pydantic import BaseModel
from typing import List, Dict, Optional, Any

class ChartConfig(BaseModel):
    type: str  # "bar", "line", "donut"
    x_axis: List[Any]
    y_axis: List[float]
    metrics_label: str


class RecommendedAction(BaseModel):
    action: str
    owner: str  # "medios" | "planning" | "estrategia"
    horizon: str  # "24h" | "7d" | "30d"
    expected_impact: str
    priority_score: float


class DecisionMeta(BaseModel):
    intent: str
    confidence_score: float
    data_freshness: str
    guardrails: List[str]
    comparisons: Dict[str, Any]
    actions: List[RecommendedAction]

class SynapseResponse(BaseModel):
    response_id: str
    narrative: str
    render_type: str  # "text", "chart", "table"
    chart_config: Optional[ChartConfig] = None
    raw_data: Optional[List[Dict]] = None
    decision_meta: Optional[DecisionMeta] = None
    # Metadatos opcionales cuando SYNAPSE_QUERY_MODE=cortex_analyst (SQL generado, avisos, etc.)
    cortex_analyst: Optional[Dict[str, Any]] = None
