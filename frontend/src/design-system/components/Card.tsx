import React from 'react';
import type { LucideIcon } from 'lucide-react';

interface CardProps {
  children: React.ReactNode;
  className?: string;
  padding?: boolean;
}

export function Card({ children, className = '', padding = true }: CardProps) {
  return (
    <div className={`
      bg-white dark:bg-slate-900
      border border-slate-200 dark:border-slate-800
      rounded-xl shadow-sm dark:shadow-none
      ${padding ? 'p-6' : ''}
      ${className}
    `}>
      {children}
    </div>
  );
}

interface CardHeaderProps {
  title: string;
  subtitle?: string;
  icon?: LucideIcon;
  action?: React.ReactNode;
}

export function CardHeader({ title, subtitle, icon: Icon, action }: CardHeaderProps) {
  return (
    <div className="flex items-center justify-between mb-5">
      <div className="flex items-center gap-4">
        {Icon && (
          <div className="h-9 w-9 rounded-lg bg-red-600/10 dark:bg-red-600/20 flex items-center justify-center flex-shrink-0">
            <Icon size={18} className="text-red-600 dark:text-red-500" />
          </div>
        )}
        <div>
          <h3 className="text-base font-bold text-slate-900 dark:text-white">{title}</h3>
          {subtitle && <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">{subtitle}</p>}
        </div>
      </div>
      {action && <div className="flex-shrink-0">{action}</div>}
    </div>
  );
}

interface CardTableHeaderProps {
  label: string;
  count?: number;
}

export function CardTableHeader({ label, count }: CardTableHeaderProps) {
  return (
    <div className="px-4 py-3.5 border-b border-slate-200 dark:border-slate-800 flex items-center justify-between flex-shrink-0">
      <span className="text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">{label}</span>
      {count !== undefined && (
        <span className="text-[11px] font-mono bg-slate-100 dark:bg-slate-800 text-slate-500 dark:text-slate-400 px-2 py-0.5 rounded-full">
          {count}
        </span>
      )}
    </div>
  );
}

interface MetricCardProps {
  label: string;
  value: number | string;
  icon: LucideIcon;
  valueColor?: string;
}

export function MetricCard({ label, value, icon: Icon, valueColor = 'text-slate-900 dark:text-white' }: MetricCardProps) {
  return (
    <div className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 p-4 lg:p-5 shadow-sm dark:shadow-none">
      <div className="flex items-center justify-between mb-2 lg:mb-3">
        <span className="text-[10px] lg:text-xs font-semibold uppercase tracking-wide text-slate-400 dark:text-slate-500 leading-tight">{label}</span>
        <Icon size={16} className={`${valueColor} flex-shrink-0`} />
      </div>
      <p className={`text-2xl lg:text-3xl font-bold font-mono ${valueColor}`}>{value}</p>
    </div>
  );
}
