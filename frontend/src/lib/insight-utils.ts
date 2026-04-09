import { SynapseResponse } from '@/types/synapse';

export type ComparisonCard = {
  id: string;
  title: string;
  statusLabel: string;
  statusClass: string;
  detail: string | null;
};

export type EvidenceSnapshot = {
  rowCount: number;
  datasetsText: string;
  periodText: string;
};

export const buildExecutiveHeadline = (narrative: string, fallback: string): string => {
  const lines = narrative
    .replace(/\r/g, '')
    .split('\n')
    .map((line) => line.trim())
    .filter(Boolean);

  const candidate = lines.find(
    (line) => !line.startsWith('#') && !line.startsWith('-') && !/^\d+[\.\)]/.test(line)
  );

  if (!candidate) {
    return fallback;
  }

  return candidate.length > 160 ? `${candidate.slice(0, 157)}...` : candidate;
};

export const buildComparisonCards = (
  decisionMeta?: SynapseResponse['decision_meta']
): ComparisonCard[] => {
  if (!decisionMeta?.comparisons) return [];

  const mapping = [
    { id: 'week_over_week', title: 'Vs semana previa' },
    { id: 'vs_target', title: 'Vs objetivo' },
    { id: 'vs_last_year', title: 'Vs año anterior' },
  ];

  return mapping
    .map(({ id, title }) => {
      const entry = decisionMeta.comparisons?.[id];
      if (!entry || typeof entry !== 'object') return null;
      const entryObj = entry as Record<string, unknown>;

      const status = String(entryObj.status || 'unavailable').toLowerCase();
      const ok = status === 'ok';

      return {
        id,
        title,
        statusLabel: ok ? 'Disponible' : 'No disponible',
        statusClass: ok ? 'text-emerald-300' : 'text-amber-300',
        detail: entryObj.reason ? String(entryObj.reason) : null,
      };
    })
    .filter(Boolean) as ComparisonCard[];
};

export const buildEvidenceSnapshot = (rawData?: unknown[]): EvidenceSnapshot => {
  const rows = Array.isArray(rawData) ? rawData : [];
  const records = rows.filter(
    (row): row is Record<string, unknown> => typeof row === 'object' && row !== null
  );

  const datasets = Array.from(
    new Set(
      records
        .map((row) => row._source_dataset)
        .filter((value): value is string => typeof value === 'string' && value.length > 0)
    )
  );

  const dates = records
    .map((row) => row.DATE)
    .filter((value): value is string | number => typeof value === 'string' || typeof value === 'number')
    .map((value) => String(value))
    .sort();

  return {
    rowCount: records.length,
    datasetsText: datasets.length > 0 ? datasets.slice(0, 3).join(', ') : 'No especificado',
    periodText: dates.length > 0 ? `${dates[0]} a ${dates[dates.length - 1]}` : 'No especificado',
  };
};

export const buildLimitations = (decisionMeta?: SynapseResponse['decision_meta']): string[] => {
  if (!decisionMeta) return [];

  const limitations: string[] = [];

  if (Array.isArray(decisionMeta.guardrails)) {
    limitations.push(...decisionMeta.guardrails.map((item) => String(item)));
  }

  const comparisons = decisionMeta.comparisons || {};
  for (const key of ['week_over_week', 'vs_target', 'vs_last_year']) {
    const value = comparisons[key];
    if (value && typeof value === 'object') {
      const valueObj = value as Record<string, unknown>;
      if (String(valueObj.status || '').toLowerCase() !== 'ok' && valueObj.reason) {
        limitations.push(String(valueObj.reason));
      }
    }
  }

  return Array.from(new Set(limitations)).slice(0, 5);
};

export const formatConfidence = (confidence?: number) => {
  if (typeof confidence !== 'number') return 'No especificada';
  return `${Math.round(confidence * 100)}%`;
};

export const formatFreshness = (freshness?: string) => {
  if (!freshness) return 'No especificada';
  return freshness.replace(/_/g, ' ');
};
