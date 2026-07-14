import React from 'react';
import type { LucideIcon } from 'lucide-react';

type Tone = 'neutral' | 'success' | 'error';

const TONE_CLS: Record<Tone, { wrapper: string; icon: string }> = {
  neutral: { wrapper: 'bg-slate-100 dark:bg-slate-800',      icon: 'text-slate-400 dark:text-slate-500' },
  success: { wrapper: 'bg-emerald-100 dark:bg-emerald-950',  icon: 'text-emerald-600 dark:text-emerald-400' },
  error:   { wrapper: 'bg-red-100 dark:bg-red-950',          icon: 'text-red-600 dark:text-red-400' },
};

interface EmptyStateProps {
  icon: LucideIcon;
  title: string;
  description: string;
  tone?: Tone;
  action?: React.ReactNode;
}

export function EmptyState({ icon: Icon, title, description, tone = 'neutral', action }: EmptyStateProps) {
  const { wrapper, icon } = TONE_CLS[tone];
  return (
    <div className="flex flex-col items-center justify-center h-full p-8 text-center">
      <div className={`w-12 h-12 rounded-full ${wrapper} flex items-center justify-center mb-3`}>
        <Icon size={22} className={icon} />
      </div>
      <h3 className="text-sm font-semibold text-slate-900 dark:text-white mb-1">{title}</h3>
      <p className="text-xs text-slate-400 dark:text-slate-500 max-w-xs leading-relaxed">{description}</p>
      {action && <div className="mt-4">{action}</div>}
    </div>
  );
}
