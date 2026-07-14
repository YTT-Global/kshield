import React from 'react';
import type { LucideIcon } from 'lucide-react';

type Variant = 'primary' | 'secondary' | 'ghost' | 'danger';
type Size    = 'sm' | 'md' | 'lg';

const VARIANT_CLS: Record<Variant, string> = {
  primary:   'bg-red-600 hover:bg-red-700 text-white shadow-sm shadow-red-600/20 hover:shadow-md hover:shadow-red-600/30',
  secondary: 'bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-300 border border-slate-200 dark:border-slate-700',
  ghost:     'text-slate-500 dark:text-slate-400 hover:bg-slate-50 dark:hover:bg-slate-800/50 hover:text-slate-800 dark:hover:text-slate-200',
  danger:    'bg-red-50 dark:bg-red-950/30 hover:bg-red-100 dark:hover:bg-red-950 text-red-600 dark:text-red-400 border border-red-200 dark:border-red-900',
};

const SIZE_CLS: Record<Size, string> = {
  sm:  'px-2.5 py-1.5 text-xs rounded-md gap-1.5',
  md:  'px-3.5 py-2.5 text-sm rounded-lg gap-2',
  lg:  'px-5 py-3 text-sm rounded-xl gap-2.5',
};

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant;
  size?: Size;
  icon?: LucideIcon;
  iconRight?: LucideIcon;
  loading?: boolean;
  fullWidth?: boolean;
}

export function Button({
  variant = 'primary',
  size = 'md',
  icon: Icon,
  iconRight: IconRight,
  loading = false,
  fullWidth = false,
  children,
  className = '',
  disabled,
  ...props
}: ButtonProps) {
  const iconSize = size === 'sm' ? 12 : size === 'md' ? 14 : 16;

  return (
    <button
      {...props}
      disabled={disabled || loading}
      className={`
        inline-flex items-center justify-center font-semibold transition-all duration-150
        disabled:opacity-50 disabled:cursor-not-allowed
        ${VARIANT_CLS[variant]}
        ${SIZE_CLS[size]}
        ${fullWidth ? 'w-full' : ''}
        ${className}
      `}
    >
      {loading ? (
        <span className="h-3.5 w-3.5 rounded-full border-2 border-current border-t-transparent animate-spin" />
      ) : Icon ? (
        <Icon size={iconSize} className="flex-shrink-0" />
      ) : null}
      {children}
      {IconRight && !loading && <IconRight size={iconSize} className="flex-shrink-0" />}
    </button>
  );
}
