import React, { useState, useEffect } from 'react';
import {
  Activity, ShieldCheck, ShieldAlert, BarChart3,
  ChevronRight, X, FileCheck2, ScanEye,
} from 'lucide-react';
import type { LucideIcon } from 'lucide-react';
import type { ScanResult, GlobalTelemetry, Anomaly } from '../types/scan';

const SEVERITY: Record<string, string> = {
  CRITICAL: 'bg-red-100 text-red-700 border-red-200 dark:bg-red-950 dark:text-red-400 dark:border-red-900',
  HIGH:     'bg-orange-100 text-orange-700 border-orange-200 dark:bg-orange-950 dark:text-orange-400 dark:border-orange-900',
  MEDIUM:   'bg-amber-100 text-amber-700 border-amber-200 dark:bg-amber-950 dark:text-amber-400 dark:border-amber-900',
  LOW:      'bg-blue-100 text-blue-700 border-blue-200 dark:bg-blue-950 dark:text-blue-400 dark:border-blue-900',
};

function DiffViewer({ diff }: { diff: string }) {
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

export const Dashboard: React.FC = () => {
  const [telemetry] = useState<GlobalTelemetry>({
    totalScans: 0,
    cleanFiles: 0,
    openVulnerabilities: 0,
    breakdown: { critical: 0, high: 0, medium: 0, low: 0 },
  });

  const [scans] = useState<ScanResult[]>([]);

  const [selectedScan, setSelectedScan] = useState<ScanResult | null>(null);
  const [drawerOpen, setDrawerOpen]       = useState(false);
  const [drawerAnomaly, setDrawerAnomaly] = useState<Anomaly | null>(null);

  const openDrawer = (anomaly: Anomaly) => { setDrawerAnomaly(anomaly); setDrawerOpen(true); };

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => { if (e.key === 'Escape') setDrawerOpen(false); };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, []);

  const metrics: { label: string; value: number; color: string; Icon: LucideIcon }[] = [
    { label: 'Total Scans',      value: telemetry.totalScans,         color: 'text-slate-900 dark:text-white',         Icon: Activity       },
    { label: 'Clean Files',      value: telemetry.cleanFiles,          color: 'text-emerald-600 dark:text-emerald-400', Icon: ShieldCheck   },
    { label: 'Vulnerabilities',  value: telemetry.openVulnerabilities, color: 'text-red-600 dark:text-red-500',         Icon: ShieldAlert   },
  ];

  const riskEntry: { key: keyof typeof telemetry.breakdown; cls: string }[] = [
    { key: 'critical', cls: 'bg-red-100 text-red-700 border-red-200 dark:bg-red-950 dark:text-red-400 dark:border-red-900' },
    { key: 'high',     cls: 'bg-orange-100 text-orange-700 border-orange-200 dark:bg-orange-950 dark:text-orange-400 dark:border-orange-900' },
    { key: 'medium',   cls: 'bg-amber-100 text-amber-700 border-amber-200 dark:bg-amber-950 dark:text-amber-400 dark:border-amber-900' },
    { key: 'low',      cls: 'bg-blue-100 text-blue-700 border-blue-200 dark:bg-blue-950 dark:text-blue-400 dark:border-blue-900' },
  ];

  return (
    <>
      <div className="space-y-6 lg:space-y-7">

        {/* Page header */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div className="flex items-center gap-6">
            <div className="h-11 w-11 rounded-xl bg-red-600 flex items-center justify-center text-white shadow-lg shadow-red-600/25 flex-shrink-0">
              <ScanEye size={22} strokeWidth={1.75} />
            </div>
            <div>
              <h2 className="text-xl sm:text-2xl font-bold tracking-tight text-slate-900 dark:text-white">Security Dashboard</h2>
              <p className="text-sm text-slate-500 dark:text-slate-400 mt-0.5">Live telemetry for staged workspace mutations.</p>
            </div>
          </div>
          <div className="flex items-center gap-2 text-xs font-mono px-3 py-1.5 rounded-full self-start sm:self-auto
            bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800
            text-slate-500 dark:text-slate-400 shadow-sm dark:shadow-none whitespace-nowrap">
            <span className="h-1.5 w-1.5 rounded-full bg-emerald-500 animate-pulse" />
            Engine active
          </div>
        </div>

        {/* Metric cards */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 lg:gap-4">
          {metrics.map(({ label, value, color, Icon }) => (
            <div key={label} className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 p-4 lg:p-5 shadow-sm dark:shadow-none">
              <div className="flex items-center justify-between mb-2 lg:mb-3">
                <span className="text-[10px] lg:text-xs font-semibold uppercase tracking-wide text-slate-400 dark:text-slate-500 leading-tight">{label}</span>
                <Icon size={16} className={`${color} flex-shrink-0`} />
              </div>
              <p className={`text-2xl lg:text-3xl font-bold font-mono ${color}`}>{value}</p>
            </div>
          ))}

          {/* Risk breakdown */}
          <div className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 p-4 lg:p-5 shadow-sm dark:shadow-none">
            <div className="flex items-center justify-between mb-2 lg:mb-3">
              <span className="text-[10px] lg:text-xs font-semibold uppercase tracking-wide text-slate-400 dark:text-slate-500">Risk Index</span>
              <BarChart3 size={16} className="text-slate-600 dark:text-slate-400 flex-shrink-0" />
            </div>
            <div className="flex gap-1 flex-wrap">
              {riskEntry.map(({ key, cls }) => (
                <span key={key} className={`text-[10px] lg:text-xs font-bold font-mono px-1.5 py-0.5 rounded border ${cls}`}>
                  {telemetry.breakdown[key]}{key[0].toUpperCase()}
                </span>
              ))}
            </div>
          </div>
        </div>

        {/* Main panels */}
        <div className="grid grid-cols-1 xl:grid-cols-3 gap-4 lg:gap-5">

          {/* Scan list */}
          <div className="xl:col-span-1 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl overflow-hidden flex flex-col h-[300px] sm:h-[380px] xl:h-[560px] shadow-sm dark:shadow-none">
            <div className="px-4 py-3.5 border-b border-slate-200 dark:border-slate-800 flex items-center justify-between flex-shrink-0">
              <span className="text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">Workspaces</span>
              <span className="text-[11px] font-mono bg-slate-100 dark:bg-slate-800 text-slate-500 dark:text-slate-400 px-2 py-0.5 rounded-full">{scans.length}</span>
            </div>
            <div className="overflow-y-auto flex-1 divide-y divide-slate-100 dark:divide-slate-800">
              {scans.length > 0 ? (
                scans.map(scan => (
                  <button
                    key={scan.scan_id}
                    onClick={() => setSelectedScan(scan)}
                    className={`w-full px-4 py-3.5 text-left flex items-center justify-between gap-3 transition-colors duration-100 ${
                      selectedScan?.scan_id === scan.scan_id
                        ? 'bg-slate-50 dark:bg-slate-800/60'
                        : 'hover:bg-slate-50/80 dark:hover:bg-slate-800/30'
                    }`}
                  >
                    <div className="flex items-center gap-2.5 min-w-0">
                      <span className={`h-1.5 w-1.5 rounded-full flex-shrink-0 ${scan.safe ? 'bg-emerald-500' : 'bg-red-500'}`} />
                      <span className="text-sm font-mono text-slate-700 dark:text-slate-200 truncate">{scan.filename}</span>
                    </div>
                    <span className={`text-[10px] font-semibold font-mono px-2 py-0.5 rounded-full flex-shrink-0 ${
                      scan.safe
                        ? 'bg-emerald-100 dark:bg-emerald-950 text-emerald-700 dark:text-emerald-400'
                        : 'bg-red-100 dark:bg-red-950 text-red-700 dark:text-red-400'
                    }`}>
                      {scan.safe ? 'Safe' : `${scan.vulnerabilities_discovered} flaws`}
                    </span>
                  </button>
                ))
              ) : (
                <div className="flex flex-col items-center justify-center h-full p-6 text-center">
                  <div className="w-10 h-10 rounded-full bg-slate-100 dark:bg-slate-800 flex items-center justify-center mb-3">
                    <ScanEye size={20} className="text-slate-400 dark:text-slate-500" />
                  </div>
                  <p className="text-xs font-medium text-slate-500 dark:text-slate-400">No scans yet</p>
                  <p className="text-[10px] text-slate-400 dark:text-slate-600 mt-1 max-w-[120px]">
                    Run <code className="bg-slate-100 dark:bg-slate-800 px-1 rounded">kshield scan</code> to start.
                  </p>
                </div>
              )}
            </div>
          </div>

          {/* Anomaly list */}
          <div className="xl:col-span-2 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl overflow-hidden flex flex-col h-[360px] sm:h-[420px] xl:h-[560px] shadow-sm dark:shadow-none">
            <div className="px-4 py-3.5 border-b border-slate-200 dark:border-slate-800 flex items-center justify-between flex-shrink-0">
              <span className="text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">Structural Hazards</span>
              {selectedScan && (
                <span className="text-xs font-mono text-slate-400 dark:text-slate-600 truncate max-w-[150px] sm:max-w-[240px]">{selectedScan.filename}</span>
              )}
            </div>

            {selectedScan && selectedScan.anomalies.length > 0 ? (
              <div className="overflow-y-auto flex-1 divide-y divide-slate-100 dark:divide-slate-800">
                {selectedScan.anomalies.map(anomaly => (
                  <button
                    key={anomaly.id}
                    onClick={() => openDrawer(anomaly)}
                    className="w-full px-4 sm:px-5 py-4 text-left hover:bg-slate-50 dark:hover:bg-slate-800/40 transition-colors duration-100 group"
                  >
                    <div className="flex items-center gap-3 sm:gap-4">
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 sm:gap-2.5 mb-1.5 flex-wrap">
                          <span className={`text-[10px] font-bold font-mono px-2 py-0.5 rounded-md border uppercase ${SEVERITY[anomaly.severity]}`}>
                            {anomaly.severity}
                          </span>
                          <span className="text-xs text-slate-400 dark:text-slate-500 font-mono">Line {anomaly.line}</span>
                        </div>
                        <h4 className="text-sm font-semibold text-slate-900 dark:text-white mb-1">{anomaly.type}</h4>
                        <p className="text-xs text-slate-500 dark:text-slate-400 leading-relaxed line-clamp-2">{anomaly.description}</p>
                      </div>
                      <ChevronRight
                        size={16}
                        className="flex-shrink-0 text-slate-300 dark:text-slate-700 group-hover:text-slate-500 dark:group-hover:text-slate-400 group-hover:translate-x-0.5 transition-all duration-150"
                      />
                    </div>
                  </button>
                ))}
              </div>
            ) : (
              <div className="flex-1 flex flex-col items-center justify-center p-8 text-center">
                <div className="w-12 h-12 rounded-full bg-emerald-100 dark:bg-emerald-950 flex items-center justify-center mb-3">
                  <FileCheck2 size={22} className="text-emerald-600 dark:text-emerald-400" />
                </div>
                <h3 className="text-sm font-semibold text-slate-900 dark:text-white mb-1">No Anomalies Detected</h3>
                <p className="text-xs text-slate-400 dark:text-slate-500 max-w-xs leading-relaxed">
                  This workspace scan returned clean — no structural hazards or credential leaks intercepted.
                </p>
              </div>
            )}
          </div>

        </div>
      </div>

      {/* Backdrop */}
      <div
        onClick={() => setDrawerOpen(false)}
        className={`fixed inset-0 bg-black/40 dark:bg-black/60 backdrop-blur-sm z-30 transition-opacity duration-300 ${
          drawerOpen ? 'opacity-100 pointer-events-auto' : 'opacity-0 pointer-events-none'
        }`}
      />

      {/* Slide-over drawer — full width on mobile, fixed width on sm+ */}
      <div className={`fixed top-0 right-0 h-full w-full sm:w-[500px] z-40 flex flex-col
        bg-white dark:bg-slate-900
        border-l border-slate-200 dark:border-slate-700
        shadow-2xl shadow-slate-300/40 dark:shadow-black/60
        transition-transform duration-300 ease-in-out
        ${drawerOpen ? 'translate-x-0' : 'translate-x-full'}`}
      >
        {drawerAnomaly && (
          <>
            <div className="flex items-start justify-between px-5 sm:px-6 py-5 border-b border-slate-200 dark:border-slate-800 flex-shrink-0">
              <div className="flex-1 pr-4 min-w-0">
                <div className="flex items-center gap-2.5 mb-2">
                  <span className={`text-[10px] font-bold font-mono px-2 py-0.5 rounded-md border uppercase ${SEVERITY[drawerAnomaly.severity]}`}>
                    {drawerAnomaly.severity}
                  </span>
                  <span className="text-xs font-mono text-slate-400 dark:text-slate-500">Line {drawerAnomaly.line}</span>
                </div>
                <h3 className="text-base font-bold text-slate-900 dark:text-white">{drawerAnomaly.type}</h3>
              </div>
              <button
                onClick={() => setDrawerOpen(false)}
                title="Close (Esc)"
                className="flex-shrink-0 h-9 w-9 flex items-center justify-center rounded-lg transition-colors
                  bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700
                  text-slate-500 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white"
              >
                <X size={15} />
              </button>
            </div>

            <div className="flex-1 overflow-y-auto px-5 sm:px-6 py-5 space-y-6">
              <div className="flex items-center gap-2 text-xs font-mono flex-wrap">
                <span className="text-slate-400 dark:text-slate-500">file</span>
                <span className="px-2 py-1 rounded-md truncate
                  bg-slate-100 dark:bg-slate-800 border border-slate-200 dark:border-slate-700
                  text-slate-700 dark:text-slate-300 max-w-full">
                  {selectedScan?.filename}
                </span>
              </div>

              <div>
                <p className="text-[10px] font-bold uppercase tracking-widest text-slate-400 dark:text-slate-500 mb-2">Description</p>
                <p className="text-sm text-slate-700 dark:text-slate-300 leading-relaxed">{drawerAnomaly.description}</p>
              </div>

              <div>
                <p className="text-[10px] font-bold uppercase tracking-widest text-slate-400 dark:text-slate-500 mb-2">Plain English</p>
                <div className="bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 rounded-lg p-4">
                  <p className="text-sm text-slate-700 dark:text-slate-300 leading-relaxed">{drawerAnomaly.remediation.explanation}</p>
                </div>
              </div>

              <div>
                <p className="text-[10px] font-bold uppercase tracking-widest text-slate-400 dark:text-slate-500 mb-2">Unified Diff Patch</p>
                <DiffViewer diff={drawerAnomaly.remediation.patch_diff} />
              </div>
            </div>

            <div className="px-5 sm:px-6 py-4 border-t border-slate-200 dark:border-slate-800 flex gap-3 flex-shrink-0">
              <button className="flex-1 py-2.5 rounded-lg text-sm font-semibold transition-colors
                bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700
                text-slate-700 dark:text-slate-300 border border-slate-200 dark:border-slate-700">
                Suppress Rule
              </button>
              <button className="flex-1 py-2.5 rounded-lg text-sm font-semibold transition-all
                bg-red-600 hover:bg-red-700 text-white
                shadow-sm shadow-red-600/20 hover:shadow-md hover:shadow-red-600/30">
                Apply Patch
              </button>
            </div>
          </>
        )}
      </div>
    </>
  );
};
