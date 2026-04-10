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
  'grafica',
  'gráfica',
  'graficar',
  'grafico',
  'gráfico',
  'visualiza',
  'visualización',
  'visualizar',
  'fuentes',
  'chart',
  'graph',
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

const SHARE_KEYWORDS = [
  'porcentaje',
  'porcentual',
  'participacion',
  'participación',
  'distribucion',
  'distribución',
  'mix',
  'composicion',
  'composición',
  'share',
  'contribucion',
  'contribución',
];

const TREND_KEYWORDS = ['tendencia', 'evolucion', 'evolución', 'diario', 'mensual', 'semanal', 'timeline'];

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
  explicit: boolean,
  semanticOverride = false
): string => {
  if (semanticOverride && type === 'donut') {
    return `Se eligió donut por semántica de participación/distribución detectada (confianza ${Math.round(
      confidence * 100
    )}%).`;
  }
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

const shouldPreferDonut = (text: string, config: ChartConfig): boolean => {
  const lower = (text || '').toLowerCase();
  if (!SHARE_KEYWORDS.some((k) => lower.includes(k))) return false;
  if (TREND_KEYWORDS.some((k) => lower.includes(k))) return false;
  if (config.type === 'line') return false;
  if (Array.isArray(config.series) && config.series.length > 1) return false;
  if (config.x_axis.length < 2 || config.x_axis.length > 8) return false;
  if (config.y_axis.some((v) => v < 0)) return false;
  return true;
};

export const resolveAutoChartIntent = ({
  rawData,
  narrative,
  explicitChartConfig,
}: IntentInput): IntentResult => {
  const lowerText = (narrative || '').toLowerCase();
  if (explicitChartConfig) {
    const semanticDonut = shouldPreferDonut(lowerText, explicitChartConfig);
    const normalizedExplicit = semanticDonut
      ? { ...explicitChartConfig, type: 'donut' as const }
      : explicitChartConfig;
    return {
      shouldRender: true,
      confidence: 1,
      reason: buildReason(normalizedExplicit.type, 1, true, semanticDonut),
      chartConfig: normalizedExplicit,
    };
  }

  const inferred = inferChartConfigFromRawData(rawData);
  const markdownInferred = !inferred ? inferChartConfigFromMarkdownTable(narrative) : null;
  const selectedBase = inferred ?? markdownInferred;
  const semanticDonut = selectedBase ? shouldPreferDonut(lowerText, selectedBase) : false;
  const selected =
    selectedBase && semanticDonut ? ({ ...selectedBase, type: 'donut' as const } as ChartConfig) : selectedBase;

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
  const hasIntentKeyword = INTENT_KEYWORDS.some((k) => lowerText.includes(k));

  let score = 0;
  score += inferred ? 0.45 : 0.42; // inferencia desde raw_data o markdown
  if (rows >= 3) score += 0.15;
  if (xCount >= 3) score += 0.12;
  if (yVar > 0) score += 0.1;
  if (hasIntentKeyword) score += 0.18;
  if (!inferred && markdownInferred && xCount >= 3) score += 0.12;

  // Evita auto-chart para distribuciones de muy pocos puntos sin intención.
  if (xCount < 2) score = 0;
  if (xCount === 2 && !hasIntentKeyword) score -= 0.1;

  const confidence = clamp01(score);
  const threshold = markdownInferred ? 0.55 : 0.65;
  const shouldRender = confidence >= threshold;

  return {
    shouldRender,
    confidence,
    reason: buildReason(selected.type, confidence, false, semanticDonut),
    chartConfig: shouldRender ? selected : null,
  };
};
