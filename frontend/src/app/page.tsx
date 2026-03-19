'use client';

import React, { useState, useRef, useEffect } from 'react';
import { SynapseChatLayout } from '@/components/layout/SynapseChatLayout';
import { DynamicRenderer } from '@/components/modules/DynamicRenderer';
import { SkeletonLoader } from '@/components/shared/SkeletonLoader';
import { useSynapseQuery } from '@/hooks/useSynapseQuery';
import { Send, Zap, Activity } from 'lucide-react';

interface ChatMessage {
  query: string;
  response: any;
}

export default function Home() {
  const [query, setQuery] = useState('');
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const { askSynapse, isLoading, response, error } = useSynapseQuery();
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    if (response) {
      setMessages(prev => [...prev, { query: prev[prev.length - 1]?.query || "Última consulta", response }]);
      scrollToBottom();
    }
  }, [response]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim()) return;
    
    // Añadimos la pregunta al estado visual inmediatamente
    const currentQuery = query;
    setQuery('');
    
    // Llamada al API
    await askSynapse(currentQuery);
  };

  return (
    <SynapseChatLayout>
      <div className="flex flex-col min-h-full">
        {/* Empty State / Welcome */}
        {messages.length === 0 && !isLoading && (
          <div className="flex flex-col items-center justify-center pt-20 text-center space-y-6">
            <div className="w-16 h-16 rounded-2xl bg-zinc-900 border border-zinc-800 flex items-center justify-center shadow-xl">
              <Zap className="text-zinc-600 fill-zinc-600" size={32} />
            </div>
            <div className="space-y-2">
              <h1 className="text-4xl font-bold tracking-tight text-white">¿Qué quieres analizar hoy?</h1>
              <p className="text-zinc-500 max-w-md mx-auto italic">Pregunta sobre ROAS, anomalías de tráfico o eficiencia de pauta.</p>
            </div>
            <div className="flex gap-2">
              <SuggestionChip text="¿Cómo ha variado el ROAS este mes?" onClick={() => { setQuery('¿Cómo ha variado el ROAS este mes?'); }} />
              <SuggestionChip text="Alertas críticas hoy" onClick={() => { setQuery('Ver alertas críticas'); }} />
            </div>
          </div>
        )}

        {/* Lista de mensajes con padding optimizado */}
        <div className="flex-grow space-y-16 pb-32">
          {messages.map((msg, idx) => (
            <div 
              key={idx} 
              className="flex flex-col space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-700"
            >
              {/* Burbuja del Usuario: Elegante y minimalista */}
              <div className="flex justify-start">
                <div className="max-w-[85%] px-6 py-4 rounded-3xl bg-zinc-900/40 border border-zinc-800 text-zinc-100 shadow-sm backdrop-blur-md">
                  <p className="text-sm font-medium leading-relaxed">{msg.query}</p>
                  <span className="text-[10px] text-zinc-600 font-bold uppercase tracking-widest mt-3 block">User Query</span>
                </div>
              </div>

              {/* Burbuja de Synapse: Expandida y rica en visualización */}
              <div className="flex flex-col space-y-4">
                <div className="flex items-center gap-3 mb-2 translate-x-1">
                  <div className="w-6 h-6 rounded-full bg-indigo-500/10 border border-indigo-400/30 flex items-center justify-center">
                    <Activity size={12} className="text-indigo-400" />
                  </div>
                  <span className="text-[10px] font-black text-indigo-400 uppercase tracking-[0.2em]">Intelligence Agent Result</span>
                </div>
                
                <div className="pl-9 space-y-6">
                  <DynamicRenderer data={msg.response} />
                </div>
              </div>
            </div>
          ))}
          
          {isLoading && <div className="space-y-4 pt-4"><SkeletonLoader /></div>}
          
          {error && (
            <div className="p-4 bg-red-950/20 border border-red-900/30 rounded-2xl text-red-400 text-xs italic ml-9">
              {error}
            </div>
          )}
          
          <div ref={messagesEndRef} />
        </div>

        {/* Input de Chat: Glassmorphism y profundidad visual */}
        <form 
          onSubmit={handleSubmit}
          className="fixed bottom-10 left-1/2 -translate-x-1/2 w-full max-w-3xl px-6 z-30"
        >
          <div className="relative group">
            <div className="absolute -inset-1 bg-gradient-to-r from-indigo-500/10 to-purple-500/10 rounded-[28px] blur-xl opacity-0 group-hover:opacity-100 transition duration-1000 group-focus-within:opacity-100" />
            <div className="relative flex items-center gap-3 p-2 bg-zinc-900/60 backdrop-blur-2xl border border-white/10 rounded-[24px] shadow-2xl transition-all duration-500 group-focus-within:border-white/20">
              <input
                type="text"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Ask Synapse for marketing insights..."
                className="flex-grow bg-transparent border-none outline-none px-5 py-3 text-sm text-zinc-100 placeholder-zinc-500 font-medium"
              />
              <button
                type="submit"
                disabled={isLoading || !query.trim()}
                className="p-3 bg-white text-black rounded-2xl hover:bg-zinc-200 disabled:opacity-30 disabled:hover:bg-white transition-all duration-300 shadow-lg active:scale-95"
              >
                <Send size={20} />
              </button>
            </div>
          </div>
          <p className="text-[10px] text-center text-zinc-600 mt-4 uppercase tracking-widest font-black">
            Powered by Snowflake Cortex AI & Buentipo Analytics
          </p>
        </form>
      </div>
    </SynapseChatLayout>
  );
}

const SuggestionChip = ({ text, onClick }: { text: string; onClick: () => void }) => (
  <button 
    onClick={onClick}
    className="px-4 py-2 bg-zinc-900/50 border border-zinc-800 rounded-lg text-xs font-semibold text-zinc-400 hover:border-zinc-700 hover:text-zinc-200 transition-all active:scale-95"
  >
    {text}
  </button>
);
