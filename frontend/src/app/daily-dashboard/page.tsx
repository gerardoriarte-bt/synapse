'use client';

import Link from 'next/link';
import { useEffect, useState, type ReactNode } from 'react';
import { ArrowLeft, Loader2, RefreshCw } from 'lucide-react';
import { getApiBaseUrl } from '@/lib/api-base';

type Row = Record<string, unknown>;
type Mode = 'volume' | 'performance';

type DailyOverview = {
  range: { start_date: string; end_date: string };
  summary: Row;
  top_products_by_units: Row[];
  top_campaigns_by_revenue: Row[];
  active_campaigns: Row[];
  product_sales_period_totals?: Row;
  active_campaigns_period_totals?: Row;
  source_campaign_hierarchy?: Row[];
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

function toNum(v: unknown): number {
  if (typeof v === 'number' && Number.isFinite(v)) return v;
  if (typeof v === 'string') {
    const parsed = Number(v.replace(/,/g, '').trim());
    return Number.isFinite(parsed) ? parsed : 0;
  }
  return 0;
}

function safeDivide(a: unknown, b: unknown): number | null {
  const den = toNum(b);
  if (!den) return null;
  return toNum(a) / den;
}

type HierarchyRow = {
  FUENTE: string;
  CAMPAIGN_PRIMARIO: string;
  VENTA_TOTAL: number;
  TRANSACCIONES: number;
  TICKET_PROMEDIO: number;
  UNIDADES_POR_TICKET: number;
  PRECIO_PROMEDIO: number;
};

type SourceNode = {
  name: string;
  revenue: number;
  tx: number;
  ticket: number;
};

function normalizeHierarchyRows(rows: Row[]): HierarchyRow[] {
  return rows.map((row) => ({
    FUENTE: String(row.FUENTE ?? 'SIN_FUENTE'),
    CAMPAIGN_PRIMARIO: String(row.CAMPAIGN_PRIMARIO ?? 'SIN_CAMPAÑA'),
    VENTA_TOTAL: toNum(row.VENTA_TOTAL),
    TRANSACCIONES: toNum(row.TRANSACCIONES),
    TICKET_PROMEDIO: toNum(row.TICKET_PROMEDIO),
    UNIDADES_POR_TICKET: toNum(row.UNIDADES_POR_TICKET),
    PRECIO_PROMEDIO: toNum(row.PRECIO_PROMEDIO),
  }));
}

function buildSourceNodes(rows: HierarchyRow[]): SourceNode[] {
  const map = new Map<string, SourceNode>();
  rows.forEach((r) => {
    const curr = map.get(r.FUENTE) ?? { name: r.FUENTE, revenue: 0, tx: 0, ticket: 0 };
    curr.revenue += r.VENTA_TOTAL;
    curr.tx += r.TRANSACCIONES;
    map.set(r.FUENTE, curr);
  });
  return Array.from(map.values())
    .map((s) => ({ ...s, ticket: s.tx ? s.revenue / s.tx : 0 }))
    .sort((a, b) => b.tx - a.tx);
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
  const ventaTotal = summary?.REVENUE_USD;
  const transacciones = summary?.ORDENES;
  const unidades = summary?.UNIDADES;
  const ticketPromedio = safeDivide(ventaTotal, transacciones);
  const unidadesPorTicket = safeDivide(unidades, transacciones);
  const precioPromedio = safeDivide(ventaTotal, unidades);

  const pt = data?.product_sales_period_totals;
  const productsFooter =
    data && data.top_products_by_units.length > 0 && pt && Object.keys(pt).length > 0
      ? ({
          PRODUCTO: 'Total periodo (todas las líneas con producto)',
          UNIDADES_VENDIDAS: pt.UNIDADES_VENDIDAS,
          REVENUE_USD: pt.REVENUE_USD,
        } satisfies Row)
      : null;

  const summaryRow = data?.summary;
  const campaignsFooter =
    data && data.top_campaigns_by_revenue.length > 0 && summaryRow && Object.keys(summaryRow).length > 0
      ? ({
          CAMPAIGN_PRIMARIO: 'Total periodo (FCT, todas las filas)',
          FUENTE: '—',
          REVENUE_USD: summaryRow.REVENUE_USD,
          ROAS: summaryRow.ROAS,
        } satisfies Row)
      : null;

  const at = data?.active_campaigns_period_totals;
  const activeFooter =
    data && data.active_campaigns.length > 0 && at && Object.keys(at).length > 0
      ? ({
          FUENTE: 'Total periodo (campañas con actividad)',
          CAMPAIGN_PRIMARIO: '—',
          INGRESOS_USD_PERIODO: at.INGRESOS_USD_PERIODO,
          GASTO_USD_PERIODO: at.GASTO_USD_PERIODO,
          ORDENES_PERIODO: at.ORDENES_PERIODO,
          ROAS: at.ROAS,
          FECHA_ULTIMA_ACTIVIDAD: '—',
        } satisfies Row)
      : null;

  const hierarchyRows = normalizeHierarchyRows(data?.source_campaign_hierarchy ?? []);

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

            <section className="grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
              <MetricCard title="Venta total (USD)" value={formatMoney(ventaTotal)} />
              <MetricCard title="Transacciones" value={formatNum(transacciones)} />
              <MetricCard title="Ticket promedio" value={ticketPromedio != null ? formatMoney(ticketPromedio) : '—'} />
              <MetricCard title="Unidades por ticket" value={unidadesPorTicket != null ? formatNum(unidadesPorTicket) : '—'} />
              <MetricCard title="Precio promedio" value={precioPromedio != null ? formatMoney(precioPromedio) : '—'} />
            </section>
            <section className="grid gap-4 sm:grid-cols-3">
              <MetricCard title="Gasto (USD)" value={formatMoney(summary?.GASTO_USD)} />
              <MetricCard title="ROAS" value={summary?.ROAS != null ? formatNum(summary.ROAS) : '—'} />
              <MetricCard title="Clicks / Impresiones" value={`${formatNum(summary?.CLICKS)} / ${formatNum(summary?.IMPRESIONES)}`} />
            </section>

            <section className="grid gap-8 lg:grid-cols-2">
              <DataPanel
                title="Nodos conectados: desglose de volumen"
                subtitle="Fuente → Campaña (conexiones ponderadas por transacciones)"
              >
                <ConnectedNodeGraph rows={hierarchyRows} mode="volume" />
              </DataPanel>
              <DataPanel
                title="Nodos conectados: comparativa de rendimiento"
                subtitle="Fuente → Campaña (color por ticket promedio vs promedio de su fuente)"
              >
                <ConnectedNodeGraph rows={hierarchyRows} mode="performance" />
              </DataPanel>
            </section>

            <section className="grid gap-8 lg:grid-cols-2">
              <DataPanel
                title="Top productos vendidos (unidades)"
                subtitle="Por volumen en el periodo"
                footnote="Si ves unidades con revenue 0, suele deberse a regalos o promos sin cargo, canjes, notas de crédito, reembolsos neteados, o líneas donde el ingreso quedó en otra fila (bundle, split de línea, o fuente distinta). La fila inferior es la suma de todo el periodo en la tabla de ventas por producto, no solo del top 10."
              >
                <SimpleTable
                  columns={[
                    { key: 'PRODUCTO', label: 'Producto' },
                    { key: 'UNIDADES_VENDIDAS', label: 'Unidades', format: formatNum },
                    { key: 'REVENUE_USD', label: 'Revenue', format: formatMoney },
                  ]}
                  rows={data.top_products_by_units}
                  footer={productsFooter}
                />
              </DataPanel>
              <DataPanel
                title="Top campañas por revenue"
                subtitle="Por ingresos atribuidos en el periodo"
                footnote="La fila inferior usa el mismo agregado del periodo que las tarjetas KPI (FCT_PERFORMANCE), no solo las campañas listadas arriba."
              >
                <SimpleTable
                  columns={[
                    { key: 'CAMPAIGN_PRIMARIO', label: 'Campaña' },
                    { key: 'FUENTE', label: 'Fuente' },
                    { key: 'REVENUE_USD', label: 'Revenue', format: formatMoney },
                    { key: 'ROAS', label: 'ROAS', format: formatNum },
                  ]}
                  rows={data.top_campaigns_by_revenue}
                  footer={campaignsFooter}
                />
              </DataPanel>
            </section>

            <DataPanel
              title="Campañas activas (fuente + nombre)"
              subtitle="Con gasto, clicks, impresiones u órdenes en el periodo; ordenadas por revenue"
              footnote="La fila inferior suma todas las campañas que cumplen el criterio de actividad en el periodo (sin tope de filas). La tabla de arriba está limitada por configuración."
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
                footer={activeFooter}
              />
            </DataPanel>
          </>
        )}
      </main>
    </div>
  );
}

