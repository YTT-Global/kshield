import React, { useState, useEffect, useCallback, useRef } from 'react';
import {
  Activity, ShieldCheck, ShieldAlert, BarChart3,
  ChevronRight, X, FileCheck2, ScanEye, CheckCircle2, AlertCircle,
} from 'lucide-react';
import { WorkspacesIcon, StructuralHazardsIcon, EngineActiveIcon } from '../design-system';
import type { LucideIcon } from 'lucide-react';
import type { ScanResult, GlobalTelemetry, Anomaly } from '../types/scan';
import { api } from '../api/client';

// ── Types ────────────────────────────────────────────────────────────────────

type Severity = 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW';
type FilterChip = Severity | 'ALL';

interface Toast {
  id: number;
  message: string;
  kind: 'success' | 'error';
}

// ── Constants ────────────────────────────────────────────────────────────────

const SEVERITY_CLS: Record<string, string> = {
  CRITICAL: 'bg-red-100 text-red-700 border-red-200 dark:bg-red-950 dark:text-red-400 dark:border-red-900',
  HIGH:     'bg-orange-100 text-orange-700 border-orange-200 dark:bg-orange-950 dark:text-orange-400 dark:border-orange-900',
  MEDIUM:   'bg-amber-100 text-amber-700 border-amber-200 dark:bg-amber-950 dark:text-amber-400 dark:border-amber-900',
  LOW:      'bg-blue-100 text-blue-700 border-blue-200 dark:bg-blue-950 dark:text-blue-400 dark:border-blue-900',
};

const CHIP_ACTIVE: Record<FilterChip, string> = {
  ALL:      'bg-slate-900 text-white dark:bg-white dark:text-slate-900',
  CRITICAL: 'bg-red-600 text-white',
  HIGH:     'bg-orange-500 text-white',
  MEDIUM:   'bg-amber-500 text-white',
  LOW:      'bg-blue-500 text-white',
};

const CHIP_IDLE = 'bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-400 hover:bg-slate-200 dark:hover:bg-slate-700';

const POLL_MS = 5000;

// ── Sub-components ───────────────────────────────────────────────────────────

function DiffViewer({ diff }: { diff: string }) {
  const lineClass = (line: string): string => {
    if (line.startsWith('---') || line.startsWith('+++')) return 'text-slate-400 dark:text-slate-500 block px-1';
    if (line.startsWith('-')) return 'text-red-600 dark:text-red-400 bg-red-50 dark:bg-red-950/30 block px-1';
    if (line.startsWith('+')) return 'text-emerald-600 dark:text-emerald-400 bg-emerald-50 dark:bg-emerald-950/30 block px-1';
    if (line.startsWith('@@')) return 'text-blue-600 dark:text-blue-400 block px-1';
    return 'text-slate-500 block px-1';
  };
  if (!diff) return (
    <p className="text-xs text-slate-400 dark:text-slate-600 italic">No patch available.</p>
  );
  return (
    <pre className="p-3 bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 rounded-lg overflow-x-auto text-[11px] font-mono leading-relaxed">
      {diff.split('\n').map((line, i) => (
        <span key={i} className={lineClass(line)}>{line || ' '}</span>
      ))}
    </pre>
  );
}

function ToastStack({ toasts, onDismiss }: { toasts: Toast[]; onDismiss: (id: number) => void }) {
  return (
    <div className="fixed bottom-5 right-5 z-50 flex flex-col gap-2 pointer-events-none">
      {toasts.map(t => (
        <div
          key={t.id}
          className={`pointer-events-auto flex items-center gap-3 px-4 py-3 rounded-xl shadow-lg border text-sm font-medium
            transition-all duration-300
            ${t.kind === 'success'
              ? 'bg-white dark:bg-slate-900 border-emerald-200 dark:border-emerald-800 text-slate-800 dark:text-slate-100'
              : 'bg-white dark:bg-slate-900 border-red-200 dark:border-red-800 text-slate-800 dark:text-slate-100'
            }`}
        >
          {t.kind === 'success'
            ? <CheckCircle2 size={16} className="text-emerald-500 flex-shrink-0" />
            : <AlertCircle size={16} className="text-red-500 flex-shrink-0" />
          }
          <span>{t.message}</span>
          <button onClick={() => onDismiss(t.id)} className="ml-1 text-slate-400 hover:text-slate-600 dark:hover:text-slate-200">
            <X size={13} />
          </button>
        </div>
      ))}
    </div>
  );
}

// ── Main component ───────────────────────────────────────────────────────────

