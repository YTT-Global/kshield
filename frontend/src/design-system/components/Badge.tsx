import React from 'react';

type Severity = 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW';
type Method   = 'GET' | 'POST' | 'PUT' | 'DELETE' | 'PATCH';
type Status   = 'safe' | 'danger' | 'warning' | 'neutral';

const SEVERITY_CLS: Record<Severity, string> = {
  CRITICAL: 'bg-red-100 text-red-700 border-red-200 dark:bg-red-950 dark:text-red-400 dark:border-red-900',
  HIGH:     'bg-orange-100 text-orange-700 border-orange-200 dark:bg-orange-950 dark:text-orange-400 dark:border-orange-900',
  MEDIUM:   'bg-amber-100 text-amber-700 border-amber-200 dark:bg-amber-950 dark:text-amber-400 dark:border-amber-900',
  LOW:      'bg-blue-100 text-blue-700 border-blue-200 dark:bg-blue-950 dark:text-blue-400 dark:border-blue-900',
};

const METHOD_CLS: Record<Method, string> = {
  GET:    'bg-emerald-100 text-emerald-700 border-emerald-200 dark:bg-emerald-950 dark:text-emerald-400 dark:border-emerald-900',
  POST:   'bg-blue-100 text-blue-700 border-blue-200 dark:bg-blue-950 dark:text-blue-400 dark:border-blue-900',
  PUT:    'bg-amber-100 text-amber-700 border-amber-200 dark:bg-amber-950 dark:text-amber-400 dark:border-amber-900',
  DELETE: 'bg-red-100 text-red-700 border-red-200 dark:bg-red-950 dark:text-red-400 dark:border-red-900',
  PATCH:  'bg-purple-100 text-purple-700 border-purple-200 dark:bg-purple-950 dark:text-purple-400 dark:border-purple-900',
};

const STATUS_CLS: Record<Status, string> = {
  safe:    'bg-emerald-100 text-emerald-700 dark:bg-emerald-950 dark:text-emerald-400',
  danger:  'bg-red-100 text-red-700 dark:bg-red-950 dark:text-red-400',
  warning: 'bg-amber-100 text-amber-700 dark:bg-amber-950 dark:text-amber-400',
  neutral: 'bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-400',
};

const BASE = 'inline-flex items-center text-[10px] font-bold font-mono px-2 py-0.5 rounded-md border uppercase';

interface SeverityBadgeProps { severity: Severity }
export function SeverityBadge({ severity }: SeverityBadgeProps) {
  return <span className={`${BASE} ${SEVERITY_CLS[severity]}`}>{severity}</span>;
}

interface MethodBadgeProps { method: Method }
export function MethodBadge({ method }: MethodBadgeProps) {
  return <span className={`${BASE} ${METHOD_CLS[method]}`}>{method}</span>;
}

interface StatusBadgeProps { status: Status; label: string }
export function StatusBadge({ status, label }: StatusBadgeProps) {
  return (
    <span className={`text-[10px] font-semibold font-mono px-2 py-0.5 rounded-full ${STATUS_CLS[status]}`}>
      {label}
    </span>
  );
}

interface LabelBadgeProps { label: string; className?: string }
export function LabelBadge({ label, className = '' }: LabelBadgeProps) {
  return (
    <span className={`text-[10px] font-mono px-1.5 py-0.5 rounded bg-slate-100 dark:bg-slate-800 text-slate-500 dark:text-slate-400 ${className}`}>
      {label}
    </span>
  );
}
