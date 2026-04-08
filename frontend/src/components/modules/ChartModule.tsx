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
} from 'recharts';
import { ChartConfig } from '@/types/synapse';

interface Props {
  config: ChartConfig;
  data?: any[];
}

export const ChartModule: React.FC<Props> = ({ config, data }) => {
  const chartData = config.x_axis.map((x, i) => ({
    name: x,
    value: config.y_axis[i] ?? 0,
  }));

  const label = config.metrics_label;

  return (
    <div className="w-full h-72 bg-zinc-950 p-4 border border-zinc-900 rounded-xl shadow-inner">
      <ResponsiveContainer width="100%" height="100%">
        {config.type === 'bar' ? (
          <BarChart data={chartData}>
            <CartesianGrid strokeDasharray="3 3" stroke="#27272a" vertical={false} />
            <XAxis 
              dataKey="name"
              stroke="#71717a" 
              fontSize={12} 
              tickLine={false} 
              axisLine={false} 
            />
            <YAxis stroke="#71717a" fontSize={12} tickLine={false} axisLine={false} />
            <Tooltip 
              contentStyle={{ backgroundColor: '#09090b', borderColor: '#27272a', borderRadius: '8px', color: '#fff' }}
              itemStyle={{ color: '#818cf8' }}
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
            <XAxis dataKey="name" stroke="#71717a" fontSize={12} />
            <YAxis stroke="#71717a" fontSize={12} />
            <Tooltip 
              contentStyle={{ backgroundColor: '#09090b', borderColor: '#27272a', borderRadius: '8px' }}
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
  );
};
