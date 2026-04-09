import React from 'react';

type SummaryStat = {
  label: string;
  value: string;
};

interface Props {
  eyebrow?: string;
  headline: string;
  subtitle?: string;
  stats?: SummaryStat[];
  containerClassName?: string;
  eyebrowClassName?: string;
}

export const ExecutiveSummaryCard: React.FC<Props> = ({
  eyebrow = 'Resumen ejecutivo',
  headline,
  subtitle,
  stats = [],
  containerClassName = '',
  eyebrowClassName = 'text-indigo-300/80',
}) => {
  return (
    <section className={`rounded-xl border border-zinc-800/70 bg-zinc-950/50 p-5 ${containerClassName}`.trim()}>
      <p className={`text-[10px] font-black uppercase tracking-[0.3em] ${eyebrowClassName}`.trim()}>
        {eyebrow}
      </p>
      <p className="mt-2 text-xl font-extrabold tracking-tight text-white">{headline}</p>
      {subtitle && <p className="mt-2 text-sm text-zinc-400">{subtitle}</p>}
      {stats.length > 0 && (
        <div className="mt-4 space-y-2 text-sm text-zinc-300">
          {stats.map((stat) => (
            <p key={`${stat.label}-${stat.value}`}>
              {stat.label}: <span className="font-bold text-white">{stat.value}</span>
            </p>
          ))}
        </div>
      )}
    </section>
  );
};
