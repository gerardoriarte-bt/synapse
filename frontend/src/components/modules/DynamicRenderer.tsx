import React from 'react';
import { SynapseResponse } from '@/types/synapse';
import { ChartModule } from './ChartModule';
import { TableModule } from './TableModule';
import { ActionToolbar } from './ActionToolbar';
import { AlertCircle } from 'lucide-react';
import { StructuredNarrative } from '@/components/shared/StructuredNarrative';

interface Props {
  data: SynapseResponse;
}

export const DynamicRenderer: React.FC<Props> = ({ data }) => {
  const { narrative, render_type, chart_config, raw_data, response_id, decision_meta } = data;

  const renderModule = () => {
    switch (render_type) {
      case 'chart':
        return chart_config ? (
          <ChartModule config={chart_config} data={raw_data} />
        ) : (
          <RenderError message="Faltan datos de configuración para el gráfico." />
        );

      case 'table':
        return raw_data ? (
          <TableModule data={raw_data} />
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
      {/* Narrativa */}
      <section className="rounded-xl border border-zinc-800/70 bg-zinc-950/40 p-5">
        <StructuredNarrative text={narrative} />
      </section>

      {decision_meta && (
        <section className="space-y-3 rounded-xl border border-zinc-800 bg-zinc-950/60 p-4">
          <div className="flex flex-wrap gap-2 text-[11px] uppercase tracking-wider">
            <span className="rounded-md bg-zinc-900 px-2 py-1 text-zinc-300">
              Intent: {decision_meta.intent}
            </span>
            <span className="rounded-md bg-zinc-900 px-2 py-1 text-zinc-300">
              Confidence: {(decision_meta.confidence_score * 100).toFixed(0)}%
            </span>
            <span className="rounded-md bg-zinc-900 px-2 py-1 text-zinc-300">
              Freshness: {decision_meta.data_freshness}
            </span>
          </div>
          {decision_meta.actions?.length > 0 && (
            <div className="space-y-2">
              <p className="text-xs font-bold uppercase tracking-wider text-zinc-400">Top Actions</p>
              {decision_meta.actions.map((a, idx) => (
                <div key={`${a.action}-${idx}`} className="rounded-lg border border-zinc-800 bg-zinc-900/40 p-3 text-sm text-zinc-200">
                  <p className="font-semibold">{idx + 1}. {a.action}</p>
                  <p className="mt-1 text-xs text-zinc-400">
                    Owner: {a.owner} | Horizon: {a.horizon} | Priority: {a.priority_score}
                  </p>
                  <p className="mt-1 text-xs text-zinc-300">{a.expected_impact}</p>
                </div>
              ))}
            </div>
          )}
        </section>
      )}

      {/* Visualizaciones */}
      <section className="min-h-[50px] w-full">
        {renderModule()}
      </section>

      {/* Acciones */}
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
