import React from 'react';
import { EvidenceSnapshot } from '@/lib/insight-utils';

interface Props {
  evidence: EvidenceSnapshot;
  limitations: string[];
  sectionTitle?: string;
  evidenceTitle?: string;
  limitationsTitle?: string;
  emptyLimitationsText?: string;
  sectionClassName?: string;
  gridClassName?: string;
  panelClassName?: string;
}

export const EvidencePanels: React.FC<Props> = ({
  evidence,
  limitations,
  sectionTitle = 'Evidencia y limitaciones',
  evidenceTitle = 'Evidencia usada',
  limitationsTitle = 'Limitaciones detectadas',
  emptyLimitationsText = 'Sin alertas críticas en esta respuesta.',
  sectionClassName = 'space-y-3 rounded-xl border border-zinc-800 bg-zinc-950/60 p-4',
  gridClassName = 'grid gap-3 md:grid-cols-2',
  panelClassName = 'rounded-lg border border-zinc-800 bg-zinc-900/40 p-3',
}) => {
  return (
    <section className={sectionClassName}>
      <p className="text-[10px] font-black uppercase tracking-[0.3em] text-zinc-300/90">
        {sectionTitle}
      </p>
      <div className={gridClassName}>
        <div className={panelClassName}>
          <p className="text-xs uppercase tracking-wider text-zinc-400">{evidenceTitle}</p>
          <ul className="mt-2 space-y-1 text-sm text-zinc-200">
            <li>Registros: {evidence.rowCount}</li>
            <li>Datasets: {evidence.datasetsText}</li>
            <li>Periodo observado: {evidence.periodText}</li>
          </ul>
        </div>
        <div className={panelClassName}>
          <p className="text-xs uppercase tracking-wider text-zinc-400">{limitationsTitle}</p>
          {limitations.length > 0 ? (
            <ul className="mt-2 list-disc space-y-1 pl-4 text-sm text-zinc-300">
              {limitations.map((item, idx) => (
                <li key={`${item}-${idx}`}>{item}</li>
              ))}
            </ul>
          ) : (
            <p className="mt-2 text-sm text-zinc-300">{emptyLimitationsText}</p>
          )}
        </div>
      </div>
    </section>
  );
};
