import React from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

interface Props {
  content: string;
  className?: string;
}

export const MarkdownNarrative: React.FC<Props> = ({ content, className }) => {
  return (
    <div className={className}>
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          h2: ({ children }) => (
            <h2 className="mt-1 mb-3 text-xl font-semibold text-white">{children}</h2>
          ),
          h3: ({ children }) => (
            <h3 className="mt-4 mb-2 text-lg font-semibold text-zinc-100">{children}</h3>
          ),
          p: ({ children }) => (
            <p className="mb-3 whitespace-pre-wrap text-zinc-100 leading-relaxed">{children}</p>
          ),
          ul: ({ children }) => <ul className="mb-3 list-disc pl-6 text-zinc-100">{children}</ul>,
          ol: ({ children }) => (
            <ol className="mb-3 list-decimal pl-6 text-zinc-100">{children}</ol>
          ),
          li: ({ children }) => <li className="mb-1">{children}</li>,
          table: ({ children }) => (
            <div className="my-4 overflow-x-auto rounded-lg border border-zinc-800">
              <table className="min-w-full border-collapse text-sm">{children}</table>
            </div>
          ),
          thead: ({ children }) => <thead className="bg-zinc-900/80">{children}</thead>,
          tbody: ({ children }) => <tbody className="bg-zinc-950/40">{children}</tbody>,
          tr: ({ children }) => <tr className="border-b border-zinc-800">{children}</tr>,
          th: ({ children }) => (
            <th className="px-3 py-2 text-left font-semibold text-zinc-200">{children}</th>
          ),
          td: ({ children }) => <td className="px-3 py-2 align-top text-zinc-100">{children}</td>,
          strong: ({ children }) => <strong className="font-semibold text-white">{children}</strong>,
          em: ({ children }) => <em className="text-zinc-200">{children}</em>,
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
};
