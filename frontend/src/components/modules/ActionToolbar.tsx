import React from 'react';
import { Download, FileText, Share2, Copy } from 'lucide-react';

interface Props {
  responseId: string;
  data?: any[];
}

export const ActionToolbar: React.FC<Props> = ({ responseId, data }) => {
  const handleExportCSV = () => {
    console.log(`[Synapse] Exporting CSV for ${responseId}`, data);
  };

  const handleExportPDF = () => {
    console.log(`[Synapse] Exporting PDF for ${responseId}`);
  };

  return (
    <div className="flex items-center gap-4 py-2">
      <button 
        onClick={handleExportCSV}
        className="flex items-center gap-2 text-xs font-semibold text-zinc-400 hover:text-indigo-400 transition-colors"
      >
        <Download size={14} />
        Exportar CSV
      </button>
      <button 
        onClick={handleExportPDF}
        className="flex items-center gap-2 text-xs font-semibold text-zinc-400 hover:text-indigo-400 transition-colors"
      >
        <FileText size={14} />
        PDF Report
      </button>
      <div className="flex-grow" />
      <button className="text-zinc-600 hover:text-zinc-400">
        <Copy size={14} />
      </button>
      <button className="text-zinc-600 hover:text-zinc-400">
        <Share2 size={14} />
      </button>
    </div>
  );
};
