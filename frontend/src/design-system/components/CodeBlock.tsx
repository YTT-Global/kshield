import React, { useState } from 'react';
import { Copy, Check } from 'lucide-react';

interface CodeBlockProps {
  code: string;
  language?: string;
  showCopy?: boolean;
}

export function CodeBlock({ code, language = 'bash', showCopy = true }: CodeBlockProps) {
  const [copied, setCopied] = useState(false);

  const copy = () => {
    navigator.clipboard.writeText(code);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="relative group">
      <pre className={`bg-slate-950 dark:bg-black border border-slate-800 rounded-lg p-4 overflow-x-auto text-[12px] font-mono leading-relaxed text-slate-300 lang-${language}`}>
        {code}
      </pre>
      {showCopy && (
        <button
          onClick={copy}
          className="absolute top-2.5 right-2.5 h-7 w-7 flex items-center justify-center rounded-md
            bg-slate-800 hover:bg-slate-700 text-slate-400 hover:text-white
            transition-colors opacity-0 group-hover:opacity-100"
          title="Copy"
        >
          {copied ? <Check size={12} /> : <Copy size={12} />}
        </button>
      )}
    </div>
  );
}

interface InlineCodeProps {
  children: React.ReactNode;
  className?: string;
}

export function InlineCode({ children, className = '' }: InlineCodeProps) {
  return (
    <code className={`font-mono text-xs bg-slate-100 dark:bg-slate-800 text-slate-800 dark:text-slate-200 px-1.5 py-0.5 rounded ${className}`}>
      {children}
    </code>
  );
}

interface DiffViewerProps {
  diff: string;
}

export function DiffViewer({ diff }: DiffViewerProps) {
  const lineClass = (line: string): string => {
    if (line.startsWith('---') || line.startsWith('+++')) return 'text-slate-400 dark:text-slate-500 block px-1';
    if (line.startsWith('-')) return 'text-red-600 dark:text-red-400 bg-red-50 dark:bg-red-950/30 block px-1';
    if (line.startsWith('+')) return 'text-emerald-600 dark:text-emerald-400 bg-emerald-50 dark:bg-emerald-950/30 block px-1';
    if (line.startsWith('@@')) return 'text-blue-600 dark:text-blue-400 block px-1';
    return 'text-slate-500 block px-1';
  };
  return (
    <pre className="p-3 bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 rounded-lg overflow-x-auto text-[11px] font-mono leading-relaxed">
      {diff.split('\n').map((line, i) => (
        <span key={i} className={lineClass(line)}>{line || ' '}</span>
      ))}
    </pre>
  );
}
