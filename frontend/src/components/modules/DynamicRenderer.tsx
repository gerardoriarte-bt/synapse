import React from 'react';
import { SynapseResponse } from '@/types/synapse';
import { ChartModule } from './ChartModule';
import { TableModule } from './TableModule';
import { ActionToolbar } from './ActionToolbar';
import { AlertCircle } from 'lucide-react';
import { inferChartConfigFromRawData } from '@/lib/chart-inference';
import { MarkdownNarrative } from './MarkdownNarrative';
import { resolveAutoChartIntent } from '@/lib/chart-intent';
import { keepSpanishFragments } from '@/lib/narrative-filter';
import { buildDonutShareHighlights } from '@/lib/chart-insight';
import { buildChartCandidates } from '@/lib/chart-multi';

interface Props {
  data: SynapseResponse;
}

export const DynamicRenderer: React.FC<Props> = ({ data }) => {
  const { narrative, render_type, chart_config, raw_data, response_id } = data;
  const inferredChartConfig = chart_config ?? inferChartConfigFromRawData(raw_data);
  const chartIntent = resolveAutoChartIntent({
    rawData: raw_data,
    narrative,
    explicitChartConfig: chart_config,
  });
  const smartChartConfig = chartIntent.chartConfig ?? inferredChartConfig;
  const chartCandidates = buildChartCandidates(smartChartConfig, chartIntent.reason);
  const chartEnabledByType =
    render_type === 'chart' || render_type === 'table' || (render_type === 'text' && chartIntent.shouldRender);
  const showChart = chartEnabledByType && chartCandidates.length > 0;
  const extraFragments = keepSpanishFragments(data.cortex_analyst?.agent_text_fragments ?? [], narrative, 2);
  const donutCandidate = chartCandidates.find((c) => c.config.type === 'donut')?.config ?? null;
  const shareHighlights = buildDonutShareHighlights(donutCandidate, 5);

  const renderChartStack = () =>
    chartCandidates.length > 0 ? (
      <div className="space-y-5">
        {chartCandidates.map((chart, idx) => (
          <div key={`${response_id}-chart-${chart.config.type}-${idx}`} className="space-y-2">
            <ChartModule config={chart.config} />
            <p className="text-xs text-zinc-500">{chart.reason}</p>
          </div>
        ))}
      </div>
    ) : (
      <RenderError message="Faltan datos de configuración para el gráfico." />
    );

  const renderModule = () => {
    switch (render_type) {
      case 'chart':
        return renderChartStack();

      case 'table':
        return raw_data ? (
          <div className="space-y-4">
            {chartCandidates.length > 0 && renderChartStack()}
            <TableModule data={raw_data} />
          </div>
        ) : (
          <RenderError message="Faltan datos para renderizar la tabla." />
        );

      case 'text':
        if (chartCandidates.length === 0 || !chartIntent.shouldRender) {
          return null;
        }
        return (
          <div className="space-y-4">
            {renderChartStack()}
            {raw_data && raw_data.length > 0 && <TableModule data={raw_data} />}
          </div>
        );

      default:
        console.warn(`[Synapse] Render type "${render_type}" no reconocido.`);
        return null;
    }
  };

  return (
    <div className="w-full space-y-6 p-6 bg-zinc-900/30 border border-zinc-800 rounded-2xl animate-in zoom-in-95 duration-500">
      <section className={showChart ? "grid gap-5 xl:grid-cols-12" : ""}>
        <div className={showChart ? "xl:col-span-6 2xl:col-span-7 space-y-4" : "space-y-4"}>
          <div className="rounded-xl border border-zinc-800/70 bg-zinc-950/40 p-5">
            <MarkdownNarrative content={narrative} hideTables={chartCandidates.length > 0} />
          </div>
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
              {extraFragments.slice(0, 2).map((fragment, idx) => (
                <article
                  key={`${response_id}-fragment-${idx}`}
                  className="rounded-xl border border-zinc-800/70 bg-zinc-950/30 p-4"
                >
                  <MarkdownNarrative content={fragment} className="text-zinc-200" />
                </article>
              ))}
            </section>
          )}
        </div>
        {showChart && (
          <aside className="xl:col-span-6 2xl:col-span-5 xl:sticky xl:top-6 xl:max-h-[calc(100vh-5rem)] xl:overflow-y-auto xl:pr-1 h-fit">
            {renderModule()}
          </aside>
        )}
      </section>
      {!showChart && <section className="min-h-[50px] w-full">{renderModule()}</section>}
      <div className="pt-2">
        <ActionToolbar responseId={response_id} data={raw_data} />
      </div>
    </div>
  );
};

const RenderError = ({ message }: { message: string }) => (
  <div className="flex items-center gap-3 p-4 bg-red-950/30 border border-red-900 rounded-lg text-red-200">
    <AlertCircle size={20} />
    <p className="text-sm italic">{message}</p>
  </div>
);
