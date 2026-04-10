import React from 'react';
import { SynapseResponse } from '@/types/synapse';
import { ChartModule } from './ChartModule';
import { TableModule } from './TableModule';
import { ActionToolbar } from './ActionToolbar';
import { AlertCircle } from 'lucide-react';
import { inferChartConfigFromRawData } from '@/lib/chart-inference';
import { MarkdownNarrative } from './MarkdownNarrative';

interface Props {
  data: SynapseResponse;
}

export const DynamicRenderer: React.FC<Props> = ({ data }) => {
  const { narrative, render_type, chart_config, raw_data, response_id } = data;
  const inferredChartConfig = chart_config ?? inferChartConfigFromRawData(raw_data);
  const extraFragments = (data.cortex_analyst?.agent_text_fragments ?? []).filter(
    (frag) => frag.trim() && frag.trim() !== narrative.trim()
  );

  const renderModule = () => {
    switch (render_type) {
      case 'chart':
        return inferredChartConfig ? (
          <ChartModule config={inferredChartConfig} />
        ) : (
          <RenderError message="Faltan datos de configuración para el gráfico." />
        );

      case 'table':
        return raw_data ? (
          <div className="space-y-4">
            {inferredChartConfig && <ChartModule config={inferredChartConfig} />}
            <TableModule data={raw_data} />
          </div>
        ) : (
          <RenderError message="Faltan datos para renderizar la tabla." />
        );

      case 'text':
        return null;

      default:
        console.warn(`[Synapse] Render type "${render_type}" no reconocido.`);
        return null;
    }
  };

  return (
    <div className="w-full space-y-6 p-6 bg-zinc-900/30 border border-zinc-800 rounded-2xl animate-in zoom-in-95 duration-500">
      <section className="rounded-xl border border-zinc-800/70 bg-zinc-950/40 p-5">
        <MarkdownNarrative content={narrative} />
      </section>
      {extraFragments.length > 0 && (
        <section className="space-y-3">
          {extraFragments.slice(0, 3).map((fragment, idx) => (
            <article
              key={`${response_id}-fragment-${idx}`}
              className="rounded-xl border border-zinc-800/70 bg-zinc-950/30 p-4"
            >
              <MarkdownNarrative content={fragment} className="text-zinc-200" />
            </article>
          ))}
        </section>
      )}
      <section className="min-h-[50px] w-full">
        {renderModule()}
      </section>
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
