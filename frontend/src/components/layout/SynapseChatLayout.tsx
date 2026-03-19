import React, { ReactNode } from 'react';
import { Sparkles, BarChart2, LayoutDashboard, Settings } from 'lucide-react';

interface Props {
  children: ReactNode;
}

export const SynapseChatLayout: React.FC<Props> = ({ children }) => {
  return (
    <div className="flex h-screen bg-black text-zinc-100 overflow-hidden font-sans">
      {/* Sidebar Corporativo */}
      <aside className="w-64 border-r border-zinc-900 flex flex-col p-4 space-y-8">
        <div className="flex items-center gap-3 px-2 py-4">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-tr from-indigo-600 to-indigo-400 flex items-center justify-center shadow-lg shadow-indigo-500/20">
            <Sparkles size={18} className="text-white fill-white" />
          </div>
          <span className="font-bold text-xl tracking-tight">Synapse</span>
        </div>

        <nav className="flex-grow space-y-1">
          <SidebarItem icon={<LayoutDashboard size={18} />} label="Overview" active />
          <SidebarItem icon={<BarChart2 size={18} />} label="Data Storytelling" />
          <SidebarItem icon={<Settings size={18} />} label="Workspace" />
        </nav>

        <div className="px-2 py-4 border-t border-zinc-900 text-xs text-zinc-500 font-medium">
          Lobueno Group © 2026
        </div>
      </aside>

      {/* Área de Contenido Principal */}
      <main className="flex-grow flex flex-col relative bg-zinc-950/20">
        <header className="h-16 border-b border-zinc-900 bg-black/40 backdrop-blur-md sticky top-0 z-10 flex items-center px-8">
          <h2 className="text-sm font-semibold text-zinc-400 uppercase tracking-widest">Workspace / Enterprise Analytics</h2>
        </header>

        <div className="flex-grow overflow-y-auto px-8 py-10 scrollbar-hide">
          <div className="max-w-4xl mx-auto w-full space-y-12">
            {children}
          </div>
        </div>
      </main>
    </div>
  );
};

const SidebarItem = ({ icon, label, active = false }: { icon: React.ReactNode; label: string; active?: boolean }) => (
  <button className={`w-full flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-all ${
    active ? 'bg-zinc-900 text-indigo-400 border border-zinc-800 shadow-sm' : 'text-zinc-500 hover:bg-zinc-900/40 hover:text-zinc-300'
  }`}>
    {icon}
    {label}
  </button>
);
