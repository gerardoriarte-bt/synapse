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
      <p className="text-zinc-500 max-w-sm font-medium italic">Click &quot;Generate Insights&quot; to build your strategic marketing pulse from Snowflake.</p>
    </div>
  );

  return (
    <div className="space-y-10 animate-in fade-in duration-1000">
      <div className="flex justify-between items-end">
        <div>
          <h2 className="text-3xl font-black tracking-tighter text-white uppercase italic">Strategic Insight Engine</h2>
          <p className="text-zinc-500 font-bold text-xs uppercase tracking-[0.2em] mt-1">Advanced Marketing Intelligence / Snowflake Cortex</p>
        </div>
        <div className="text-[10px] px-6 py-2 bg-indigo-500/10 border border-indigo-400/20 text-indigo-400 font-black rounded-full uppercase tracking-[0.3em] shadow-lg shadow-indigo-500/5">
          Real-Time Analysis Enabled
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        <div className="bg-zinc-900/40 border border-zinc-800 p-8 rounded-[40px] space-y-6 relative overflow-hidden group backdrop-blur-md">
          <div className="absolute top-0 right-0 p-6 opacity-5 group-hover:opacity-10 transition-opacity">
            <AlertTriangle size={80} className="text-amber-500" />
          </div>
          <div className="flex items-center gap-3">
             <div className="w-10 h-10 rounded-xl bg-amber-500/10 flex items-center justify-center border border-amber-500/20">
               <AlertTriangle size={20} className="text-amber-500" />
             </div>
             <h3 className="text-[10px] font-black text-amber-500/80 uppercase tracking-widest">The Strategic Tension</h3>
          </div>
          <p className="text-sm font-bold text-zinc-300 leading-relaxed italic">
            &quot;Dynamic ROAS volatility detected in your latest Snowflake data cycles. This warrants immediate executive attention.&quot;
          </p>
        </div>

        <div className="lg:col-span-2 bg-[#050505] border border-zinc-800/60 rounded-[40px] p-8 space-y-4 shadow-2xl relative overflow-hidden group">
          <div className="absolute inset-0 bg-gradient-to-tr from-emerald-500/5 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-1000" />
          <div className="flex items-center justify-between mb-2 relative z-10">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-emerald-500/10 flex items-center justify-center border border-emerald-500/20">
                <TrendingUp size={20} className="text-emerald-500" />
              </div>
              <h3 className="text-[10px] font-black text-emerald-500 uppercase tracking-widest">Live Contextual Evidence</h3>
            </div>
          </div>
          <div className="h-[280px] relative z-10">
             {data.chart_config && <ChartModule config={data.chart_config} />}
          </div>
        </div>
      </div>

      <div className="bg-gradient-to-br from-indigo-900/30 to-black border border-indigo-500/30 p-10 rounded-[50px] space-y-8 relative group overflow-hidden shadow-2xl">
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_bottom_right,_var(--tw-gradient-stops))] from-indigo-500/10 via-transparent to-transparent opacity-50" />
        <div className="flex items-center gap-5 relative z-10">
          <div className="w-14 h-14 rounded-2xl bg-indigo-500/20 flex items-center justify-center text-indigo-400 ring-1 ring-indigo-400/40 shadow-xl">
            <Lightbulb size={28} />
          </div>
          <div>
            <h3 className="text-[10px] font-black text-indigo-400 uppercase tracking-[0.4em]">Cortex AI Recommendation</h3>
            <p className="text-xl font-black text-white tracking-tighter uppercase italic">Executive Action Plan</p>
          </div>
        </div>
        <div className="relative z-10">
          <p className="text-zinc-300 text-lg leading-relaxed font-semibold tracking-tight">
            {data.narrative}
          </p>
        </div>
        <button className="relative z-10 flex items-center gap-3 text-white font-black text-[10px] uppercase tracking-[0.2em] bg-indigo-600 px-8 py-4 rounded-2xl border border-indigo-400/40 hover:bg-indigo-500 transition-all shadow-xl shadow-indigo-600/20 active:scale-95">
          Execute Intelligence Strategy <ArrowUpRight size={18} />
        </button>
      </div>
    </div>
  );
};
