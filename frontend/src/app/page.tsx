'use client';

import React, { useState, useRef, useEffect } from 'react';
import { SynapseChatLayout } from '@/components/layout/SynapseChatLayout';
import { DynamicRenderer } from '@/components/modules/DynamicRenderer';
import { IntelligenceDashboard } from '@/components/modules/IntelligenceDashboard';
import { SkeletonLoader } from '@/components/shared/SkeletonLoader';
import { useSynapseQuery } from '@/hooks/useSynapseQuery';
import { SynapseResponse } from '@/types/synapse';
import { Send, Activity, Sparkles, Loader2 } from 'lucide-react';

interface ChatMessage {
  query: string;
  response: SynapseResponse;
  createdAt: string;
}

export default function Home() {
  const [view, setView] = useState<'chat' | 'intelligence'>('chat');
  const [query, setQuery] = useState('');
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [intelligenceData, setIntelligenceData] = useState<SynapseResponse | null>(null);
  const [lastIntelligenceQuery, setLastIntelligenceQuery] = useState<string | null>(null);
  const [activeQuery, setActiveQuery] = useState<string | null>(null);
  const [loadingSeconds, setLoadingSeconds] = useState(0);
  const [loadingPhase, setLoadingPhase] = useState(0);
  
  const { askSynapse, isLoading, response, error } = useSynapseQuery();
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const pendingQueryRef = useRef<string | null>(null);
  const pendingViewRef = useRef<'chat' | 'intelligence'>('chat');

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    if (response && pendingQueryRef.current) {
      const messageEntry: ChatMessage = {
        query: pendingQueryRef.current,
        response,
        createdAt: new Date().toISOString(),
      };
      setMessages(prev => [...prev, messageEntry]);

      if (pendingViewRef.current === 'intelligence') {
        setIntelligenceData(response);
        setLastIntelligenceQuery(pendingQueryRef.current);
      }

      pendingQueryRef.current = null;
      scrollToBottom();
    }
  }, [response]);

  useEffect(() => {
    if (!isLoading) return;
    const timer = window.setInterval(() => {
      setLoadingSeconds((prev) => prev + 1);
      setLoadingPhase((prev) => (prev + 1) % LOADING_STEPS.length);
    }, 1000);
    return () => window.clearInterval(timer);
  }, [isLoading]);

  const hydrateIntelligenceFromLatestMessage = () => {
    if (messages.length === 0) return false;
    const latestMessage = messages[messages.length - 1];
    setIntelligenceData(latestMessage.response);
    setLastIntelligenceQuery(latestMessage.query);
    return true;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim()) return;
    const currentQuery = query;
    setQuery('');
    pendingQueryRef.current = currentQuery;
    setActiveQuery(currentQuery);
    setLoadingSeconds(0);
    setLoadingPhase(0);
    pendingViewRef.current = 'chat';
    await askSynapse(currentQuery);
    setActiveQuery(null);
    setLoadingSeconds(0);
    setLoadingPhase(0);
  };

  const generateIntelligence = async () => {
    setView('intelligence');
    const trimmedQuery = query.trim();

    if (trimmedQuery) {
      setQuery('');
      pendingQueryRef.current = trimmedQuery;
      setActiveQuery(trimmedQuery);
      setLoadingSeconds(0);
      setLoadingPhase(0);
      pendingViewRef.current = 'intelligence';
      await askSynapse(trimmedQuery);
      setActiveQuery(null);
      setLoadingSeconds(0);
      setLoadingPhase(0);
      return;
    }

    hydrateIntelligenceFromLatestMessage();
  };

  const handleViewChange = (nextView: 'chat' | 'intelligence') => {
    setView(nextView);
    if (nextView === 'intelligence') {
      hydrateIntelligenceFromLatestMessage();
    }
  };

  return (
    <SynapseChatLayout
      currentView={view}
      onViewChange={(v) => handleViewChange(v as 'chat' | 'intelligence')}
    >
      <div className="flex flex-col min-h-full">
        {view === 'intelligence' ? (
          <div className="space-y-10">
             {lastIntelligenceQuery && (
               <div className="rounded-2xl border border-zinc-800 bg-zinc-900/30 p-5">
                 <p className="text-[10px] font-black uppercase tracking-[0.2em] text-zinc-500">Consulta ejecutada</p>
                 <p className="mt-2 text-zinc-100 font-semibold leading-relaxed">{lastIntelligenceQuery}</p>
               </div>
             )}
             <IntelligenceDashboard data={intelligenceData} isLoading={isLoading} />
             {messages.length > 0 && (
                <div className="pt-10 border-t border-zinc-900">
                  <h3 className="text-xs font-bold text-zinc-600 uppercase tracking-widest mb-6 px-4">
                    Historial de Consultas
                  </h3>
                  <div className="space-y-3 max-h-[360px] overflow-y-auto pr-2">
                     {messages.slice(-8).reverse().map((m, i) => (
                       <div key={i} className="p-4 bg-zinc-900/30 border border-zinc-800 rounded-2xl text-[12px] text-zinc-200">
                         <p className="text-[10px] uppercase tracking-wider text-zinc-500 mb-1">
                           {new Date(m.createdAt).toLocaleString()}
                         </p>
                         <p><strong>Q:</strong> {m.query}</p>
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
                  <h1 className="text-5xl font-black tracking-tighter text-white">Synapse Analyst</h1>
                  <p className="text-zinc-500 max-w-sm mx-auto font-medium leading-relaxed">
                    Consulta tus datos de negocio y transforma cada respuesta en una lectura ejecutiva accionable.
                  </p>
                </div>
                <div className="flex flex-wrap justify-center gap-3 max-w-xl">
                  <SuggestionChip text="Vista Ejecutiva" onClick={generateIntelligence} highlight />
                  <SuggestionChip text="ROAS Semanal" onClick={() => { setQuery('¿Cómo ha variado el ROAS las últimas semanas?'); }} />
                  <SuggestionChip text="Anomalías de Gasto" onClick={() => { setQuery('Busca anomalías de gasto ayer'); }} />
                </div>
              </div>
            )}

            <div className="flex-grow space-y-16 pb-40">
              {messages.map((msg, idx) => (
                <div key={idx} className="flex flex-col space-y-8 animate-in fade-in slide-in-from-bottom-6 duration-1000">
                  <div className="flex justify-start">
                    <div className="max-w-[85%] px-8 py-5 rounded-[2rem] bg-zinc-900/40 border border-zinc-800/50 text-zinc-100 shadow-sm backdrop-blur-md">
                      <p className="text-[15px] font-medium leading-relaxed tracking-tight">{msg.query}</p>
                      <span className="text-[10px] text-zinc-600 font-black uppercase tracking-[0.2em] mt-4 block opacity-50">
                        {new Date(msg.createdAt).toLocaleTimeString()}
                      </span>
                    </div>
                  </div>

                  <div className="flex flex-col space-y-6">
                    <div className="flex items-center gap-4 mb-2 pl-2">
                      <div className="w-8 h-8 rounded-xl bg-indigo-500/10 border border-indigo-400/20 flex items-center justify-center shadow-inner">
                        <Activity size={14} className="text-indigo-400" />
                      </div>
                      <span className="text-[11px] font-black text-indigo-400/80 uppercase tracking-[0.25em]">Synapse Analyst</span>
                    </div>
                    <div className="pl-12 space-y-8 border-l-2 border-zinc-900/50 ml-4">
                      <DynamicRenderer data={msg.response} />
                    </div>
                  </div>
                </div>
              ))}
              {isLoading && (
                <div className="space-y-6 pt-6 pl-12">
                  <ProcessingIndicator
                    query={activeQuery}
                    seconds={loadingSeconds}
                    phase={LOADING_STEPS[loadingPhase]}
                  />
                  <SkeletonLoader />
                </div>
              )}
              {error && <div className="p-6 bg-red-950/10 border border-red-900/20 rounded-3xl text-red-500 text-xs italic ml-12">{error}</div>}
              <div ref={messagesEndRef} />
            </div>

            {/* Input Estilo Comando */}
            <form onSubmit={handleSubmit} className="fixed bottom-12 left-1/2 -translate-x-1/2 w-full max-w-3xl px-6 z-40">
              <div className="relative group">
                <div className="absolute -inset-1 bg-gradient-to-r from-indigo-500/20 via-blue-500/10 to-indigo-900/20 rounded-[2rem] blur-2xl opacity-30 group-focus-within:opacity-100 transition duration-700" />
                <div className="relative flex items-center gap-3 p-2 bg-black/55 backdrop-blur-3xl border border-indigo-300/35 rounded-[1.8rem] shadow-2xl transition-all duration-300 group-focus-within:border-indigo-200/70 group-focus-within:bg-black/75">
                  <input
                    type="text"
                    value={query}
                    onChange={(e) => setQuery(e.target.value)}
                    placeholder="Escribe una consulta de negocio..."
                    className="flex-grow bg-transparent border-none outline-none px-6 py-4 text-sm text-zinc-200 placeholder-zinc-600 font-semibold tracking-tight"
                  />
                  <button type="submit" disabled={isLoading || !query.trim()} className="p-4 bg-white text-black rounded-2xl hover:bg-zinc-200 disabled:opacity-30 transition-all shadow-xl active:scale-90">
                    {isLoading ? <Loader2 size={20} className="animate-spin" /> : <Send size={20} />}
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

const LOADING_STEPS = [
  'Interpretando consulta',
  'Consultando Synapse Analyst',
  'Procesando resultados',
  'Construyendo visualizaciones',
];

const ProcessingIndicator = ({
  query,
  seconds,
  phase,
}: {
  query: string | null;
  seconds: number;
  phase: string;
}) => (
  <div className="rounded-2xl border border-indigo-500/20 bg-indigo-950/20 p-4">
    <div className="flex items-center gap-2 text-indigo-300">
      <Loader2 size={15} className="animate-spin" />
      <p className="text-xs font-semibold uppercase tracking-wider">Procesando consulta</p>
      <span className="ml-auto text-[11px] text-indigo-200/80">{seconds}s</span>
    </div>
    <p className="mt-2 text-sm text-indigo-100">{phase}...</p>
    {query && <p className="mt-2 text-xs text-zinc-400 line-clamp-2">{query}</p>}
  </div>
);
