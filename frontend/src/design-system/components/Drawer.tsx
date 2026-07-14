import React, { useEffect } from 'react';
import { X } from 'lucide-react';

interface DrawerProps {
  open: boolean;
  onClose: () => void;
  title?: React.ReactNode;
  footer?: React.ReactNode;
  children: React.ReactNode;
}

export function Drawer({ open, onClose, title, footer, children }: DrawerProps) {
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose(); };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [onClose]);

  return (
    <>
      {/* Backdrop */}
      <div
        onClick={onClose}
        className={`fixed inset-0 bg-black/40 dark:bg-black/60 backdrop-blur-sm z-30 transition-opacity duration-300 ${
          open ? 'opacity-100 pointer-events-auto' : 'opacity-0 pointer-events-none'
        }`}
      />

      {/* Panel */}
      <div className={`
        fixed top-0 right-0 h-full w-full sm:w-[500px] z-40 flex flex-col
        bg-white dark:bg-slate-900
        border-l border-slate-200 dark:border-slate-700
        shadow-2xl shadow-slate-300/40 dark:shadow-black/60
        transition-transform duration-300 ease-in-out
        ${open ? 'translate-x-0' : 'translate-x-full'}
      `}>
        {title && (
          <div className="flex items-start justify-between px-5 sm:px-6 py-5 border-b border-slate-200 dark:border-slate-800 flex-shrink-0">
            <div className="flex-1 pr-4 min-w-0">{title}</div>
            <button
              onClick={onClose}
              title="Close (Esc)"
              className="flex-shrink-0 h-9 w-9 flex items-center justify-center rounded-lg transition-colors
                bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700
                text-slate-500 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white"
            >
              <X size={15} />
            </button>
          </div>
        )}

        <div className="flex-1 overflow-y-auto px-5 sm:px-6 py-5">
          {children}
        </div>

        {footer && (
          <div className="px-5 sm:px-6 py-4 border-t border-slate-200 dark:border-slate-800 flex gap-3 flex-shrink-0">
            {footer}
          </div>
        )}
      </div>
    </>
  );
}
