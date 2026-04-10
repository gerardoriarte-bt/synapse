'use client';

import React from 'react';
import dynamic from 'next/dynamic';
import type { EChartsOption } from 'echarts';
import { ChartConfig } from '@/types/synapse';

interface Props {
  config: ChartConfig;
}

const ReactECharts = dynamic(() => import('echarts-for-react'), { ssr: false });

const PALETTE = ['#6366f1', '#14b8a6', '#22c55e', '#f59e0b', '#f97316', '#a78bfa', '#06b6d4'];

const formatNumber = (value: number): string => {
  if (!Number.isFinite(value)) return '0';
  return new Intl.NumberFormat('es-MX', {
    maximumFractionDigits: 2,
  }).format(value);
};

export const ChartModule: React.FC<Props> = ({ config }) => {
  const chartData = config.x_axis.map((x, i) => ({
    name: String(x),
    value: config.y_axis[i] ?? 0,
  }));

  const label = config.metrics_label;
  const hasMultiSeries = Array.isArray(config.series) && config.series.length > 1;
  const title =
    config.type === 'bar'
      ? `Comparativo de ${label}`
      : config.type === 'donut'
      ? `Distribución de ${label}`
      : `Tendencia de ${label}`;
  const xAxisTitle = config.x_axis_label || 'Dimensión';

  const series =
    config.type === 'donut'
      ? [
          {
            type: 'pie',
            radius: ['45%', '72%'],
            center: ['50%', '50%'],
            data: chartData.map((d) => ({ name: d.name, value: d.value })),
            padAngle: 1,
            itemStyle: { borderColor: '#09090b', borderWidth: 2 },
            label: {
              color: '#d4d4d8',
              formatter: '{b}: {d}%',
            },
          },
        ]
      : [
          ...(hasMultiSeries
            ? (config.series || []).map((s, idx) => ({
                type: config.type === 'line' ? 'line' : 'bar',
                name: s.name,
                data: s.values,
                smooth: config.type === 'line',
                showSymbol: config.type === 'line',
                symbolSize: 8,
                lineStyle: { width: 3, color: PALETTE[idx % PALETTE.length] },
                itemStyle: { color: PALETTE[idx % PALETTE.length] },
                areaStyle:
                  config.type === 'line'
                    ? {
                        opacity: 0.1,
                        color: PALETTE[idx % PALETTE.length],
                      }
                    : undefined,
                barMaxWidth: 32,
                emphasis: { focus: 'series' },
              }))
            : [
                {
                  type: config.type === 'line' ? 'line' : 'bar',
                  name: label,
                  data: chartData.map((d) => d.value),
                  smooth: config.type === 'line',
                  showSymbol: config.type === 'line',
                  symbolSize: 8,
                  lineStyle: { width: 3, color: PALETTE[0] },
                  itemStyle: { color: PALETTE[0] },
                  areaStyle:
                    config.type === 'line'
                      ? {
                          opacity: 0.12,
                          color: PALETTE[0],
                        }
                      : undefined,
                  barMaxWidth: 40,
                  emphasis: {
                    focus: 'series',
                  },
                },
              ]),
        ];

  const option: EChartsOption = {
    backgroundColor: 'transparent',
    color: PALETTE,
    animationDuration: 550,
    textStyle: {
      fontFamily: 'Inter, ui-sans-serif, system-ui',
    },
    tooltip: {
      trigger: config.type === 'donut' ? 'item' : 'axis',
      backgroundColor: '#09090b',
      borderColor: '#27272a',
      borderWidth: 1,
      textStyle: { color: '#f4f4f5' },
      valueFormatter: (value) => formatNumber(Number(value)),
    },
    legend: {
      top: 8,
      textStyle: { color: '#a1a1aa', fontSize: 11 },
      type: 'scroll',
    },
    toolbox: {
      right: 8,
      itemSize: 14,
      iconStyle: {
        borderColor: '#a1a1aa',
      },
      feature: {
        saveAsImage: { show: true, title: 'Guardar imagen' },
        dataView: { show: true, readOnly: true, title: 'Ver datos' },
        restore: { show: true, title: 'Restaurar' },
      },
    },
    grid:
      config.type === 'donut'
        ? undefined
        : {
            left: 54,
            right: 20,
            top: 54,
            bottom: 52,
            containLabel: true,
          },
    xAxis:
      config.type === 'donut'
        ? undefined
        : {
            type: 'category',
            name: xAxisTitle,
            nameLocation: 'middle',
            nameGap: 34,
            data: chartData.map((d) => d.name),
            axisLabel: {
              color: '#a1a1aa',
              rotate: chartData.length > 8 ? 25 : 0,
              hideOverlap: true,
            },
            axisLine: { lineStyle: { color: '#3f3f46' } },
            axisTick: { show: false },
          },
    yAxis:
      config.type === 'donut'
        ? undefined
        : {
            type: 'value',
            name: label,
            nameLocation: 'middle',
            nameGap: 44,
            axisLabel: {
              color: '#a1a1aa',
              formatter: (v: number) => formatNumber(v),
            },
            splitLine: {
              lineStyle: { color: '#27272a', type: 'dashed' },
            },
          },
    dataZoom:
      config.type === 'donut'
        ? undefined
        : [
            {
              type: 'inside',
              start: 0,
              end: chartData.length > 14 ? 55 : 100,
            },
            {
              type: 'slider',
              bottom: 8,
              height: 14,
              borderColor: '#3f3f46',
              backgroundColor: '#18181b',
              fillerColor: 'rgba(99,102,241,0.22)',
              handleStyle: {
                color: '#6366f1',
              },
              start: 0,
              end: chartData.length > 14 ? 55 : 100,
            },
          ],
    series: series as NonNullable<EChartsOption['series']>,
  };

  return (
    <div className="w-full space-y-3 bg-gradient-to-b from-zinc-950 to-zinc-900/90 p-4 border border-zinc-800 rounded-2xl shadow-inner">
      <div className="space-y-1">
        <h4 className="text-sm font-extrabold text-zinc-100 tracking-tight">{title}</h4>
        <p className="text-[11px] text-zinc-400">
          Eje Y: <span className="text-zinc-200 font-semibold">{label}</span> · Eje X:{' '}
          <span className="text-zinc-200 font-semibold">{xAxisTitle}</span> · Puntos analizados:{' '}
          <span className="text-zinc-200 font-semibold">{chartData.length}</span>
        </p>
      </div>
      <div className="h-72">
        <ReactECharts
          option={option}
          style={{ height: '100%', width: '100%' }}
          opts={{ renderer: 'canvas' }}
          notMerge
          lazyUpdate
        />
      </div>
    </div>
  );
};
