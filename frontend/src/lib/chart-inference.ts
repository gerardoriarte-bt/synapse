import { ChartConfig } from '@/types/synapse';

const EXCLUDED_KEYS = new Set([
  '_source_dataset',
  'request_id',
  'run_id',
  'response_id',
  'conversation_id',
]);

const METRIC_PRIORITY = [
  'TOTAL_REVENUE_USD',
  'REVENUE',
  'INGRESOS_USD',
  'INGRESOS',
  'TOTAL_COST',
  'COST_USD',
  'COST',
  'GASTO_USD',
  'GASTO',
  'TOTAL_IMPRESSIONS',
  'IMPRESSIONS',
  'IMPRESIONES',
  'TOTAL_CLICKS',
  'CLICKS',
  'TOTAL_ORDERS',
  'ORDERS',
  'ORDENES',
];

const DIMENSION_PRIORITY = [
  'DATE',
  'FECHA',
  'DAY',
  'MONTH',
  'WEEK',
  'CAMPAIGN_PRIMARIO',
  'CAMPAIGN',
  'FUENTE',
  'CHANNEL',
  'PLATFORM',
  'SOURCE',
];

const toNumber = (value: unknown): number | null => {
  if (typeof value === 'number' && Number.isFinite(value)) return value;
  if (typeof value === 'string') {
    const normalized = value.replace(/,/g, '').trim();
    if (!normalized) return null;
    const parsed = Number(normalized);
    return Number.isFinite(parsed) ? parsed : null;
  }
  return null;
};

const looksLikeDate = (value: unknown): boolean => {
  if (typeof value !== 'string') return false;
  const v = value.trim();
  if (!v) return false;
  if (/^\d{4}-\d{2}-\d{2}/.test(v)) return true;
  if (/^\d{4}\/\d{2}\/\d{2}/.test(v)) return true;
  return !Number.isNaN(Date.parse(v));
};

const prettifyLabel = (raw: string): string =>
  raw
    .replace(/_/g, ' ')
    .toLowerCase()
    .replace(/\b\w/g, (m) => m.toUpperCase());

export const inferChartConfigFromRawData = (rawData?: unknown[]): ChartConfig | null => {
  if (!Array.isArray(rawData) || rawData.length < 2) return null;
  const rows = rawData.filter(
    (row): row is Record<string, unknown> =>
      typeof row === 'object' && row !== null && !Array.isArray(row)
  );
  if (rows.length < 2) return null;

  const keys = Object.keys(rows[0]).filter((k) => !EXCLUDED_KEYS.has(k));
  if (keys.length < 2) return null;

  const numericKeys = keys.filter((key) => {
    let hits = 0;
    for (const row of rows) {
      if (toNumber(row[key]) !== null) hits += 1;
    }
    return hits >= Math.ceil(rows.length * 0.5);
  });
  if (numericKeys.length === 0) return null;

  const dimensionKeys = keys.filter((k) => !numericKeys.includes(k));
  if (dimensionKeys.length === 0) return null;

  const metricKey =
    METRIC_PRIORITY.find((p) => numericKeys.includes(p)) ?? numericKeys[0];
  const dimensionKey =
    DIMENSION_PRIORITY.find((p) => dimensionKeys.includes(p)) ?? dimensionKeys[0];

  const aggregate = new Map<string, number>();
  for (const row of rows) {
    const dim = row[dimensionKey];
    const metric = toNumber(row[metricKey]);
    if (metric === null || dim === null || dim === undefined) continue;
    const label = String(dim).trim();
    if (!label) continue;
    aggregate.set(label, (aggregate.get(label) ?? 0) + metric);
  }
  if (aggregate.size < 2) return null;

  const points = [...aggregate.entries()].map(([x, y]) => ({ x, y }));
  const dateDimension = points.filter((p) => looksLikeDate(p.x)).length >= Math.ceil(points.length * 0.7);

  let type: ChartConfig['type'] = 'bar';
  if (dateDimension) type = 'line';
  else if (points.length <= 6) type = 'donut';

  if (type === 'line') {
    points.sort((a, b) => new Date(a.x).getTime() - new Date(b.x).getTime());
  } else {
    points.sort((a, b) => b.y - a.y);
  }

  const limited = points.slice(0, type === 'line' ? 30 : 12);
  return {
    type,
    x_axis: limited.map((p) => p.x),
    y_axis: limited.map((p) => Number(p.y.toFixed(2))),
    metrics_label: prettifyLabel(metricKey),
    x_axis_label: prettifyLabel(dimensionKey),
  };
};
