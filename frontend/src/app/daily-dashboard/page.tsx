'use client';

import Link from 'next/link';
import { useEffect, useState, type ReactNode } from 'react';
import { ArrowLeft, Loader2, RefreshCw } from 'lucide-react';
import { getApiBaseUrl } from '@/lib/api-base';

type Row = Record<string, unknown>;

type DailyOverview = {
  range: { start_date: string; end_date: string };
  summary: Row;
  top_products_by_units: Row[];
  top_campaigns_by_revenue: Row[];
  active_campaigns: Row[];
  meta: {
    top_limit: number;
    active_campaigns_row_cap: number;
    products_date_filter_applied: boolean;
  };
};

function formatNum(v: unknown): string {
  if (v === null || v === undefined) return '—';
  const n = typeof v === 'number' ? v : Number(v);
  if (!Number.isFinite(n)) return String(v);
  return n.toLocaleString('es-MX', { maximumFractionDigits: 2 });
}

function formatMoney(v: unknown): string {
  if (v === null || v === undefined) return '—';
  const n = typeof v === 'number' ? v : Number(v);
  if (!Number.isFinite(n)) return String(v);
  return n.toLocaleString('es-MX', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 });
}

export default function DailyDashboardPage() {
  const [data, setData] = useState<DailyOverview | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [endDate, setEndDate] = useState(() => new Date().toISOString().slice(0, 10));

  const load = async () => {
    setLoading(true);
    setError(null);
    try {
      const end = endDate;
      const startObj = new Date(end + 'T12:00:00');
      startObj.setDate(startObj.getDate() - 29);
      const start = startObj.toISOString().slice(0, 10);
      const base = getApiBaseUrl();
      const url = `${base}/api/dashboard/daily-overview?start_date=${encodeURIComponent(start)}&end_date=${encodeURIComponent(end)}`;
      const res = await fetch(url);
      if (!res.ok) {
        const text = await res.text();
        throw new Error(text || res.statusText);
      }
      const json = (await res.json()) as DailyOverview;
      setData(json);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Error al cargar el tablero');
      setData(null);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void load();
    // Carga inicial solamente; cambios de rango con "Actualizar"
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const summary = data?.summary;

  return (
    <div className="min-h-screen bg-[#141414] text-zinc-100">
      <header className="sticky top-0 z-10 border-b border-white/10 bg-black/40 backdrop-blur-md px-6 py-4">
        <div className="mx-auto flex max-w-7xl flex-wrap items-center justify-between gap-4">
          <div className="flex items-center gap-4">
            <Link
              href="/"
              className="inline-flex items-center gap-2 rounded-xl border border-zinc-700 bg-zinc-900/60 px-3 py-2 text-xs font-semibold text-zinc-300 transition hover:border-zinc-500 hover:text-white"
            >
              <ArrowLeft size={16} />
              Volver al chat
            </Link>
            <div>
              <h1 className="text-sm font-bold uppercase tracking-widest text-zinc-400">Seguimiento diario</h1>
              <p className="text-xs text-zinc-500">Datos en vivo desde Snowflake (últimos 30 días por defecto)</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <label className="text-[10px] font-bold uppercase tracking-wider text-zinc-500">Hasta</label>
            <input
              type="date"
              value={endDate}
              onChange={(e) => setEndDate(e.target.value)}
              className="rounded-lg border border-zinc-700 bg-zinc-950 px-2 py-1.5 text-xs text-zinc-200"
            />
            <button
              type="button"
              onClick={() => void load()}
              disabled={loading}
              className="inline-flex items-center gap-2 rounded-xl bg-indigo-600 px-4 py-2 text-xs font-semibold text-white shadow-lg shadow-indigo-900/30 transition hover:bg-indigo-500 disabled:opacity-40"
            >
              {loading ? <Loader2 size={14} className="animate-spin" /> : <RefreshCw size={14} />}
              Actualizar
            </button>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-7xl space-y-10 px-6 py-10">
        {error && (
          <div className="rounded-2xl border border-red-900/40 bg-red-950/20 p-4 text-sm text-red-200">{error}</div>
        )}

        {loading && !data && (
          <div className="flex items-center gap-3 text-sm text-zinc-400">
            <Loader2 className="animate-spin" size={18} />
            Consultando Snowflake…
          </div>
        )}

        {data && (
          <>
            <p className="text-xs text-zinc-500">
              Periodo: <span className="text-zinc-300">{data.range.start_date}</span> —{' '}
              <span className="text-zinc-300">{data.range.end_date}</span>
              {!data.meta.products_date_filter_applied && (
                <span className="ml-2 text-amber-400/90">
                  (Productos: sin filtro por fecha en servidor; revisa SYNAPSE_DASHBOARD_PRODUCT_SALES_DATE_COLUMN)
                </span>
              )}
            </p>

            <section className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
              <MetricCard title="Revenue (USD)" value={formatMoney(summary?.REVENUE_USD)} />
              <MetricCard title="Gasto (USD)" value={formatMoney(summary?.GASTO_USD)} />
              <MetricCard title="Órdenes" value={formatNum(summary?.ORDENES)} />
              <MetricCard title="ROAS" value={summary?.ROAS != null ? formatNum(summary.ROAS) : '—'} />
            </section>
            <section className="grid gap-4 sm:grid-cols-2">
              <MetricCard title="Unidades" value={formatNum(summary?.UNIDADES)} />
              <MetricCard title="Clicks / Impresiones" value={`${formatNum(summary?.CLICKS)} / ${formatNum(summary?.IMPRESIONES)}`} />
            </section>

            <section className="grid gap-8 lg:grid-cols-2">
              <DataPanel title="Top productos vendidos (unidades)" subtitle="Por volumen en el periodo">
                <SimpleTable
                  columns={[
                    { key: 'PRODUCTO', label: 'Producto' },
                    { key: 'UNIDADES_VENDIDAS', label: 'Unidades', format: formatNum },
                    { key: 'REVENUE_USD', label: 'Revenue', format: formatMoney },
                  ]}
                  rows={data.top_products_by_units}
                />
              </DataPanel>
              <DataPanel title="Top campañas por revenue" subtitle="Por ingresos atribuidos en el periodo">
                <SimpleTable
                  columns={[
                    { key: 'CAMPAIGN_PRIMARIO', label: 'Campaña' },
                    { key: 'FUENTE', label: 'Fuente' },
                    { key: 'REVENUE_USD', label: 'Revenue', format: formatMoney },
                    { key: 'ROAS', label: 'ROAS', format: formatNum },
                  ]}
                  rows={data.top_campaigns_by_revenue}
                />
              </DataPanel>
            </section>

            <DataPanel
              title="Campañas activas (fuente + nombre)"
              subtitle="Con gasto, clicks, impresiones u órdenes en el periodo; ordenadas por revenue"
            >
              <SimpleTable
                columns={[
                  { key: 'FUENTE', label: 'Fuente' },
                  { key: 'CAMPAIGN_PRIMARIO', label: 'Campaña' },
                  { key: 'INGRESOS_USD_PERIODO', label: 'Revenue', format: formatMoney },
                  { key: 'GASTO_USD_PERIODO', label: 'Gasto', format: formatMoney },
                  { key: 'ORDENES_PERIODO', label: 'Órdenes', format: formatNum },
                  { key: 'ROAS', label: 'ROAS', format: formatNum },
                  { key: 'FECHA_ULTIMA_ACTIVIDAD', label: 'Última actividad' },
                ]}
                rows={data.active_campaigns}
              />
            </DataPanel>
          </>
        )}
      </main>
    </div>
  );
}

function MetricCard({ title, value }: { title: string; value: string }) {
  return (
    <div className="rounded-2xl border border-zinc-800 bg-zinc-900/40 p-5 shadow-sm">
      <p className="text-[10px] font-bold uppercase tracking-widest text-zinc-500">{title}</p>
      <p className="mt-2 text-2xl font-semibold tracking-tight text-zinc-50">{value}</p>
    </div>
  );
}

function DataPanel({
  title,
  subtitle,
  children,
}: {
  title: string;
  subtitle?: string;
  children: ReactNode;
}) {
  return (
    <div className="rounded-2xl border border-zinc-800 bg-zinc-900/30 p-5">
      <h2 className="text-sm font-bold text-zinc-200">{title}</h2>
      {subtitle && <p className="mt-1 text-xs text-zinc-500">{subtitle}</p>}
      <div className="mt-4 overflow-x-auto">{children}</div>
    </div>
  );
}

function SimpleTable({
  columns,
  rows,
}: {
  columns: { key: string; label: string; format?: (v: unknown) => string }[];
  rows: Row[];
}) {
  if (!rows.length) {
    return <p className="text-sm text-zinc-500">Sin filas en este periodo.</p>;
  }
  return (
    <table className="w-full min-w-[520px] border-collapse text-left text-xs">
      <thead>
        <tr className="border-b border-zinc-800 text-[10px] font-bold uppercase tracking-wider text-zinc-500">
          {columns.map((c) => (
            <th key={c.key} className="py-2 pr-3 font-semibold">
              {c.label}
            </th>
          ))}
        </tr>
      </thead>
      <tbody>
        {rows.map((row, i) => (
          <tr key={i} className="border-b border-zinc-800/80 text-zinc-300">
            {columns.map((c) => {
              const raw = row[c.key];
              const cell = c.format ? c.format(raw) : raw === null || raw === undefined ? '—' : String(raw);
              return (
                <td key={c.key} className="max-w-[220px] truncate py-2 pr-3 align-top">
                  {cell}
                </td>
              );
            })}
          </tr>
        ))}
      </tbody>
    </table>
  );
}
