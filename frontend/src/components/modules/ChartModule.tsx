'use client';

import React from 'react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  LineChart,
  Line,
  Legend,
  Label,
  PieChart,
  Pie,
  Cell,
} from 'recharts';
import { ChartConfig } from '@/types/synapse';

interface Props {
  config: ChartConfig;
  data?: unknown[];
}

export const ChartModule: React.FC<Props> = ({ config, data }) => {
  const chartData = config.x_axis.map((x, i) => ({
    name: x,
    value: config.y_axis[i] ?? 0,
  }));
  const palette = ['#6366f1', '#14b8a6', '#22c55e', '#f59e0b', '#f97316', '#a78bfa', '#06b6d4'];

  const label = config.metrics_label;
  const title =
    config.type === 'bar'
      ? `Comparativo de ${label}`
      : config.type === 'donut'
      ? `Distribución de ${label}`
      : `Tendencia de ${label}`;
  const xAxisTitle =
    typeof config.x_axis[0] === 'string' && String(config.x_axis[0]).includes('-')
      ? 'Periodo / Fecha'
      : 'Dimensión analizada';
  const sources =
    data && data.length > 0
      ? Array.from(
          new Set(
            data
              .map((row) => {
                if (!row || typeof row !== 'object' || Array.isArray(row)) return null;
                const rec = row as Record<string, unknown>;
                return rec.FUENTE || rec.CHANNEL || rec.PLATAFORMA;
              })
              .filter(Boolean)
          )
        ).slice(0, 3)
      : [];

  return (
    <div className="w-full space-y-3 bg-gradient-to-b from-zinc-950 to-zinc-900/90 p-4 border border-zinc-800 rounded-2xl shadow-inner">
      <div className="space-y-1">
        <h4 className="text-sm font-extrabold text-zinc-100 tracking-tight">{title}</h4>
        <p className="text-[11px] text-zinc-400">
          Métrica: <span className="text-zinc-200 font-semibold">{label}</span> · Puntos analizados:{' '}
          <span className="text-zinc-200 font-semibold">{chartData.length}</span>
          {sources.length > 0 && (
            <>
              {' '}· Fuente/canal:{' '}
              <span className="text-zinc-200 font-semibold">{sources.join(', ')}</span>
            </>
          )}
        </p>
      </div>
      <div className="h-72">
        <ResponsiveContainer width="100%" height="100%">
          {config.type === 'donut' ? (
            <PieChart>
              <Tooltip
                contentStyle={{ backgroundColor: '#09090b', borderColor: '#27272a', borderRadius: '10px', color: '#fff' }}
                labelStyle={{ color: '#e4e4e7', fontWeight: 700 }}
              />
              <Legend wrapperStyle={{ fontSize: '11px', color: '#a1a1aa' }} />
              <Pie
                data={chartData}
                dataKey="value"
                nameKey="name"
                innerRadius={56}
                outerRadius={98}
                paddingAngle={2}
                stroke="#18181b"
                strokeWidth={2}
              >
                {chartData.map((_, i) => (
                  <Cell key={`slice-${i}`} fill={palette[i % palette.length]} />
                ))}
              </Pie>
            </PieChart>
          ) : config.type === 'bar' ? (
            <BarChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#27272a" vertical={false} />
              <XAxis
                dataKey="name"
                stroke="#71717a"
                fontSize={12}
                tickLine={false}
                axisLine={false}
              >
                <Label value={xAxisTitle} offset={-2} position="insideBottom" fill="#71717a" fontSize={11} />
              </XAxis>
              <YAxis stroke="#71717a" fontSize={12} tickLine={false} axisLine={false}>
                <Label value={label} angle={-90} position="insideLeft" fill="#71717a" fontSize={11} />
              </YAxis>
              <Legend wrapperStyle={{ fontSize: '11px', color: '#a1a1aa' }} />
              <Tooltip
                contentStyle={{ backgroundColor: '#09090b', borderColor: '#27272a', borderRadius: '10px', color: '#fff' }}
                itemStyle={{ color: '#818cf8' }}
                labelStyle={{ color: '#e4e4e7', fontWeight: 700 }}
              />
              <Bar
                dataKey="value"
                fill="#6366f1"
                radius={[4, 4, 0, 0]}
                name={label}
              />
            </BarChart>
          ) : (
            <LineChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#27272a" vertical={false} />
              <XAxis dataKey="name" stroke="#71717a" fontSize={12}>
                <Label value={xAxisTitle} offset={-2} position="insideBottom" fill="#71717a" fontSize={11} />
              </XAxis>
              <YAxis stroke="#71717a" fontSize={12}>
                <Label value={label} angle={-90} position="insideLeft" fill="#71717a" fontSize={11} />
              </YAxis>
              <Legend wrapperStyle={{ fontSize: '11px', color: '#a1a1aa' }} />
              <Tooltip
                contentStyle={{ backgroundColor: '#09090b', borderColor: '#27272a', borderRadius: '10px' }}
                labelStyle={{ color: '#e4e4e7', fontWeight: 700 }}
              />
              <Line
                type="monotone"
                dataKey="value"
                stroke="#6366f1"
                strokeWidth={3}
                dot={{ fill: '#6366f1', r: 4 }}
                name={label}
              />
            </LineChart>
          )}
        </ResponsiveContainer>
      </div>
    </div>
  );
};
