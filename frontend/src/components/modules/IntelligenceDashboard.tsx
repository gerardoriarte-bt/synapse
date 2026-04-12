import React from 'react';
import { BarChart3 } from 'lucide-react';
import { SynapseResponse } from '@/types/synapse';
import { ChartModule } from './ChartModule';
import { TableModule } from './TableModule';
import { inferChartConfigFromRawData } from '@/lib/chart-inference';
import { MarkdownNarrative } from './MarkdownNarrative';
import { resolveAutoChartIntent } from '@/lib/chart-intent';
import { keepSpanishFragments } from '@/lib/narrative-filter';
import { buildDonutShareHighlights } from '@/lib/chart-insight';
import { buildChartCandidates } from '@/lib/chart-multi';

interface Props {
  data: SynapseResponse | null;
  isLoading: boolean;
}

export const IntelligenceDashboard: React.FC<Props> = ({ data, isLoading }) => {
  if (isLoading) return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-6 animate-pulse">
      {[1, 2, 3].map(i => (
        <div key={i} className="h-64 bg-zinc-900/50 border border-zinc-800 rounded-3xl" />
      ))}
    </div>
  );

  if (!data) return (
    <div className="flex flex-col items-center justify-center py-20 text-center space-y-4">
      <div className="w-16 h-16 rounded-full bg-zinc-900 border border-zinc-800 flex items-center justify-center">
        <BarChart3 className="text-zinc-600" size={32} />
      </div>
      <h2 className="text-xl font-bold text-white">Sin lectura estratégica disponible</h2>
      <p className="text-zinc-500 max-w-sm font-medium italic">
        Realiza una consulta o reutiliza la última respuesta del chat para ver esta vista.
      </p>
    </div>
  );

  const inferredChartConfig = data.chart_config ?? inferChartConfigFromRawData(data.raw_data);
  const chartIntent = resolveAutoChartIntent({
    rawData: data.raw_data,
    narrative: data.narrative,
    explicitChartConfig: data.chart_config,
  });
  const smartChartConfig = chartIntent.chartConfig ?? inferredChartConfig;
  const chartCandidates = buildChartCandidates(smartChartConfig, chartIntent.reason);
  const extraFragments = keepSpanishFragments(data.cortex_analyst?.agent_text_fragments ?? [], data.narrative, 3);
  const donutCandidate = chartCandidates.find((c) => c.config.type === 'donut')?.config ?? null;
  const shareHighlights = buildDonutShareHighlights(donutCandidate, 5);
  return (
    <div className="space-y-6 animate-in fade-in duration-700">
      <section className="rounded-xl border border-zinc-800/70 bg-zinc-950/40 p-5">
        <MarkdownNarrative content={data.narrative} hideTables={chartCandidates.length > 0} />
      </section>
      {shareHighlights.length > 0 && (
        <section className="rounded-xl border border-zinc-800/70 bg-zinc-950/35 p-4">
          <h5 className="text-xs uppercase tracking-[0.18em] font-black text-zinc-400">
            Participacion por categoria (%)
          </h5>
          <p className="mt-2 text-sm text-zinc-100 leading-relaxed">
            {shareHighlights
              .map((item) => `${item.label}: ${item.pct.toFixed(1)}%`)
              .join(' · ')}
          </p>
        </section>
      )}
      {extraFragments.length > 0 && (
        <section className="space-y-3">
          {extraFragments.slice(0, 3).map((fragment, idx) => (
            <article
              key={`${data.response_id}-fragment-${idx}`}
              className="rounded-xl border border-zinc-800/70 bg-zinc-950/30 p-4"
            >
              <MarkdownNarrative content={fragment} className="text-zinc-200" />
            </article>
          ))}
        </section>
      )}
      {chartCandidates.length > 0 && (
        <div className="space-y-5">
          {chartCandidates.map((chart, idx) => (
            <div key={`${data.response_id}-int-chart-${chart.config.type}-${idx}`} className="space-y-2">
              <ChartModule config={chart.config} />
              <p className="text-xs text-zinc-500">{chart.reason}</p>
            </div>
          ))}
        </div>
      )}
      {data.raw_data && data.raw_data.length > 0 && <TableModule data={data.raw_data} />}
    </div>
  );
};
