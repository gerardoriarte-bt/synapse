import React, { ReactNode } from 'react';
import Image from 'next/image';
import { BarChart3, LayoutDashboard } from 'lucide-react';

interface Props {
  children: ReactNode;
  onViewChange?: (view: string) => void;
  currentView?: 'chat' | 'intelligence';
}

export const SynapseChatLayout: React.FC<Props> = ({ children, onViewChange, currentView = 'chat' }) => {
  return (
    <div className="flex h-screen bg-[#141414] text-zinc-100 overflow-hidden font-sans">
      {/* Sidebar Corporativo Premium */}
      <aside className="w-72 border-r border-zinc-900 flex flex-col p-6 space-y-10 bg-[#050505]/80 backdrop-blur-xl">
        <div className="flex items-center justify-center px-4 pb-2">
          <div className="relative w-full h-20">
            <Image 
              src="/SYNAPSE BT COLORS - LIGHT BKG.png" 
              alt="Synapse Logo" 
              fill
              className="object-contain"
              priority
            />
          </div>
        </div>

        <nav className="flex-grow space-y-2">
          <SidebarItem 
            icon={<LayoutDashboard size={19} />} 
            label="Analytic Chat" 
            active={currentView === 'chat'}
            onClick={() => onViewChange?.('chat')}
          />
          <SidebarItem 
            icon={<BarChart3 size={19} />} 
            label="Marketing Intelligence" 
            active={currentView === 'intelligence'}
            onClick={() => onViewChange?.('intelligence')}
          />
        </nav>

        {/* Footer Sidebar */}
        <div className="px-3 py-4 border-t border-zinc-900">
          <p className="text-[10px] font-bold uppercase tracking-[0.25em] text-zinc-600">Synapse Workspace</p>
          <p className="mt-2 text-xs text-zinc-500">Vista enfocada en análisis y lectura ejecutiva de negocio.</p>
        </div>
      </aside>

      {/* Área de Contenido Principal con fondo degradado sutil */}
      <main className="flex-grow flex flex-col relative bg-[linear-gradient(to_bottom,#17283A_0%,#141414_100%)]">
        <header className="h-20 border-b border-white/10 bg-black/25 backdrop-blur-md sticky top-0 z-20 flex items-center px-10">
          <div className="flex items-center gap-2">
            <div className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
            <h2 className="text-xs font-bold text-zinc-500 uppercase tracking-widest">Synapse Analyst Workspace</h2>
          </div>
        </header>

        <div className="flex-grow overflow-y-auto px-10 py-12 scrollbar-hide">
          <div className="max-w-5xl mx-auto w-full">
            {children}
          </div>
        </div>
      </main>
    </div>
  );
};

const SidebarItem = ({ icon, label, active = false, onClick }: { icon: React.ReactNode; label: string; active?: boolean; onClick?: () => void }) => (
  <button 
    onClick={onClick}
    className={`w-full flex items-center gap-4 px-4 py-3 rounded-xl text-sm font-semibold transition-all duration-300 group ${
    active 
      ? 'bg-zinc-100/10 text-white border border-zinc-800 shadow-[0_0_15px_rgba(99,102,241,0.05)]' 
      : 'text-zinc-500 hover:bg-zinc-100/5 hover:text-zinc-300'
  }`}>
    <span className={`${active ? 'text-indigo-400' : 'group-hover:text-zinc-300'}`}>{icon}</span>
    {label}
  </button>
);