function ConnectedNodeGraph({ rows, mode }: { rows: HierarchyRow[]; mode: Mode }) {
  if (!rows.length) {
    return <p className="text-sm text-zinc-500">Sin datos jerárquicos para el periodo.</p>;
  }

  const sources = buildSourceNodes(rows).slice(0, 6);
  const sourceSet = new Set(sources.map((s) => s.name));
  const campaigns = rows
    .filter((r) => sourceSet.has(r.FUENTE))
    .sort((a, b) => b.TRANSACCIONES - a.TRANSACCIONES)
    .slice(0, 12);

  const sourceYStep = 320 / Math.max(sources.length, 1);
  const campaignYStep = 320 / Math.max(campaigns.length, 1);
  const maxTx = Math.max(...campaigns.map((c) => c.TRANSACCIONES), 1);

  return (
    <div className="space-y-3">
      <div className="h-[340px] w-full overflow-hidden rounded-xl border border-zinc-800 bg-zinc-950/40 p-2">
        <svg viewBox="0 0 1000 340" className="h-full w-full">
          {campaigns.map((c, i) => {
            const sourceIndex = sources.findIndex((s) => s.name === c.FUENTE);
            const y1 = 20 + sourceYStep * sourceIndex + sourceYStep / 2;
            const y2 = 20 + campaignYStep * i + campaignYStep / 2;
            const strokeWidth = mode === 'volume' ? Math.max(1.2, (c.TRANSACCIONES / maxTx) * 8) : 2.5;
            const sourceTicket = sources[sourceIndex]?.ticket ?? 0;
            const perfRatio = sourceTicket > 0 ? c.TICKET_PROMEDIO / sourceTicket : 1;
            const perfColor =
              perfRatio >= 1.1 ? '#22c55e' : perfRatio >= 0.95 ? '#a3a3a3' : '#f97316';
            const stroke = mode === 'volume' ? '#6366f1' : perfColor;
            return (
              <path
                key={`${c.FUENTE}-${c.CAMPAIGN_PRIMARIO}`}
                d={`M 220 ${y1} C 380 ${y1}, 560 ${y2}, 760 ${y2}`}
                fill="none"
                stroke={stroke}
                strokeWidth={strokeWidth}
                opacity={0.7}
              />
            );
          })}

          {sources.map((s, i) => {
            const y = 20 + sourceYStep * i + sourceYStep / 2;
            return (
              <g key={s.name}>
                <rect x={20} y={y - 18} width={190} height={36} rx={8} fill="#1e1b4b" stroke="#4338ca" />
                <text x={30} y={y - 3} fill="#e5e7eb" fontSize={12} fontWeight={600}>
                  {s.name}
                </text>
                <text x={30} y={y + 11} fill="#a1a1aa" fontSize={10}>
                  Tx {formatNum(s.tx)} | Ticket {formatMoney(s.ticket)}
                </text>
              </g>
            );
          })}

          {campaigns.map((c, i) => {
            const y = 20 + campaignYStep * i + campaignYStep / 2;
            const sourceTicket = sources.find((s) => s.name === c.FUENTE)?.ticket ?? 0;
            const perfRatio = sourceTicket > 0 ? c.TICKET_PROMEDIO / sourceTicket : 1;
            const perfColor =
              perfRatio >= 1.1 ? '#14532d' : perfRatio >= 0.95 ? '#1f2937' : '#7c2d12';
            const fill = mode === 'volume' ? '#312e81' : perfColor;
            return (
              <g key={`${c.FUENTE}-${c.CAMPAIGN_PRIMARIO}-node`}>
                <rect x={770} y={y - 16} width={210} height={32} rx={8} fill={fill} stroke="#374151" />
                <text x={780} y={y - 2} fill="#e5e7eb" fontSize={11} fontWeight={600}>
                  {c.CAMPAIGN_PRIMARIO.slice(0, 28)}
                </text>
                <text x={780} y={y + 11} fill="#a1a1aa" fontSize={9}>
                  Tx {formatNum(c.TRANSACCIONES)} | Ticket {formatMoney(c.TICKET_PROMEDIO)}
                </text>
              </g>
            );
          })}
        </svg>
      </div>
      <p className="text-[11px] text-zinc-500">
        {mode === 'volume'
          ? 'Conexiones más gruesas = mayor volumen de transacciones.'
          : 'Verde = ticket sobre promedio de su fuente, naranja = bajo promedio de su fuente.'}
      </p>
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
  footnote,
  children,
}: {
  title: string;
  subtitle?: string;
  footnote?: string;
  children: ReactNode;
}) {
  return (
    <div className="rounded-2xl border border-zinc-800 bg-zinc-900/30 p-5">
      <h2 className="text-sm font-bold text-zinc-200">{title}</h2>
      {subtitle && <p className="mt-1 text-xs text-zinc-500">{subtitle}</p>}
      {footnote && <p className="mt-2 text-[11px] leading-relaxed text-zinc-600">{footnote}</p>}
      <div className="mt-4 overflow-x-auto">{children}</div>
    </div>
  );
}

function SimpleTable({
  columns,
  rows,
  footer,
}: {
  columns: { key: string; label: string; format?: (v: unknown) => string }[];
  rows: Row[];
  footer?: Row | null;
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
      {footer && (
        <tfoot>
          <tr className="border-t border-zinc-700 bg-zinc-900/80 text-zinc-100">
            {columns.map((c) => {
              const raw = footer[c.key];
              const cell = c.format ? c.format(raw) : raw === null || raw === undefined ? '—' : String(raw);
              return (
                <td key={c.key} className="max-w-[220px] truncate py-2.5 pr-3 align-top text-[11px] font-semibold">
                  {cell}
                </td>
              );
            })}
          </tr>
        </tfoot>
      )}
    </table>
  );
}
