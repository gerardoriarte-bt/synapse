export interface ChartConfig {
  type: 'bar' | 'line' | 'donut';
  x_axis: (string | number)[];
  y_axis: number[];
  metrics_label: string;
}

export interface RecommendedAction {
  action: string;
  owner: 'medios' | 'planning' | 'estrategia';
  horizon: '24h' | '7d' | '30d';
  expected_impact: string;
  priority_score: number;
}

export interface DecisionMeta {
  intent: string;
  confidence_score: number;
  data_freshness: string;
  guardrails: string[];
  comparisons: Record<string, any>;
  actions: RecommendedAction[];
}

export interface SynapseResponse {
  response_id: string;
  narrative: string;
  render_type: 'text' | 'chart' | 'table';
  chart_config?: ChartConfig;
  raw_data?: any[];
  decision_meta?: DecisionMeta;
  /** Presente si el backend usa modo Cortex Analyst */
  cortex_analyst?: Record<string, unknown>;
  /** Reenviar en el siguiente ask para continuar el hilo Cortex Agent */
  conversation_id?: string;
}
