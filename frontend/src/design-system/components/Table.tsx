import React from 'react';

interface Column<T> {
  key: keyof T | string;
  label: string;
  width?: string;
  render?: (row: T) => React.ReactNode;
}

interface TableProps<T> {
  columns: Column<T>[];
  rows: T[];
  keyField: keyof T;
  emptyMessage?: string;
}

export function Table<T extends Record<string, unknown>>({
  columns,
  rows,
  keyField,
  emptyMessage = 'No data.',
}: TableProps<T>) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-slate-200 dark:border-slate-800">
            {columns.map(col => (
              <th
                key={String(col.key)}
                className={`text-left pb-2.5 text-[10px] font-semibold uppercase tracking-wide text-slate-400 dark:text-slate-500 ${col.width ?? ''}`}
              >
                {col.label}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
          {rows.length === 0 ? (
            <tr>
              <td colSpan={columns.length} className="py-8 text-center text-xs text-slate-400 dark:text-slate-600">
                {emptyMessage}
              </td>
            </tr>
          ) : rows.map(row => (
            <tr key={String(row[keyField])} className="hover:bg-slate-50/60 dark:hover:bg-slate-800/30 transition-colors">
              {columns.map(col => (
                <td key={String(col.key)} className="py-3 pr-4 align-top text-slate-600 dark:text-slate-400">
                  {col.render ? col.render(row) : String(row[col.key as keyof T] ?? '')}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

interface FieldTableProps {
  fields: {
    name: string;
    type: string;
    required?: boolean;
    description: string;
  }[];
}

export function FieldTable({ fields }: FieldTableProps) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm border border-slate-100 dark:border-slate-800 rounded-lg overflow-hidden">
        <thead>
          <tr className="bg-slate-50 dark:bg-slate-800/50 border-b border-slate-100 dark:border-slate-800">
            {['Field', 'Type', 'Description'].map(h => (
              <th key={h} className="text-left px-4 py-2.5 text-[10px] font-semibold uppercase tracking-wide text-slate-400 dark:text-slate-500">
                {h}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
          {fields.map(f => (
            <tr key={f.name}>
              <td className="px-4 py-2.5 align-top">
                <div className="flex items-center gap-1.5">
                  <code className="text-[11px] font-mono text-slate-800 dark:text-slate-200">{f.name}</code>
                  {f.required && <span className="text-[9px] font-bold text-red-500 uppercase">req</span>}
                </div>
              </td>
              <td className="px-4 py-2.5 align-top">
                <code className="text-[11px] font-mono text-blue-600 dark:text-blue-400">{f.type}</code>
              </td>
              <td className="px-4 py-2.5 text-xs text-slate-500 dark:text-slate-400 leading-relaxed align-top">{f.description}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
