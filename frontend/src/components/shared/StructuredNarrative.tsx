'use client';

import React from 'react';

interface StructuredNarrativeProps {
  text: string;
  compact?: boolean;
}

const structuralLine = (line: string): boolean => {
  const t = line.trim();
  return (
    /^#{1,4}\s+/.test(t) ||
    /^\d+[\.\)]\s+/.test(t) ||
    /^[-*]\s+/.test(t) ||
    t.startsWith('```')
  );
};

const renderInline = (value: string): React.ReactNode[] => {
  const chunks = value.split(/(\*\*[^*]+\*\*)/g);
  return chunks.map((chunk, idx) => {
    if (chunk.startsWith('**') && chunk.endsWith('**') && chunk.length > 4) {
      return (
        <strong key={idx} className="font-extrabold text-white">
          {chunk.slice(2, -2)}
        </strong>
      );
    }
    return <React.Fragment key={idx}>{chunk}</React.Fragment>;
  });
};

export const StructuredNarrative: React.FC<StructuredNarrativeProps> = ({ text, compact = false }) => {
  const lines = text.replace(/\r/g, '').split('\n');
  const blocks: React.ReactNode[] = [];
  let i = 0;

  while (i < lines.length) {
    const raw = lines[i];
    const line = raw.trim();
    if (!line) {
      i += 1;
      continue;
    }

    if (line.startsWith('```')) {
      const codeLines: string[] = [];
      i += 1;
      while (i < lines.length && !lines[i].trim().startsWith('```')) {
        codeLines.push(lines[i]);
        i += 1;
      }
      if (i < lines.length) i += 1;
      blocks.push(
        <pre
          key={`code-${i}`}
          className="overflow-x-auto rounded-xl border border-zinc-800 bg-zinc-950/80 p-4 text-xs text-zinc-300"
        >
          <code>{codeLines.join('\n')}</code>
        </pre>
      );
      continue;
    }

    const headingMatch = line.match(/^(#{1,4})\s+(.*)$/);
    if (headingMatch) {
      const level = headingMatch[1].length;
      const content = headingMatch[2];
      const cls =
        level <= 2
          ? 'text-2xl md:text-3xl font-black text-white tracking-tight'
          : level === 3
            ? 'text-xl font-extrabold text-zinc-100 tracking-tight'
            : 'text-base font-bold text-zinc-200';
      blocks.push(
        <div key={`h-${i}`} className={level <= 2 ? 'pt-2' : 'pt-1'}>
          <p className={cls}>{renderInline(content)}</p>
        </div>
      );
      i += 1;
      continue;
    }

    if (/^\d+[\.\)]\s+/.test(line)) {
      const items: string[] = [];
      while (i < lines.length && /^\d+[\.\)]\s+/.test(lines[i].trim())) {
        items.push(lines[i].trim().replace(/^\d+[\.\)]\s+/, ''));
        i += 1;
      }
      blocks.push(
        <ol key={`ol-${i}`} className="list-decimal space-y-2 pl-5 text-zinc-200">
          {items.map((item, idx) => (
            <li key={idx} className="leading-relaxed">
              {renderInline(item)}
            </li>
          ))}
        </ol>
      );
      continue;
    }

    if (/^[-*]\s+/.test(line)) {
      const items: string[] = [];
      while (i < lines.length && /^[-*]\s+/.test(lines[i].trim())) {
        items.push(lines[i].trim().replace(/^[-*]\s+/, ''));
        i += 1;
      }
      blocks.push(
        <ul key={`ul-${i}`} className="list-disc space-y-2 pl-5 text-zinc-200">
          {items.map((item, idx) => (
            <li key={idx} className="leading-relaxed">
              {renderInline(item)}
            </li>
          ))}
        </ul>
      );
      continue;
    }

    const paragraph: string[] = [line];
    i += 1;
    while (i < lines.length) {
      const candidate = lines[i].trim();
      if (!candidate || structuralLine(candidate)) break;
      paragraph.push(candidate);
      i += 1;
    }

    blocks.push(
      <p
        key={`p-${i}`}
        className={`${compact ? 'text-sm' : 'text-base'} leading-relaxed text-zinc-200`}
      >
        {renderInline(paragraph.join(' '))}
      </p>
    );
  }

  return <div className="space-y-4">{blocks}</div>;
};
