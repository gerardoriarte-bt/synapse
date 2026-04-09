import React from 'react';
import { ComparisonCard } from '@/lib/insight-utils';

interface Props {
  items: ComparisonCard[];
  title?: string;
  sectionClassName?: string;
  gridClassName?: string;
  cardClassName?: string;
  titleClassName?: string;
}

export const ComparisonCards: React.FC<Props> = ({
  items,
  title = 'Comparativos clave',
  sectionClassName = '',
  gridClassName = 'grid gap-3 md:grid-cols-3',
  cardClassName = 'rounded-lg border border-zinc-800 bg-zinc-900/50 p-3',
  titleClassName = 'text-[10px] font-black uppercase tracking-[0.3em] text-emerald-300/80',
}) => {
  if (items.length === 0) return null;

  return (
    <section className={`space-y-3 rounded-xl border border-zinc-800 bg-zinc-950/60 p-4 ${sectionClassName}`.trim()}>
      <p className={titleClassName}>{title}</p>
      <div className={gridClassName}>
        {items.map((item) => (
          <div key={item.id} className={cardClassName}>
            <p className="text-xs uppercase tracking-wider text-zinc-400">{item.title}</p>
            <p className={`mt-2 text-sm font-bold ${item.statusClass}`}>{item.statusLabel}</p>
            {item.detail && <p className="mt-1 text-xs text-zinc-400">{item.detail}</p>}
          </div>
        ))}
      </div>
    </section>
  );
};
