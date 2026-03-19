from pydantic import BaseModel
from typing import List, Dict, Optional, Any

class ChartConfig(BaseModel):
    type: str  # "bar", "line", "donut"
    x_axis: List[Any]
    y_axis: List[float]
    metrics_label: str

class SynapseResponse(BaseModel):
    response_id: str
    narrative: str
    render_type: str  # "text", "chart", "table"
    chart_config: Optional[ChartConfig] = None
    raw_data: Optional[List[Dict]] = None
