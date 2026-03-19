'use client';

import React, { useState, useRef, useEffect } from 'react';
import { SynapseChatLayout } from '@/components/layout/SynapseChatLayout';
import { DynamicRenderer } from '@/components/modules/DynamicRenderer';
import { IntelligenceDashboard } from '@/components/modules/IntelligenceDashboard';
import { SkeletonLoader } from '@/components/shared/SkeletonLoader';
import { useSynapseQuery } from '@/hooks/useSynapseQuery';
import { Send, Zap, Activity, Sparkles } from 'lucide-react';

interface ChatMessage {
  query: string;
  response: any;
}

export default function Home() {
  const [view, setView] = useState<'chat' | 'intelligence'>('chat');
  const [query, setQuery] = useState('');
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [intelligenceData, setIntelligenceData] = useState<any>(null);
  
  const { askSynapse, isLoading, response, error } = useSynapseQuery();
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    if (response) {
      if (view === 'chat') {
        setMessages(prev => [...prev, { query: prev[prev.length - 1]?.query || "Última consulta", response }]);
      } else {
        setIntelligenceData(response);
      }
      scrollToBottom();
    }
  }, [response]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim()) return;
    const currentQuery = query;
    setQuery('');
    await askSynapse(currentQuery);
  };

  const generateIntelligence = async () => {
    setView('intelligence');
    await askSynapse("GENERATE STRATEGIC INTELLIGENCE REPORT");
  };

  return (
    <SynapseChatLayout onViewChange={(v) => setView(v as 'chat' | 'intelligence')}>
      <div className="flex flex-col min-h-full">
        {view === 'intelligence' ? (
          <div className="space-y-10">
             <IntelligenceDashboard data={intelligenceData} isLoading={isLoading} />
             {messages.length > 0 && (
                <div className="pt-10 border-t border-zinc-900">
                  <h3 className="text-xs font-bold text-zinc-600 uppercase tracking-widest mb-6 px-4">Knowledge Base (Previous Context)</h3>
                  <div className="space-y-4 opacity-50 grayscale hover:grayscale-0 transition-all duration-500">
                     {messages.slice(-2).map((m, i) => (
                       <div key={i} className="p-4 bg-zinc-900/20 border border-zinc-800 rounded-2xl text-[11px]">
                         <strong>Q:</strong> {m.query}
                       </div>
                     ))}
                  </div>
                </div>
             )}
          </div>
        ) : (
          /* VISTA DE CHAT (Existente) */
          <div className="flex flex-col space-y-12">
            {messages.length === 0 && !isLoading && (
              <div className="flex flex-col items-center justify-center pt-20 text-center space-y-8 animate-in fade-in zoom-in duration-700">
                <div className="w-20 h-20 rounded-[2.5rem] bg-indigo-600/10 border border-indigo-500/20 flex items-center justify-center shadow-2xl shadow-indigo-500/10 relative overflow-hidden">
                   <div className="absolute inset-0 bg-gradient-to-tr from-indigo-500/10 to-transparent animate-pulse" />
                   <Sparkles className="text-indigo-400" size={36} />
                </div>
                <div className="space-y-3">
                  <h1 className="text-5xl font-black tracking-tighter text-white">Advanced Analytics</h1>
                  <p className="text-zinc-500 max-w-sm mx-auto font-medium leading-relaxed">
                    Consult your business data in real-time using Snowflake Cortex AI intelligence.
                  </p>
                </div>
                <div className="flex flex-wrap justify-center gap-3 max-w-xl">
                  <SuggestionChip text="Perform Strategic Analysis" onClick={generateIntelligence} highlight />
                  <SuggestionChip text="Weekly ROAS Performance" onClick={() => { setQuery('¿Cómo ha variado el ROAS las últimas semanas?'); }} />
                  <SuggestionChip text="Anomaly Detection" onClick={() => { setQuery('Busca anomalías de gasto ayer'); }} />
                </div>
              </div>
            )}

            <div className="flex-grow space-y-16 pb-40">
              {messages.map((msg, idx) => (
                <div key={idx} className="flex flex-col space-y-8 animate-in fade-in slide-in-from-bottom-6 duration-1000">
                  <div className="flex justify-start">
                    <div className="max-w-[85%] px-8 py-5 rounded-[2rem] bg-zinc-900/40 border border-zinc-800/50 text-zinc-100 shadow-sm backdrop-blur-md">
                      <p className="text-[15px] font-medium leading-relaxed tracking-tight">{msg.query}</p>
                      <span className="text-[10px] text-zinc-600 font-black uppercase tracking-[0.2em] mt-4 block opacity-50">Query Registered</span>
                    </div>
                  </div>

                  <div className="flex flex-col space-y-6">
                    <div className="flex items-center gap-4 mb-2 pl-2">
                      <div className="w-8 h-8 rounded-xl bg-indigo-500/10 border border-indigo-400/20 flex items-center justify-center shadow-inner">
                        <Activity size={14} className="text-indigo-400" />
                      </div>
                      <span className="text-[11px] font-black text-indigo-400/80 uppercase tracking-[0.25em]">Cortex Analyst Engine</span>
                    </div>
                    <div className="pl-12 space-y-8 border-l-2 border-zinc-900/50 ml-4">
                      <DynamicRenderer data={msg.response} />
                    </div>
                  </div>
                </div>
              ))}
              {isLoading && <div className="space-y-6 pt-6 pl-12"><SkeletonLoader /></div>}
              {error && <div className="p-6 bg-red-950/10 border border-red-900/20 rounded-3xl text-red-500 text-xs italic ml-12">{error}</div>}
              <div ref={messagesEndRef} />
            </div>

            {/* Input Estilo Comando */}
            <form onSubmit={handleSubmit} className="fixed bottom-12 left-1/2 -translate-x-1/2 w-full max-w-3xl px-6 z-40">
              <div className="relative group">
                <div className="absolute -inset-1 bg-gradient-to-r from-indigo-500/10 to-indigo-900/10 rounded-[2rem] blur-2xl opacity-0 group-focus-within:opacity-100 transition duration-1000" />
                <div className="relative flex items-center gap-3 p-2 bg-black/60 backdrop-blur-3xl border border-white/5 rounded-[1.8rem] shadow-2xl transition-all duration-300 group-focus-within:border-white/10 group-focus-within:bg-black/80">
                  <input
                    type="text"
                    value={query}
                    onChange={(e) => setQuery(e.target.value)}
                    placeholder="Enter analytical command..."
                    className="flex-grow bg-transparent border-none outline-none px-6 py-4 text-sm text-zinc-200 placeholder-zinc-600 font-semibold tracking-tight"
                  />
                  <button type="submit" disabled={isLoading || !query.trim()} className="p-4 bg-white text-black rounded-2xl hover:bg-zinc-200 disabled:opacity-30 transition-all shadow-xl active:scale-90">
                    <Send size={20} />
                  </button>
                </div>
              </div>
            </form>
          </div>
        )}
      </div>
    </SynapseChatLayout>
  );
}

const SuggestionChip = ({ text, onClick, highlight = false }: { text: string; onClick: () => void; highlight?: boolean }) => (
  <button 
    onClick={onClick}
    className={`px-5 py-3 rounded-2xl text-[11px] font-black uppercase tracking-widest transition-all active:scale-95 border ${
      highlight 
        ? 'bg-indigo-600 text-white border-indigo-400 shadow-lg shadow-indigo-600/20 hover:bg-indigo-500' 
        : 'bg-zinc-900/40 border-zinc-800 text-zinc-500 hover:border-zinc-700 hover:text-zinc-300'
    }`}
  >
    {text}
  </button>
);
