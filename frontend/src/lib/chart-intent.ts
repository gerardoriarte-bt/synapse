import { ChartConfig } from '@/types/synapse';
import { inferChartConfigFromRawData } from './chart-inference';
import { inferChartConfigFromMarkdownTable } from './markdown-table-chart';

type IntentResult = {
  shouldRender: boolean;
  confidence: number;
  reason: string;
  chartConfig: ChartConfig | null;
};

type IntentInput = {
  rawData?: Array<Record<string, unknown>>;
  narrative?: string;
  explicitChartConfig?: ChartConfig;
};

const INTENT_KEYWORDS = [
  'analiza',
  'analisis',
  'análisis',
  'tendencia',
  'evolucion',
  'evolución',
  'comparativo',
  'comparar',
  'top',
  'ranking',
  'participacion',
  'participación',
  'mix',
  'distribution',
  'trend',
  'compare',
  'breakdown',
];

const clamp01 = (v: number): number => Math.max(0, Math.min(1, v));

const variance = (values: number[]): number => {
  if (values.length < 2) return 0;
  const mean = values.reduce((acc, v) => acc + v, 0) / values.length;
  const sum = values.reduce((acc, v) => acc + (v - mean) ** 2, 0);
  return sum / values.length;
};

const buildReason = (
  type: ChartConfig['type'],
  confidence: number,
  explicit: boolean
): string => {
  if (explicit) return 'Se muestra el gráfico configurado en la respuesta.';
  if (type === 'line') {
    return `Se eligió línea por patrón temporal detectado (confianza ${Math.round(
      confidence * 100
    )}%).`;
  }
  if (type === 'donut') {
    return `Se eligió donut por distribución de categorías compacta (confianza ${Math.round(
      confidence * 100
    )}%).`;
  }
  return `Se eligió barras por comparativo entre categorías (confianza ${Math.round(
    confidence * 100
  )}%).`;
};

export const resolveAutoChartIntent = ({
  rawData,
  narrative,
  explicitChartConfig,
}: IntentInput): IntentResult => {
  if (explicitChartConfig) {
    return {
      shouldRender: true,
      confidence: 1,
      reason: buildReason(explicitChartConfig.type, 1, true),
      chartConfig: explicitChartConfig,
    };
  }

  const inferred = inferChartConfigFromRawData(rawData);
  const markdownInferred = !inferred ? inferChartConfigFromMarkdownTable(narrative) : null;
  const selected = inferred ?? markdownInferred;

  if (!selected) {
    return {
      shouldRender: false,
      confidence: 0,
      reason: 'No hay estructura suficiente para graficar.',
      chartConfig: null,
    };
  }

  const rows = Array.isArray(rawData) ? rawData.length : 0;
  const xCount = selected.x_axis.length;
  const yVar = variance(selected.y_axis);
  const lowerText = (narrative || '').toLowerCase();
  const hasIntentKeyword = INTENT_KEYWORDS.some((k) => lowerText.includes(k));

  let score = 0;
  score += inferred ? 0.45 : 0.38; // inferencia desde raw_data o markdown
  if (rows >= 3) score += 0.15;
  if (xCount >= 3) score += 0.12;
  if (yVar > 0) score += 0.1;
  if (hasIntentKeyword) score += 0.18;

  // Evita auto-chart para distribuciones de muy pocos puntos sin intención.
  if (xCount < 2) score = 0;
  if (xCount === 2 && !hasIntentKeyword) score -= 0.1;

  const confidence = clamp01(score);
  const shouldRender = confidence >= 0.65;

  return {
    shouldRender,
    confidence,
    reason: buildReason(selected.type, confidence, false),
    chartConfig: shouldRender ? selected : null,
  };
};
