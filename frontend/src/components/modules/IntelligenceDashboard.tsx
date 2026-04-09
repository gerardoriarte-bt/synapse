import React from 'react';
import { TrendingUp, AlertTriangle, Lightbulb, BarChart3 } from 'lucide-react';
import { SynapseResponse } from '@/types/synapse';
import { ChartModule } from './ChartModule';
import { TableModule } from './TableModule';
import { StructuredNarrative } from '@/components/shared/StructuredNarrative';
import { ExecutiveSummaryCard } from '@/components/shared/ExecutiveSummaryCard';
import { ComparisonCards } from '@/components/shared/ComparisonCards';
import { EvidencePanels } from '@/components/shared/EvidencePanels';
import {
  buildComparisonCards,
  buildEvidenceSnapshot,
  buildExecutiveHeadline,
  buildLimitations,
} from '@/lib/insight-utils';
import { inferChartConfigFromRawData } from '@/lib/chart-inference';

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

  const isCortexPassthrough = Boolean(data.cortex_analyst);
  const smartChartConfig = data.chart_config ?? inferChartConfigFromRawData(data.raw_data);
  if (isCortexPassthrough) {
    return (
      <div className="space-y-6 animate-in fade-in duration-700">
        <section className="rounded-xl border border-zinc-800/70 bg-zinc-950/40 p-5">
          <p className="whitespace-pre-wrap text-zinc-100 leading-relaxed">{data.narrative}</p>
        </section>
        {smartChartConfig && <ChartModule config={smartChartConfig} data={data.raw_data} />}
        {data.raw_data && data.raw_data.length > 0 && <TableModule data={data.raw_data} />}
      </div>
    );
  }

  const executiveHeadline = buildExecutiveHeadline(
    data.narrative,
    'Lectura ejecutiva disponible para apoyar la priorización del negocio.'
  );
  const comparisons = buildComparisonCards(data.decision_meta);
  const evidence = buildEvidenceSnapshot(data.raw_data);
  const limitations = buildLimitations(data.decision_meta);

  return (
    <div className="space-y-10 animate-in fade-in duration-1000">
      <div className="flex justify-between items-end">
        <div>
          <h2 className="text-3xl font-black tracking-tighter text-white uppercase italic">Lectura estratégica</h2>
          <p className="mt-1 text-zinc-500 font-bold text-xs uppercase tracking-[0.2em]">
            Marketing Intelligence · Synapse Analyst
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        <div className="relative overflow-hidden rounded-[40px] bg-zinc-900/40 p-8 backdrop-blur-md">
          <div className="absolute top-0 right-0 p-6 opacity-5 group-hover:opacity-10 transition-opacity">
            <AlertTriangle size={80} className="text-amber-500" />
          </div>
          <ExecutiveSummaryCard
            headline={executiveHeadline}
            eyebrowClassName="text-amber-500/80"
            containerClassName="border-zinc-800 bg-transparent p-0"
          />
        </div>

        <div className="lg:col-span-2 bg-[#050505] border border-zinc-800/60 rounded-[40px] p-8 space-y-4 shadow-2xl relative overflow-hidden group">
          <div className="absolute inset-0 bg-gradient-to-tr from-emerald-500/5 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-1000" />
          <div className="flex items-center justify-between mb-2 relative z-10">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-emerald-500/10 flex items-center justify-center border border-emerald-500/20">
                <TrendingUp size={20} className="text-emerald-500" />
              </div>
              <h3 className="text-[10px] font-black text-emerald-500 uppercase tracking-widest">Evidencia contextual</h3>
            </div>
          </div>
          <div className="h-[280px] relative z-10">
             {smartChartConfig && <ChartModule config={smartChartConfig} data={data.raw_data} />}
          </div>
        </div>
      </div>

      <ComparisonCards
        items={comparisons}
        sectionClassName="border-0 bg-transparent p-0"
        gridClassName="grid gap-4 md:grid-cols-3"
        cardClassName="rounded-[28px] border border-zinc-800 bg-zinc-900/40 p-6 shadow-xl"
        titleClassName="hidden"
      />

      <EvidencePanels
        evidence={evidence}
        limitations={limitations}
        sectionTitle="Evidencia y cautelas"
        evidenceTitle="Evidencia utilizada"
        limitationsTitle="Limitaciones y cautelas"
        emptyLimitationsText="No se identificaron alertas críticas para esta lectura."
        sectionClassName="space-y-3 border-0 bg-transparent p-0"
        gridClassName="grid gap-4 lg:grid-cols-2"
        panelClassName="rounded-[32px] border border-zinc-800 bg-zinc-900/40 p-7 shadow-xl"
      />

      <div className="bg-gradient-to-br from-indigo-900/30 to-black border border-indigo-500/30 p-10 rounded-[50px] space-y-8 relative group overflow-hidden shadow-2xl">
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_bottom_right,_var(--tw-gradient-stops))] from-indigo-500/10 via-transparent to-transparent opacity-50" />
        <div className="flex items-center gap-5 relative z-10">
          <div className="w-14 h-14 rounded-2xl bg-indigo-500/20 flex items-center justify-center text-indigo-400 ring-1 ring-indigo-400/40 shadow-xl">
            <Lightbulb size={28} />
          </div>
          <div>
            <h3 className="text-[10px] font-black text-indigo-400 uppercase tracking-[0.4em]">Lectura del analista</h3>
            <p className="text-xl font-black text-white tracking-tighter uppercase italic">Diagnóstico y decisión</p>
          </div>
        </div>
        <div className="relative z-10">
          <StructuredNarrative text={data.narrative} compact />
        </div>
      </div>
    </div>
  );
};
