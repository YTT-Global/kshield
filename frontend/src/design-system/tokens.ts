// KShield Design Tokens
// Single source of truth for all visual decisions.

export const colors = {
  brand: {
    DEFAULT: 'red-600',
    hover:   'red-700',
    light:   'red-50',
    muted:   'red-600/10',
    shadow:  'red-600/25',
  },
  severity: {
    CRITICAL: {
      bg:     'bg-red-100 dark:bg-red-950',
      text:   'text-red-700 dark:text-red-400',
      border: 'border-red-200 dark:border-red-900',
    },
    HIGH: {
      bg:     'bg-orange-100 dark:bg-orange-950',
      text:   'text-orange-700 dark:text-orange-400',
      border: 'border-orange-200 dark:border-orange-900',
    },
    MEDIUM: {
      bg:     'bg-amber-100 dark:bg-amber-950',
      text:   'text-amber-700 dark:text-amber-400',
      border: 'border-amber-200 dark:border-amber-900',
    },
    LOW: {
      bg:     'bg-blue-100 dark:bg-blue-950',
      text:   'text-blue-700 dark:text-blue-400',
      border: 'border-blue-200 dark:border-blue-900',
    },
  },
  status: {
    success: 'bg-emerald-500',
    warning: 'bg-amber-500',
    danger:  'bg-red-500',
  },
  surface: {
    page:    'bg-slate-50 dark:bg-slate-950',
    card:    'bg-white dark:bg-slate-900',
    raised:  'bg-slate-50 dark:bg-slate-800/50',
    overlay: 'bg-slate-950 dark:bg-black',
  },
  border: {
    DEFAULT: 'border-slate-200 dark:border-slate-800',
    subtle:  'border-slate-100 dark:border-slate-800',
  },
  text: {
    primary:   'text-slate-900 dark:text-white',
    secondary: 'text-slate-500 dark:text-slate-400',
    muted:     'text-slate-400 dark:text-slate-600',
    code:      'text-slate-300',
  },
} as const;

export const radius = {
  sm:  'rounded-md',
  md:  'rounded-lg',
  lg:  'rounded-xl',
  full: 'rounded-full',
} as const;

export const shadow = {
  card:  'shadow-sm dark:shadow-none',
  brand: 'shadow-lg shadow-red-600/25',
} as const;

export const font = {
  mono: 'font-mono',
  sans: 'font-sans',
  sizes: {
    label: 'text-[10px]',
    xs:    'text-xs',
    sm:    'text-sm',
    base:  'text-base',
    lg:    'text-xl sm:text-2xl',
  },
} as const;
