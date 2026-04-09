import React from 'react';
import { BarChart3 } from 'lucide-react';
import { SynapseResponse } from '@/types/synapse';
import { ChartModule } from './ChartModule';
import { TableModule } from './TableModule';
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

  const smartChartConfig = data.chart_config ?? inferChartConfigFromRawData(data.raw_data);
  return (
    <div className="space-y-6 animate-in fade-in duration-700">
      <section className="rounded-xl border border-zinc-800/70 bg-zinc-950/40 p-5">
        <p className="whitespace-pre-wrap text-zinc-100 leading-relaxed">{data.narrative}</p>
      </section>
      {smartChartConfig && <ChartModule config={smartChartConfig} />}
      {data.raw_data && data.raw_data.length > 0 && <TableModule data={data.raw_data} />}
    </div>
  );
};
