import { ChartConfig } from '@/types/synapse';

type ShareHighlight = {
  label: string;
  value: number;
  pct: number;
};

export const buildDonutShareHighlights = (
  config?: ChartConfig | null,
  limit = 5
): ShareHighlight[] => {
  if (!config || config.type !== 'donut') return [];
  const points = config.x_axis.map((x, idx) => ({
    label: String(x || '').trim(),
    value: Number(config.y_axis[idx] ?? 0),
  }));
  const valid = points.filter((p) => p.label && Number.isFinite(p.value) && p.value >= 0);
  if (valid.length < 2) return [];
  const total = valid.reduce((acc, p) => acc + p.value, 0);
  if (total <= 0) return [];

  return valid
    .map((p) => ({
      ...p,
      pct: (p.value / total) * 100,
    }))
    .sort((a, b) => b.pct - a.pct)
    .slice(0, limit);
};
