import React from 'react';
import { AlertTriangle, Info, CheckCircle2, XCircle } from 'lucide-react';

type AlertVariant = 'info' | 'warning' | 'success' | 'error';

const VARIANT_CONFIG: Record<AlertVariant, {
  cls: string;
  Icon: React.ElementType;
  iconCls: string;
}> = {
  info: {
    cls:     'bg-blue-50 dark:bg-blue-950/30 border-blue-200 dark:border-blue-900',
    Icon:    Info,
    iconCls: 'text-blue-600 dark:text-blue-400',
  },
  warning: {
    cls:     'bg-amber-50 dark:bg-amber-950/30 border-amber-200 dark:border-amber-900',
    Icon:    AlertTriangle,
    iconCls: 'text-amber-600 dark:text-amber-400',
  },
  success: {
    cls:     'bg-emerald-50 dark:bg-emerald-950/30 border-emerald-200 dark:border-emerald-900',
    Icon:    CheckCircle2,
    iconCls: 'text-emerald-600 dark:text-emerald-400',
  },
  error: {
    cls:     'bg-red-50 dark:bg-red-950/30 border-red-200 dark:border-red-900',
    Icon:    XCircle,
    iconCls: 'text-red-600 dark:text-red-400',
  },
};

const TEXT_CLS: Record<AlertVariant, string> = {
  info:    'text-blue-700 dark:text-blue-400',
  warning: 'text-amber-700 dark:text-amber-400',
  success: 'text-emerald-700 dark:text-emerald-400',
  error:   'text-red-700 dark:text-red-400',
};

interface AlertProps {
  variant?: AlertVariant;
  children: React.ReactNode;
}

export function Alert({ variant = 'info', children }: AlertProps) {
  const { cls, Icon, iconCls } = VARIANT_CONFIG[variant];
  return (
    <div className={`flex items-start gap-3 p-3.5 rounded-lg border ${cls}`}>
      <Icon size={14} className={`${iconCls} mt-0.5 flex-shrink-0`} />
      <p className={`text-xs leading-relaxed ${TEXT_CLS[variant]}`}>{children}</p>
    </div>
  );
}