export const Dashboard: React.FC = () => {
  const [telemetry, setTelemetry] = useState<GlobalTelemetry>({
    totalScans: 0, cleanFiles: 0, openVulnerabilities: 0,
    breakdown: { critical: 0, high: 0, medium: 0, low: 0 },
  });
  const [scans, setScans]           = useState<ScanResult[]>([]);
  const [selectedScan, setSelectedScan] = useState<ScanResult | null>(null);
  const [drawerOpen, setDrawerOpen]     = useState(false);
  const [drawerAnomaly, setDrawerAnomaly] = useState<Anomaly | null>(null);
  const [filter, setFilter]             = useState<FilterChip>('ALL');
  const [toasts, setToasts]             = useState<Toast[]>([]);
  const toastCounter                    = useRef(0);

  // ── Data fetching ──────────────────────────────────────────────────────────

  const fetchData = useCallback(async () => {
    try {
      const [s, t] = await Promise.all([api.scans(), api.telemetry()]);
      setScans(s);
      setTelemetry(t);
      // keep selected scan in sync if it was updated
      if (selectedScan) {
        const refreshed = s.find(x => x.scan_id === selectedScan.scan_id);
        if (refreshed) setSelectedScan(refreshed);
      }
    } catch {
      // backend not running — fail silently, keep showing last state
    }
  }, [selectedScan]);

  useEffect(() => {
    fetchData();
    const id = setInterval(fetchData, POLL_MS);
    return () => clearInterval(id);
  }, [fetchData]);

  // ── Keyboard ───────────────────────────────────────────────────────────────

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => { if (e.key === 'Escape') setDrawerOpen(false); };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, []);

  // ── Toasts ─────────────────────────────────────────────────────────────────

  const addToast = (message: string, kind: Toast['kind']) => {
    const id = ++toastCounter.current;
    setToasts(prev => [...prev, { id, message, kind }]);
    setTimeout(() => setToasts(prev => prev.filter(t => t.id !== id)), 4000);
  };

  const dismissToast = (id: number) => setToasts(prev => prev.filter(t => t.id !== id));

  // ── Actions ────────────────────────────────────────────────────────────────

  const handleApplyPatch = async () => {
    if (!drawerAnomaly) return;
    if (!drawerAnomaly.remediation.patch_diff) {
      addToast('No patch available for this finding.', 'error');
      return;
    }
    try {
      const result = await api.applyPatch(drawerAnomaly.id) as { status: string; message?: string };
      if (result.status === 'applied') {
        addToast(`Patch applied to file successfully.`, 'success');
        setDrawerOpen(false);
      } else {
        // Fall back to clipboard
        await navigator.clipboard.writeText(drawerAnomaly.remediation.patch_diff);
        addToast(result.message ?? 'Patch copied to clipboard — run `git apply` to apply it.', 'error');
      }
    } catch {
      await navigator.clipboard.writeText(drawerAnomaly.remediation.patch_diff);
      addToast('Patch copied to clipboard — run `git apply` to apply it.', 'error');
    }
  };

  const handleSuppress = async () => {
    if (!drawerAnomaly) return;
    try {
      await api.suppress(drawerAnomaly.type);
      addToast(`"${drawerAnomaly.type}" suppressed globally — future scans will skip it.`, 'success');
      setDrawerOpen(false);
      fetchData();
    } catch {
      addToast('Could not save suppression rule.', 'error');
    }
  };

  const openDrawer = (anomaly: Anomaly) => { setDrawerAnomaly(anomaly); setDrawerOpen(true); };

  // ── Derived ────────────────────────────────────────────────────────────────

  const visibleAnomalies = selectedScan
    ? (filter === 'ALL' ? selectedScan.anomalies : selectedScan.anomalies.filter(a => a.severity === filter))
    : [];

  const metrics: { label: string; value: number; color: string; Icon: LucideIcon }[] = [
    { label: 'Total Scans',     value: telemetry.totalScans,         color: 'text-slate-900 dark:text-white',         Icon: Activity    },
    { label: 'Clean Files',     value: telemetry.cleanFiles,          color: 'text-emerald-600 dark:text-emerald-400', Icon: ShieldCheck },
    { label: 'Vulnerabilities', value: telemetry.openVulnerabilities, color: 'text-red-600 dark:text-red-500',         Icon: ShieldAlert },
  ];

  const riskEntry: { key: keyof typeof telemetry.breakdown; cls: string }[] = [
    { key: 'critical', cls: SEVERITY_CLS.CRITICAL },
    { key: 'high',     cls: SEVERITY_CLS.HIGH     },
    { key: 'medium',   cls: SEVERITY_CLS.MEDIUM   },
    { key: 'low',      cls: SEVERITY_CLS.LOW      },
  ];

  const chips: FilterChip[] = ['ALL', 'CRITICAL', 'HIGH', 'MEDIUM', 'LOW'];

  // ── Render ─────────────────────────────────────────────────────────────────

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
            <EngineActiveIcon size={14} className="text-emerald-500" />
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
              <span className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">
                <WorkspacesIcon size={14} className="text-slate-400 dark:text-slate-500" />
                Workspaces
              </span>
              <span className="text-[11px] font-mono bg-slate-100 dark:bg-slate-800 text-slate-500 dark:text-slate-400 px-2 py-0.5 rounded-full">{scans.length}</span>
            </div>
            <div className="overflow-y-auto flex-1 divide-y divide-slate-100 dark:divide-slate-800">
              {scans.length > 0 ? (
                scans.map(scan => (
                  <button
                    key={scan.scan_id}
                    onClick={() => { setSelectedScan(scan); setFilter('ALL'); }}
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
            <div className="px-4 py-3.5 border-b border-slate-200 dark:border-slate-800 flex-shrink-0 space-y-2">
              <div className="flex items-center justify-between">
                <span className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">
                  <StructuralHazardsIcon size={14} className="text-slate-400 dark:text-slate-500" />
                  Structural Hazards
                </span>
                {selectedScan && (
                  <span className="text-xs font-mono text-slate-400 dark:text-slate-600 truncate max-w-[150px] sm:max-w-[240px]">{selectedScan.filename}</span>
                )}
              </div>

              {/* Filter chips */}
              {selectedScan && (
                <div className="flex gap-1.5 flex-wrap">
                  {chips.map(chip => (
                    <button
                      key={chip}
                      onClick={() => setFilter(chip)}
                      className={`text-[10px] font-bold font-mono px-2.5 py-1 rounded-full transition-colors duration-100 ${
                        filter === chip ? CHIP_ACTIVE[chip] : CHIP_IDLE
                      }`}
                    >
                      {chip === 'ALL'
                        ? `ALL · ${selectedScan.anomalies.length}`
                        : `${chip} · ${selectedScan.anomalies.filter(a => a.severity === chip).length}`}
                    </button>
                  ))}
                </div>
              )}
            </div>

            {selectedScan && visibleAnomalies.length > 0 ? (
              <div className="overflow-y-auto flex-1 divide-y divide-slate-100 dark:divide-slate-800">
                {visibleAnomalies.map(anomaly => (
                  <button
                    key={anomaly.id}
                    onClick={() => openDrawer(anomaly)}
                    className="w-full px-4 sm:px-5 py-4 text-left hover:bg-slate-50 dark:hover:bg-slate-800/40 transition-colors duration-100 group"
                  >
                    <div className="flex items-center gap-3 sm:gap-4">
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 sm:gap-2.5 mb-1.5 flex-wrap">
                          <span className={`text-[10px] font-bold font-mono px-2 py-0.5 rounded-md border uppercase ${SEVERITY_CLS[anomaly.severity]}`}>
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
                <h3 className="text-sm font-semibold text-slate-900 dark:text-white mb-1">
                  {selectedScan && filter !== 'ALL' ? `No ${filter} findings` : 'No Anomalies Detected'}
                </h3>
                <p className="text-xs text-slate-400 dark:text-slate-500 max-w-xs leading-relaxed">
                  {selectedScan && filter !== 'ALL'
                    ? `This scan has no ${filter} severity findings.`
                    : 'This workspace scan returned clean — no structural hazards or credential leaks intercepted.'}
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

      {/* Slide-over drawer */}
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
                  <span className={`text-[10px] font-bold font-mono px-2 py-0.5 rounded-md border uppercase ${SEVERITY_CLS[drawerAnomaly.severity]}`}>
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
                  <p className="text-sm text-slate-700 dark:text-slate-300 leading-relaxed">
                    {drawerAnomaly.remediation.explanation || 'No explanation available.'}
                  </p>
                </div>
              </div>

              <div>
                <p className="text-[10px] font-bold uppercase tracking-widest text-slate-400 dark:text-slate-500 mb-2">Unified Diff Patch</p>
                <DiffViewer diff={drawerAnomaly.remediation.patch_diff} />
              </div>
            </div>

            <div className="px-5 sm:px-6 py-4 border-t border-slate-200 dark:border-slate-800 flex gap-3 flex-shrink-0">
              <button
                onClick={handleSuppress}
                className="flex-1 py-2.5 rounded-lg text-sm font-semibold transition-colors
                  bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700
                  text-slate-700 dark:text-slate-300 border border-slate-200 dark:border-slate-700"
              >
                Suppress Rule
              </button>
              <button
                onClick={handleApplyPatch}
                className="flex-1 py-2.5 rounded-lg text-sm font-semibold transition-all
                  bg-red-600 hover:bg-red-700 text-white
                  shadow-sm shadow-red-600/20 hover:shadow-md hover:shadow-red-600/30"
              >
                Apply Patch
              </button>
            </div>
          </>
        )}
      </div>

      {/* Toast stack */}
      <ToastStack toasts={toasts} onDismiss={dismissToast} />
    </>
  );
};
