'use client';

import React, { useState } from 'react';
import { SynapseChatLayout } from '@/components/layout/SynapseChatLayout';
import { DynamicRenderer } from '@/components/modules/DynamicRenderer';
import { SkeletonLoader } from '@/components/shared/SkeletonLoader';
import { useSynapseQuery } from '@/hooks/useSynapseQuery';
import { Send, Zap, Command } from 'lucide-react';

export default function Home() {
  const [query, setQuery] = useState('');
  const { askSynapse, isLoading, response, error } = useSynapseQuery();

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim()) return;
    askSynapse(query);
    setQuery('');
  };

  return (
    <SynapseChatLayout>
      <div className="space-y-12 pb-24">
        {/* Empty State / Welcome */}
        {!response && !isLoading && (
          <div className="flex flex-col items-center justify-center pt-20 text-center space-y-6">
            <div className="w-16 h-16 rounded-2xl bg-zinc-900 border border-zinc-800 flex items-center justify-center shadow-xl">
              <Zap className="text-zinc-600 fill-zinc-600" size={32} />
            </div>
            <div className="space-y-2">
              <h1 className="text-4xl font-bold tracking-tight text-white">¿Qué quieres analizar hoy?</h1>
              <p className="text-zinc-500 max-w-md mx-auto italic">Pregunta sobre ROAS, anomalías de tráfico o eficiencia de pauta.</p>
            </div>
            <div className="flex gap-2">
              <SuggestionChip text="¿Cómo ha variado el ROAS este mes?" onClick={() => askSynapse('¿Cómo ha variado el ROAS este mes?')} />
              <SuggestionChip text="Alertas críticas hoy" onClick={() => askSynapse('Ver alertas críticas')} />
            </div>
          </div>
        )}

        {/* Loading State */}
        {isLoading && <SkeletonLoader />}

        {/* Error State */}
        {error && (
          <div className="p-4 bg-red-950/20 border border-red-900/50 rounded-xl text-red-400 text-sm italic">
            {error}
          </div>
        )}

        {/* Response State */}
        {response && !isLoading && (
          <div className="space-y-8">
             <DynamicRenderer data={response} />
          </div>
        )}
      </div>

      {/* Input Flotante / Barra de Comandos */}
      <div className="fixed bottom-10 left-1/2 -translate-x-1/2 w-full max-w-3xl px-6">
        <form 
          onSubmit={handleSubmit}
          className="relative group flex items-center bg-zinc-900/60 backdrop-blur-xl border border-zinc-800 p-2 pl-4 rounded-2xl shadow-2xl focus-within:border-indigo-500/50 transition-all duration-300"
        >
          <Command className="text-zinc-600 mr-2" size={18} />
          <input 
            type="text" 
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Analizar datos de pauta histórica..."
            className="flex-grow bg-transparent border-none outline-none text-sm text-zinc-100 placeholder:text-zinc-600 h-10"
          />
          <button 
            type="submit"
            className="bg-indigo-600 hover:bg-indigo-500 text-white p-2 rounded-xl transition-all shadow-lg active:scale-95 disabled:opacity-50"
            disabled={!query.trim()}
          >
            <Send size={18} />
          </button>
        </form>
        <div className="mt-3 text-[10px] text-center text-zinc-600 uppercase tracking-widest font-bold">
          Empowering Data Decisions • AI Engine v2.0
        </div>
      </div>
    </SynapseChatLayout>
  );
}

const SuggestionChip = ({ text, onClick }: { text: string; onClick: () => void }) => (
  <button 
    onClick={onClick}
    className="px-4 py-2 bg-zinc-900/50 border border-zinc-800 rounded-lg text-xs font-semibold text-zinc-400 hover:border-zinc-700 hover:text-zinc-200 transition-all"
  >
    {text}
  </button>
);
