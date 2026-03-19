import React from 'react';
import { SynapseResponse } from '@/types/synapse';
import { ChartModule } from './ChartModule';
import { TableModule } from './TableModule';
import { ActionToolbar } from './ActionToolbar';
import { AlertCircle } from 'lucide-react';

interface Props {
  data: SynapseResponse;
}

export const DynamicRenderer: React.FC<Props> = ({ data }) => {
  const { narrative, render_type, chart_config, raw_data, response_id } = data;

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
      <section className="text-zinc-100 text-lg leading-relaxed font-medium">
        {narrative}
      </section>

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
