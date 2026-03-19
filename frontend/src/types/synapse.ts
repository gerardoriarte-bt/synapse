export interface ChartConfig {
  type: 'bar' | 'line' | 'donut';
  x_axis: (string | number)[];
  y_axis: number[];
  metrics_label: string;
}

export interface SynapseResponse {
  response_id: string;
  narrative: string;
  render_type: 'text' | 'chart' | 'table';
  chart_config?: ChartConfig;
  raw_data?: any[];
}
