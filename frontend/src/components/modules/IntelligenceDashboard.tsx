'use client';

import React from 'react';
import { TrendingUp, AlertTriangle, Lightbulb, ArrowUpRight, BarChart3 } from 'lucide-react';
import { SynapseResponse } from '@/types/synapse';
import { ChartModule } from './ChartModule';

interface Props {
  data: SynapseResponse | null;
  isLoading: boolean;
}

export const IntelligenceDashboard: React.FC<Props> = ({ data, isLoading }) => {
  if (isLoading) return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-6 animate-pulse">
      {[1, 2, 3].map(i => (
        <div key={i} className="h-64 bg-zinc-900/50 border border-zinc-800 rounded-3xl" />
      ))}
    </div>
  );

  if (!data) return (
    <div className="flex flex-col items-center justify-center py-20 text-center space-y-4">
      <div className="w-16 h-16 rounded-full bg-zinc-900 border border-zinc-800 flex items-center justify-center">
        <BarChart3 className="text-zinc-600" size={32} />
      </div>
      <h2 className="text-xl font-bold text-white">No Intelligence Assets Found</h2>
      <p className="text-zinc-500 max-w-sm font-medium">Click "Generate Insights" to build your daily marketing pulse from Snowflake.</p>
    </div>
  );

  return (
    <div className="space-y-10 animate-in fade-in duration-1000">
      {/* Header Dashboard */}
      <div className="flex justify-between items-end">
        <div>
          <h2 className="text-3xl font-black tracking-tighter text-white">Daily Pulse Dashboard</h2>
          <p className="text-zinc-500 font-medium">Marketing Intelligence by Synapse Cortex Agent</p>
        </div>
        <div className="text-xs px-4 py-2 bg-indigo-500/10 border border-indigo-400/20 text-indigo-400 font-black rounded-full uppercase tracking-widest">
          Live Analysis
        </div>
      </div>

      {/* Grid de Insights Estratégicos */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Card 1: The Tension (Problem) */}
        <div className="bg-zinc-900/30 border border-zinc-800 p-8 rounded-[40px] space-y-6 relative overflow-hidden group">
          <div className="absolute top-0 right-0 p-6 opacity-10 group-hover:opacity-20 transition-opacity">
            <AlertTriangle size={80} className="text-amber-500" />
          </div>
          <div className="flex items-center gap-3">
             <div className="w-10 h-10 rounded-full bg-amber-500/10 flex items-center justify-center">
               <AlertTriangle size={20} className="text-amber-500" />
             </div>
             <h3 className="text-xs font-black text-amber-500 uppercase tracking-widest">The Tension</h3>
          </div>
          <p className="text-sm font-semibold text-zinc-300 leading-relaxed italic">
            "We've detected a ROAS volatility that might impact your monthly target if search volume keeps dropping."
          </p>
        </div>

        {/* Card 2: The Data (Visualization) */}
        <div className="lg:col-span-2 bg-[#050505] border border-zinc-800 rounded-[40px] p-8 space-y-4 shadow-2xl">
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-full bg-emerald-500/10 flex items-center justify-center">
                <TrendingUp size={20} className="text-emerald-500" />
              </div>
              <h3 className="text-xs font-black text-emerald-500 uppercase tracking-widest text-emerald-500">Snowflake Context</h3>
            </div>
          </div>
          <div className="h-[280px]">
             {data.chart_config && <ChartModule config={data.chart_config} />}
          </div>
        </div>
      </div>

      {/* Card 3: The Opportunity (Solution) */}
      <div className="bg-gradient-to-br from-indigo-900/20 to-purple-900/10 border border-indigo-500/30 p-10 rounded-[50px] space-y-6 relative group overflow-hidden">
        <div className="flex items-center gap-4">
          <div className="w-12 h-12 rounded-2xl bg-indigo-500/20 flex items-center justify-center text-indigo-400 ring-1 ring-indigo-400/30">
            <Lightbulb size={24} />
          </div>
          <div>
            <h3 className="text-[10px] font-black text-indigo-400 uppercase tracking-[0.3em]">AI-Powered Solution</h3>
            <p className="text-lg font-bold text-white tracking-tight">Strategic Optimization Recommendation</p>
          </div>
        </div>
        <p className="text-zinc-300 leading-relaxed font-medium">
          {data.narrative}
        </p>
        <button className="flex items-center gap-2 text-indigo-400 font-bold text-sm bg-black/40 px-6 py-3 rounded-2xl border border-indigo-400/20 hover:bg-black transition-all">
          Implement Strategy <ArrowUpRight size={18} />
        </button>
      </div>
    </div>
  );
};
