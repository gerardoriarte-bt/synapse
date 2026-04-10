'use client';

import React, { useState } from 'react';
import dynamic from 'next/dynamic';
import type { EChartsOption } from 'echarts';
import { ChartConfig } from '@/types/synapse';
import { Moon, Sun } from 'lucide-react';

interface Props {
  config: ChartConfig;
}

const ReactECharts = dynamic(() => import('echarts-for-react'), { ssr: false });

const PALETTE = [
  '#1F6AA5',
  '#2B82CC',
  '#3F9DE3',
  '#8EC9F3',
  '#C9E7FB',
  '#F4FAFF',
  '#FAF0E2',
  '#F7DDB8',
  '#F4BE84',
  '#F39A4A',
  '#EE7422',
  '#D95D15',
];
const PRIMARY_ACCENT = '#2B82CC';
const SERIES_CONTRAST = ['#1F6AA5', '#EE7422', '#3F9DE3', '#D95D15'];
const VALUE_GRADIENT = [
  '#1F6AA5',
  '#2B82CC',
  '#3F9DE3',
  '#8EC9F3',
  '#C9E7FB',
  '#F4FAFF',
  '#FAF0E2',
  '#F7DDB8',
  '#F4BE84',
  '#F39A4A',
  '#EE7422',
  '#D95D15',
];

type ChartTheme = 'dark' | 'light';

const THEME_COLORS: Record<
  ChartTheme,
  {
    tooltipBg: string;
    tooltipBorder: string;
    tooltipText: string;
    legendText: string;
    axisText: string;
    axisLine: string;
    gridLine: string;
    zoomBorder: string;
    zoomBg: string;
    zoomFill: string;
    chartSurface: string;
  }
> = {
  dark: {
    tooltipBg: '#09090b',
    tooltipBorder: '#27272a',
    tooltipText: '#f4f4f5',
    legendText: '#a1a1aa',
    axisText: '#a1a1aa',
    axisLine: '#3f3f46',
    gridLine: '#27272a',
    zoomBorder: '#3f3f46',
    zoomBg: '#18181b',
    zoomFill: 'rgba(43,130,204,0.22)',
    chartSurface: 'bg-gradient-to-b from-zinc-950 to-zinc-900/90 border-zinc-800',
  },
  light: {
    tooltipBg: '#ffffff',
    tooltipBorder: '#d4d4d8',
    tooltipText: '#18181b',
    legendText: '#3f3f46',
    axisText: '#52525b',
    axisLine: '#d4d4d8',
    gridLine: '#e4e4e7',
    zoomBorder: '#cbd5e1',
    zoomBg: '#f4f4f5',
    zoomFill: 'rgba(43,130,204,0.15)',
    chartSurface: 'bg-gradient-to-b from-zinc-100 to-zinc-50 border-zinc-300',
  },
};

const formatNumber = (value: number): string => {
  if (!Number.isFinite(value)) return '0';
  return new Intl.NumberFormat('es-MX', {
    maximumFractionDigits: 2,
  }).format(value);
};

