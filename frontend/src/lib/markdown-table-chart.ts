import { ChartConfig } from '@/types/synapse';

const PERIOD_HINT = /(ene|feb|mar|abr|may|jun|jul|ago|sep|oct|nov|dic|jan|apr|aug|dec|20\d{2})/i;
const EXCLUDE_METRIC_HINT = /(variaci|cambio|delta|pp|%)/i;

const toNumber = (raw: string): number | null => {
  const cleaned = raw
    .replace(/\$/g, '')
    .replace(/usd/gi, '')
    .replace(/,/g, '')
    .replace(/pp/gi, '')
    .replace(/%/g, '')
    .trim();
  if (!cleaned) return null;
  const n = Number(cleaned);
  return Number.isFinite(n) ? n : null;
};

const parseRow = (line: string): string[] => {
  const trimmed = line.trim();
  if (!trimmed.startsWith('|') || !trimmed.endsWith('|')) return [];
  return trimmed
    .slice(1, -1)
    .split('|')
    .map((s) => s.trim());
};

export const inferChartConfigFromMarkdownTable = (narrative?: string): ChartConfig | null => {
  if (!narrative) return null;
  const lines = narrative.split('\n');
  let tableStart = -1;
  for (let i = 0; i < lines.length - 1; i += 1) {
    const header = parseRow(lines[i]);
    const sep = parseRow(lines[i + 1]);
    if (
      header.length >= 3 &&
      sep.length === header.length &&
      sep.every((c) => /^:?-{3,}:?$/.test(c.replace(/\s/g, '')))
    ) {
      tableStart = i;
      break;
    }
  }
  if (tableStart < 0) return null;

  const headers = parseRow(lines[tableStart]);
  const rows: string[][] = [];
  for (let i = tableStart + 2; i < lines.length; i += 1) {
    const cols = parseRow(lines[i]);
    if (cols.length !== headers.length) break;
    rows.push(cols);
  }
  if (rows.length < 2) return null;

  const dimensionIdx = 0;
  const candidates = headers
    .map((h, idx) => ({ h, idx }))
    .filter(({ idx }) => idx !== dimensionIdx)
    .filter(({ h }) => !EXCLUDE_METRIC_HINT.test(h))
    .filter(({ idx }) => {
      let numeric = 0;
      for (const r of rows) {
        if (toNumber(r[idx]) !== null) numeric += 1;
      }
      return numeric >= Math.ceil(rows.length * 0.7);
    });

  if (candidates.length === 0) return null;
  const ranked = candidates.sort((a, b) => {
    const ah = PERIOD_HINT.test(a.h) ? 1 : 0;
    const bh = PERIOD_HINT.test(b.h) ? 1 : 0;
    return bh - ah;
  });
  const selected = ranked.slice(0, 2);
  if (selected.length === 0) return null;

  const xAxis = rows.map((r) => r[dimensionIdx]);
  const series = selected.map(({ h, idx }) => ({
    name: h,
    values: rows.map((r) => toNumber(r[idx]) ?? 0),
  }));

  return {
    type: 'bar',
    x_axis: xAxis,
    y_axis: series[0].values,
    metrics_label: series[0].name,
    x_axis_label: headers[dimensionIdx] || 'Dimensión',
    series,
  };
};
