import React, { useMemo, useState } from 'react';

interface Props {
  data: Array<Record<string, unknown>>;
}

export const TableModule: React.FC<Props> = ({ data }) => {
  const PAGE_SIZE_OPTIONS = [25, 50, 100];
  const [pageSize, setPageSize] = useState<number>(25);
  const [page, setPage] = useState<number>(1);

  const headers = useMemo(() => {
    const ordered: string[] = [];
    const seen = new Set<string>();
    for (const row of data) {
      for (const key of Object.keys(row)) {
        if (!seen.has(key)) {
          seen.add(key);
          ordered.push(key);
        }
      }
    }
    return ordered;
  }, [data]);

  const totalRows = data.length;
  const totalPages = Math.max(1, Math.ceil(totalRows / pageSize));
  const safePage = Math.min(page, totalPages);
  const start = (safePage - 1) * pageSize;
  const end = start + pageSize;
  const rows = data.slice(start, end);

  if (totalRows === 0) return null;

  const formatValue = (value: unknown): string => {
    if (value === null || value === undefined) return '-';
    if (typeof value === 'number') return value.toLocaleString();
    if (typeof value === 'object') return JSON.stringify(value);
    return String(value);
  };

  const onPageSizeChange = (next: number) => {
    setPageSize(next);
    setPage(1);
  };

  return (
    <div className="w-full overflow-hidden border border-zinc-900 rounded-xl bg-zinc-950/50 space-y-0">
      <div className="flex items-center justify-between px-4 py-3 border-b border-zinc-900 bg-zinc-900/40">
        <p className="text-xs text-zinc-400 font-semibold">
          Mostrando <span className="text-zinc-200">{start + 1}-{Math.min(end, totalRows)}</span> de{' '}
          <span className="text-zinc-200">{totalRows}</span> filas
        </p>
        <div className="flex items-center gap-2">
          <label htmlFor="page-size" className="text-xs text-zinc-500">Filas por página</label>
          <select
            id="page-size"
            value={pageSize}
            onChange={(e) => onPageSizeChange(Number(e.target.value))}
            className="bg-zinc-900 border border-zinc-700 rounded-md px-2 py-1 text-xs text-zinc-200"
          >
            {PAGE_SIZE_OPTIONS.map((opt) => (
              <option key={opt} value={opt}>{opt}</option>
            ))}
          </select>
        </div>
      </div>

      <div className="overflow-x-auto">
      <table className="w-full text-left text-sm">
        <thead className="bg-zinc-900/80 text-zinc-400 border-b border-zinc-800">
          <tr>
            {headers.map((h) => (
              <th key={h} className="px-4 py-3 font-semibold uppercase tracking-wider capitalize">
                {h.replaceAll('_', ' ')}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-zinc-900">
          {rows.map((row, i) => (
            <tr key={i} className="hover:bg-zinc-900/30 transition-colors">
              {headers.map((h) => (
                <td key={h} className="px-4 py-3 text-zinc-300 font-medium">
                  {formatValue(row[h])}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
      </div>

      {totalPages > 1 && (
        <div className="flex items-center justify-between px-4 py-3 border-t border-zinc-900 bg-zinc-900/20">
          <button
            onClick={() => setPage((p) => Math.max(1, p - 1))}
            disabled={safePage <= 1}
            className="px-3 py-1.5 text-xs rounded-md border border-zinc-700 text-zinc-200 disabled:opacity-40"
          >
            Anterior
          </button>
          <p className="text-xs text-zinc-400">
            Página <span className="text-zinc-200">{safePage}</span> de <span className="text-zinc-200">{totalPages}</span>
          </p>
          <button
            onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
            disabled={safePage >= totalPages}
            className="px-3 py-1.5 text-xs rounded-md border border-zinc-700 text-zinc-200 disabled:opacity-40"
          >
            Siguiente
          </button>
        </div>
      )}
    </div>
  );
};
