import React from 'react';
import { SynapseResponse } from '@/types/synapse';
import { ChartModule } from './ChartModule';
import { TableModule } from './TableModule';
import { ActionToolbar } from './ActionToolbar';
import { AlertCircle } from 'lucide-react';
import { StructuredNarrative } from '@/components/shared/StructuredNarrative';
import { ExecutiveSummaryCard } from '@/components/shared/ExecutiveSummaryCard';
import { ComparisonCards } from '@/components/shared/ComparisonCards';
import { EvidencePanels } from '@/components/shared/EvidencePanels';
import { inferChartConfigFromRawData } from '@/lib/chart-inference';
import {
  buildComparisonCards,
  buildEvidenceSnapshot,
  buildExecutiveHeadline,
  buildLimitations,
} from '@/lib/insight-utils';

interface Props {
  data: SynapseResponse;
}

export const DynamicRenderer: React.FC<Props> = ({ data }) => {
  const { narrative, render_type, chart_config, raw_data, response_id, decision_meta } = data;
  const inferredChartConfig = chart_config ?? inferChartConfigFromRawData(raw_data);
  const isCortexPassthrough = Boolean(data.cortex_analyst);
  const executiveHeadline = buildExecutiveHeadline(
    narrative,
    'Lectura ejecutiva generada para orientar la toma de decisiones.'
  );
  const comparisons = buildComparisonCards(decision_meta);
  const evidence = buildEvidenceSnapshot(raw_data);
  const limitations = buildLimitations(decision_meta);

  const renderModule = () => {
    switch (render_type) {
      case 'chart':
        return inferredChartConfig ? (
          <ChartModule config={inferredChartConfig} data={raw_data} />
        ) : (
          <RenderError message="Faltan datos de configuración para el gráfico." />
        );

      case 'table':
        return raw_data ? (
          <div className="space-y-4">
            {inferredChartConfig && <ChartModule config={inferredChartConfig} data={raw_data} />}
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

  if (isCortexPassthrough) {
    return (
      <div className="w-full space-y-6 p-6 bg-zinc-900/30 border border-zinc-800 rounded-2xl animate-in zoom-in-95 duration-500">
        <section className="rounded-xl border border-zinc-800/70 bg-zinc-950/40 p-5">
          <p className="whitespace-pre-wrap text-zinc-100 leading-relaxed">{narrative}</p>
        </section>
        <section className="min-h-[50px] w-full">{renderModule()}</section>
        <div className="pt-2">
          <ActionToolbar responseId={response_id} data={raw_data} />
        </div>
      </div>
    );
  }

  return (
    <div className="w-full space-y-6 p-6 bg-zinc-900/30 border border-zinc-800 rounded-2xl animate-in zoom-in-95 duration-500">
      <ExecutiveSummaryCard
        headline={executiveHeadline}
        subtitle="Diagnóstico y decisión recomendada con foco en impacto de negocio."
      />

      {/* Narrativa */}
      <section className="rounded-xl border border-zinc-800/70 bg-zinc-950/40 p-5">
        <StructuredNarrative text={narrative} />
      </section>

      <ComparisonCards items={comparisons} />

      <EvidencePanels evidence={evidence} limitations={limitations} />

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