export const ChartModule: React.FC<Props> = ({ config }) => {
  const [chartTheme, setChartTheme] = useState<ChartTheme>('dark');
  const theme = THEME_COLORS[chartTheme];
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
  const minVal = Math.min(...chartData.map((d) => d.value));
  const maxVal = Math.max(...chartData.map((d) => d.value));
  const valueColor = (v: number): string => {
    if (!Number.isFinite(v) || maxVal <= minVal) return VALUE_GRADIENT[0];
    const normalized = (v - minVal) / (maxVal - minVal);
    const idx = Math.max(
      0,
      Math.min(VALUE_GRADIENT.length - 1, Math.round(normalized * (VALUE_GRADIENT.length - 1)))
    );
    return VALUE_GRADIENT[idx];
  };
  const barDataWithColor = chartData.map((d) => ({
    value: d.value,
    itemStyle: { color: valueColor(d.value) },
  }));

  const series =
    config.type === 'donut'
      ? [
          {
            type: 'pie',
            radius: ['45%', '72%'],
            center: ['50%', '50%'],
            data: chartData
              .map((d) => ({ name: d.name, value: d.value }))
              .sort((a, b) => a.value - b.value)
              .map((d) => ({
                ...d,
                itemStyle: { color: valueColor(d.value) },
              })),
            padAngle: 1,
            itemStyle: {
              borderColor: chartTheme === 'dark' ? '#09090b' : '#ffffff',
              borderWidth: 2,
            },
            label: {
              color: chartTheme === 'dark' ? '#d4d4d8' : '#27272a',
              formatter: '{b}: {d}%',
              fontWeight: 600,
            },
            labelLine: { lineStyle: { color: theme.axisLine } },
          },
        ]
      : [
          ...(hasMultiSeries
            ? (config.series || []).map((s, idx) => ({
                type: config.type === 'line' ? 'line' : 'bar',
                name: s.name,
                data:
                  config.type === 'bar'
                    ? s.values.map((v) => ({
                        value: v,
                        itemStyle: {
                          color: SERIES_CONTRAST[idx % SERIES_CONTRAST.length],
                          borderColor: chartTheme === 'dark' ? '#0b1120' : '#ffffff',
                          borderWidth: 1,
                        },
                      }))
                    : s.values,
                smooth: config.type === 'line',
                showSymbol: config.type === 'line',
                symbolSize: 8,
                lineStyle: { width: 3, color: SERIES_CONTRAST[idx % SERIES_CONTRAST.length] },
                itemStyle: { color: SERIES_CONTRAST[idx % SERIES_CONTRAST.length] },
                areaStyle:
                  config.type === 'line'
                    ? {
                        opacity: 0.1,
                        color: SERIES_CONTRAST[idx % SERIES_CONTRAST.length],
                      }
                    : undefined,
                barMaxWidth: 32,
                emphasis: { focus: 'series' },
              }))
            : [
                {
                  type: config.type === 'line' ? 'line' : 'bar',
                  name: label,
                  data: config.type === 'bar' ? barDataWithColor : chartData.map((d) => d.value),
                  smooth: config.type === 'line',
                  showSymbol: config.type === 'line',
                  symbolSize: 8,
                  lineStyle: { width: 3, color: PRIMARY_ACCENT },
                  itemStyle: { color: PRIMARY_ACCENT },
                  areaStyle:
                    config.type === 'line'
                      ? {
                          opacity: 0.12,
                          color: PRIMARY_ACCENT,
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
      backgroundColor: theme.tooltipBg,
      borderColor: theme.tooltipBorder,
      borderWidth: 1,
      textStyle: { color: theme.tooltipText },
      extraCssText: 'box-shadow: 0 8px 24px rgba(0,0,0,.18);',
      valueFormatter: (value) => formatNumber(Number(value)),
    },
    legend: {
      top: 8,
      textStyle: { color: theme.legendText, fontSize: 11 },
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
              color: theme.axisText,
              fontWeight: 600,
              rotate: chartData.length > 8 ? 25 : 0,
              hideOverlap: true,
            },
            axisLine: { lineStyle: { color: theme.axisLine } },
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
              color: theme.axisText,
              fontWeight: 600,
              formatter: (v: number) => formatNumber(v),
            },
            splitLine: {
              lineStyle: { color: theme.gridLine, type: 'dashed' },
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
              borderColor: theme.zoomBorder,
              backgroundColor: theme.zoomBg,
              handleStyle: {
                color: PRIMARY_ACCENT,
              },
              fillerColor: theme.zoomFill,
              start: 0,
              end: chartData.length > 14 ? 55 : 100,
            },
          ],
    series: series as NonNullable<EChartsOption['series']>,
  };

  return (
    <div className={`w-full space-y-3 p-4 border rounded-2xl shadow-inner ${theme.chartSurface}`}>
      <div className="flex items-start justify-between gap-3">
        <div className="space-y-1">
          <h4 className={`text-sm font-extrabold tracking-tight ${chartTheme === 'dark' ? 'text-zinc-100' : 'text-zinc-900'}`}>{title}</h4>
          <p className={`text-[11px] ${chartTheme === 'dark' ? 'text-zinc-400' : 'text-zinc-600'}`}>
          Eje Y: <span className={chartTheme === 'dark' ? 'text-zinc-200 font-semibold' : 'text-zinc-800 font-semibold'}>{label}</span> · Eje X:{' '}
          <span className={chartTheme === 'dark' ? 'text-zinc-200 font-semibold' : 'text-zinc-800 font-semibold'}>{xAxisTitle}</span> · Puntos analizados:{' '}
          <span className={chartTheme === 'dark' ? 'text-zinc-200 font-semibold' : 'text-zinc-800 font-semibold'}>{chartData.length}</span>
          </p>
        </div>
        <button
          type="button"
          onClick={() => setChartTheme((prev) => (prev === 'dark' ? 'light' : 'dark'))}
          className={`inline-flex items-center gap-2 rounded-lg border px-3 py-1.5 text-[11px] font-semibold ${
            chartTheme === 'dark'
              ? 'border-zinc-600/40 bg-zinc-900/40 text-zinc-200 hover:border-zinc-500'
              : 'border-zinc-300 bg-white text-zinc-700 hover:border-zinc-400'
          }`}
          title="Cambiar modo de gráfico"
        >
          {chartTheme === 'dark' ? <Moon size={13} /> : <Sun size={13} />}
          {chartTheme === 'dark' ? 'Dark' : 'Light'}
        </button>
      </div>
      <div className="h-72 xl:h-[26rem]">
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
