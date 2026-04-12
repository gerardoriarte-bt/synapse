import { ChartConfig } from '@/types/synapse';

export type ChartCandidate = {
  config: ChartConfig;
  reason: string;
};

const looksLikeDateValue = (value: string | number): boolean => {
  const txt = String(value || '').trim();
  if (!txt) return false;
  if (/^\d{4}-\d{2}-\d{2}/.test(txt)) return true;
  if (/^\d{4}\/\d{2}\/\d{2}/.test(txt)) return true;
  return !Number.isNaN(Date.parse(txt));
};

const isMostlyTemporalAxis = (xAxis: Array<string | number>): boolean => {
  if (xAxis.length < 3) return false;
  const hits = xAxis.filter((x) => looksLikeDateValue(x)).length;
  return hits >= Math.ceil(xAxis.length * 0.7);
};

const asType = (config: ChartConfig, type: ChartConfig['type']): ChartConfig => ({
  ...config,
  type,
});

export const buildChartCandidates = (
  primary: ChartConfig | null | undefined,
  primaryReason: string
): ChartCandidate[] => {
  if (!primary) return [];

  const candidates: ChartCandidate[] = [{ config: primary, reason: primaryReason }];
  const hasMultiSeries = Array.isArray(primary.series) && primary.series.length > 1;
  if (hasMultiSeries) return candidates;

  const points = primary.x_axis.length;
  const isTemporal = isMostlyTemporalAxis(primary.x_axis);

  if (primary.type === 'donut' && points >= 2) {
    candidates.push({
      config: asType(primary, isTemporal ? 'line' : 'bar'),
      reason: isTemporal
        ? 'Vista complementaria: tendencia temporal para validar evolución.'
        : 'Vista complementaria: barras para comparar magnitudes absolutas.',
    });
  } else if (primary.type === 'bar') {
    if (points >= 2 && points <= 8) {
      candidates.push({
        config: asType(primary, 'donut'),
        reason: 'Vista complementaria: participación porcentual por categoría.',
      });
    }
    if (isTemporal) {
      candidates.push({
        config: asType(primary, 'line'),
        reason: 'Vista complementaria: tendencia temporal en línea.',
      });
    }
  } else if (primary.type === 'line' && points >= 2) {
    candidates.push({
      config: asType(primary, 'bar'),
      reason: 'Vista complementaria: comparativo de valores por corte.',
    });
  }

  const uniqueByType = new Map<ChartConfig['type'], ChartCandidate>();
  for (const candidate of candidates) {
    if (!uniqueByType.has(candidate.config.type)) {
      uniqueByType.set(candidate.config.type, candidate);
    }
  }
  return [...uniqueByType.values()].slice(0, 3);
};
