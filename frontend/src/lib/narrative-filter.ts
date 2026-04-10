const ENGLISH_NOISE_PATTERNS = [
  /^the user is asking/i,
  /^the question is clear/i,
  /^i can answer .*sql/i,
  /^skill:\s*system_chart_workflow/i,
  /^description:\s*chart generation workflow/i,
  /^instructions$/i,
  /^chart workflow$/i,
];

const ENGLISH_MARKERS = [
  ' the ',
  ' and ',
  ' with ',
  ' for ',
  ' share ',
  ' revenue ',
  ' chart ',
  ' sql ',
];

const SPANISH_MARKERS = [
  ' el ',
  ' la ',
  ' los ',
  ' las ',
  ' de ',
  ' para ',
  ' con ',
  ' porcentaje ',
  ' participación ',
  ' ingresos ',
];

const markerScore = (text: string, markers: string[]): number => {
  const t = ` ${text.toLowerCase()} `;
  return markers.reduce((acc, m) => (t.includes(m) ? acc + 1 : acc), 0);
};

export const keepSpanishFragments = (fragments: string[], narrative: string, limit = 2): string[] => {
  const narrativeNorm = (narrative || '').trim().toLowerCase();
  const kept: string[] = [];
  const seen = new Set<string>();

  for (const raw of fragments || []) {
    const txt = (raw || '').trim();
    if (!txt) continue;
    if (ENGLISH_NOISE_PATTERNS.some((p) => p.test(txt))) continue;

    const low = txt.toLowerCase();
    if (narrativeNorm && (low === narrativeNorm || low.includes(narrativeNorm) || narrativeNorm.includes(low))) {
      continue;
    }

    const en = markerScore(txt, ENGLISH_MARKERS);
    const es = markerScore(txt, SPANISH_MARKERS);
    if (en >= 2 && en > es) continue;

    if (seen.has(low)) continue;
    seen.add(low);
    kept.push(txt);
    if (kept.length >= limit) break;
  }
  return kept;
};
