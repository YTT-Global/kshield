type DotStatus = 'active' | 'idle' | 'error' | 'warning';

const DOT_CLS: Record<DotStatus, string> = {
  active:  'bg-emerald-500 animate-pulse',
  idle:    'bg-slate-400 dark:bg-slate-600',
  error:   'bg-red-500',
  warning: 'bg-amber-500',
};

interface StatusDotProps {
  status: DotStatus;
  label?: string;
}

export function StatusDot({ status, label }: StatusDotProps) {
  return (
    <div className="flex items-center gap-2">
      <span className={`h-2 w-2 rounded-full flex-shrink-0 ${DOT_CLS[status]}`} />
      {label && (
        <span className="text-xs font-mono text-slate-400 dark:text-slate-500">{label}</span>
      )}
    </div>
  );
}

interface LivePillProps {
  label: string;
}

export function LivePill({ label }: LivePillProps) {
  return (
    <div className="flex items-center gap-2 text-xs font-mono px-3 py-1.5 rounded-full
      bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800
      text-slate-500 dark:text-slate-400 shadow-sm dark:shadow-none whitespace-nowrap">
      <span className="h-1.5 w-1.5 rounded-full bg-emerald-500 animate-pulse" />
      {label}
    </div>
  );
}
