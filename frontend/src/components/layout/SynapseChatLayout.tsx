'use client';

import React, { ReactNode, useState } from 'react';
import Image from 'next/image';
import { BarChart3, ChevronsLeft, ChevronsRight, LayoutDashboard } from 'lucide-react';

interface Props {
  children: ReactNode;
  onViewChange?: (view: string) => void;
  currentView?: 'chat' | 'intelligence';
}

export const SynapseChatLayout: React.FC<Props> = ({ children, onViewChange, currentView = 'chat' }) => {
  const [collapsed, setCollapsed] = useState(false);

  return (
    <div className="flex h-screen bg-[#141414] text-zinc-100 overflow-hidden font-sans">
      {/* Sidebar Corporativo Premium */}
      <aside
        className={`m-4 rounded-2xl border border-white/20 shadow-[0_0_26px_rgba(255,255,255,0.10)] flex flex-col bg-[#050505]/62 backdrop-blur-xl transition-all duration-300 ${
          collapsed ? 'w-20 p-3' : 'w-72 p-6'
        }`}
      >
        <div className={`flex items-center ${collapsed ? 'justify-center' : 'justify-between'} pb-2`}>
          {!collapsed && (
            <div className="relative w-full h-20">
              <Image
                src="/SYNAPSE BT COLORS - LIGHT BKG.png"
                alt="Synapse Logo"
                fill
                className="object-contain"
                priority
              />
            </div>
          )}
          {collapsed && (
            <div className="w-10 h-10 rounded-xl bg-zinc-900/70 border border-zinc-700 flex items-center justify-center">
              <BarChart3 size={18} className="text-indigo-300" />
            </div>
          )}
          <button
            onClick={() => setCollapsed((prev) => !prev)}
            className={`rounded-lg border border-zinc-700 bg-zinc-900/60 hover:border-zinc-500 transition-colors ${
              collapsed ? 'mt-3 p-2' : 'ml-3 p-2'
            }`}
            title={collapsed ? 'Expandir menú' : 'Colapsar menú'}
            aria-label={collapsed ? 'Expandir menú lateral' : 'Colapsar menú lateral'}
          >
            {collapsed ? <ChevronsRight size={16} /> : <ChevronsLeft size={16} />}
          </button>
        </div>

        <nav className={`flex-grow space-y-2 ${collapsed ? 'mt-4' : 'mt-2'}`}>
          <SidebarItem
            icon={<LayoutDashboard size={19} />}
            label="Analytic Chat"
            active={currentView === 'chat'}
            onClick={() => onViewChange?.('chat')}
            collapsed={collapsed}
          />
          <SidebarItem
            icon={<BarChart3 size={19} />}
            label="Marketing Intelligence"
            active={currentView === 'intelligence'}
            onClick={() => onViewChange?.('intelligence')}
            collapsed={collapsed}
          />
        </nav>

        {/* Footer Sidebar */}
        {!collapsed && (
          <div className="px-3 py-4 border-t border-zinc-900">
            <p className="text-[10px] font-bold uppercase tracking-[0.25em] text-zinc-600">Synapse Workspace</p>
            <p className="mt-2 text-xs text-zinc-500">Vista enfocada en análisis y lectura ejecutiva de negocio.</p>
          </div>
        )}
      </aside>

      {/* Área de Contenido Principal con fondo degradado sutil */}
      <main className="flex-grow flex flex-col relative bg-[linear-gradient(to_bottom,#17283A_0%,#141414_100%)]">
        <header className="h-20 border-b border-white/10 bg-black/25 backdrop-blur-md sticky top-0 z-20 flex items-center px-10">
          <div className="flex items-center gap-2">
            <div className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
            <h2 className="text-xs font-bold text-zinc-500 uppercase tracking-widest">Synapse Analyst Workspace</h2>
          </div>
        </header>

        <div className="flex-grow overflow-y-auto px-6 xl:px-10 py-12 scrollbar-hide">
          <div className="max-w-[96rem] mx-auto w-full">
            {children}
          </div>
        </div>
      </main>
    </div>
  );
};

const SidebarItem = ({
  icon,
  label,
  active = false,
  onClick,
  collapsed = false,
}: {
  icon: React.ReactNode;
  label: string;
  active?: boolean;
  onClick?: () => void;
  collapsed?: boolean;
}) => (
  <button 
    onClick={onClick}
    className={`w-full flex items-center ${
      collapsed ? 'justify-center px-2' : 'gap-4 px-4'
    } py-3 rounded-xl text-sm font-semibold transition-all duration-300 group ${
    active 
      ? 'bg-zinc-100/10 text-white border border-zinc-800 shadow-[0_0_15px_rgba(99,102,241,0.05)]' 
      : 'text-zinc-500 hover:bg-zinc-100/5 hover:text-zinc-300'
  }`}>
    <span className={`${active ? 'text-indigo-400' : 'group-hover:text-zinc-300'}`}>{icon}</span>
    {!collapsed && label}
  </button>
);
