import React from 'react';

interface Props {
  data: any[];
}

export const TableModule: React.FC<Props> = ({ data }) => {
  if (!data || data.length === 0) return null;

  const headers = Object.keys(data[0]);

  return (
    <div className="w-full overflow-hidden border border-zinc-900 rounded-xl bg-zinc-950/50">
      <table className="w-full text-left text-sm">
        <thead className="bg-zinc-900/80 text-zinc-400 border-b border-zinc-800">
          <tr>
            {headers.map((h) => (
              <th key={h} className="px-4 py-3 font-semibold uppercase tracking-wider capitalize">
                {h.replace('_', ' ')}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-zinc-900">
          {data.map((row, i) => (
            <tr key={i} className="hover:bg-zinc-900/30 transition-colors">
              {headers.map((h) => (
                <td key={h} className="px-4 py-3 text-zinc-300 font-medium">
                  {typeof row[h] === 'number' ? row[h].toLocaleString() : row[h]}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};
