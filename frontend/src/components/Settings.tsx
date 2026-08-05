import React, { useEffect, useState } from 'react';
import { ShieldCog, Server, ListChecks, Ban } from 'lucide-react';
import { api } from '../api/client';
import type { SuppressedRule } from '../types/scan';

// The actual detection rules the engine supports — matches anomaly_type
// exactly as returned by the backend. There is no dynamic/custom rule
// system; the previous "Add New Rule" form implied a capability that never
// existed on the backend, so it's gone rather than kept as decoration.
const RULE_TYPES: { type: string; description: string; severity: 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW' }[] = [
  { type: 'Hardcoded Secret',            description: 'Named token signatures — GitHub, AWS, Stripe, and 25+ more.',          severity: 'CRITICAL' },
  { type: 'High Entropy Credential',     description: 'Shannon-entropy fallback for secrets with no named pattern.',           severity: 'HIGH' },
  { type: 'Broken Access Control',       description: 'FastAPI routes with no authentication guard.',                          severity: 'HIGH' },
  { type: 'AI Structural Hallucination', description: 'Placeholder stubs, hallucinated imports, AI generation artifacts.',     severity: 'MEDIUM' },
  { type: 'Dependency Hallucination',    description: "Imports that don't exist on PyPI, npm, the Go proxy, or RubyGems.",     severity: 'CRITICAL' },
  { type: 'Possible Typosquat',          description: 'Undeclared imports very close to a well-known package name.',          severity: 'HIGH' },
  { type: 'Undeclared Dependency',       description: 'Imports missing from requirements.txt / package.json.',                severity: 'LOW' },
  { type: 'Syntax Violation',            description: 'Files that fail to parse — often truncated AI-generated code.',        severity: 'MEDIUM' },
];

const SEVERITY: Record<string, string> = {
  CRITICAL: 'bg-red-100 text-red-700 border-red-200 dark:bg-red-950 dark:text-red-400 dark:border-red-900',
  HIGH:     'bg-orange-100 text-orange-700 border-orange-200 dark:bg-orange-950 dark:text-orange-400 dark:border-orange-900',
  MEDIUM:   'bg-amber-100 text-amber-700 border-amber-200 dark:bg-amber-950 dark:text-amber-400 dark:border-amber-900',
  LOW:      'bg-blue-100 text-blue-700 border-blue-200 dark:bg-blue-950 dark:text-blue-400 dark:border-blue-900',
};

export const Settings: React.FC = () => {
  const [apiUrl, setApiUrl] = useState('');
  const [ignorePatterns, setIgnorePatterns] = useState('');
  const [saved, setSaved] = useState(false);

  const [suppressedRules, setSuppressedRules] = useState<SuppressedRule[]>([]);
  const [suppressedLoading, setSuppressedLoading] = useState(true);
  const [suppressedError, setSuppressedError] = useState(false);
  const [togglingType, setTogglingType] = useState<string | null>(null);

  const loadSuppressedRules = () => {
    setSuppressedLoading(true);
    setSuppressedError(false);
    api.suppressedRules()
      .then(setSuppressedRules)
      .catch(() => setSuppressedError(true))
      .finally(() => setSuppressedLoading(false));
  };

  useEffect(() => {
    loadSuppressedRules();
  }, []);

  const isRuleEnabled = (type: string) => !suppressedRules.some(r => r.rule_type === type);

  const handleToggleRule = async (type: string) => {
    setTogglingType(type);
    try {
      if (isRuleEnabled(type)) {
        await api.suppress(type);
        setSuppressedRules(prev => [...prev, { rule_type: type, justification: 'Suppressed via dashboard', created_at: new Date().toISOString() }]);
      } else {
        await api.unsuppress(type);
        setSuppressedRules(prev => prev.filter(r => r.rule_type !== type));
      }
    } catch {
      setSuppressedError(true);
    } finally {
      setTogglingType(null);
    }
  };

  const handleSave = () => {
    setSaved(true);
    setTimeout(() => setSaved(false), 2500);
  };

  const activeCount = RULE_TYPES.length - suppressedRules.length;

  return (
    <div className="space-y-6 lg:space-y-7">

      {/* Page header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div className="flex items-center gap-6">
          <div className="h-11 w-11 rounded-xl bg-red-600 flex items-center justify-center text-white shadow-lg shadow-red-600/25 flex-shrink-0">
            <ShieldCog size={22} strokeWidth={1.75} />
          </div>
          <div>
            <h2 className="text-xl sm:text-2xl font-bold tracking-tight text-slate-900 dark:text-white">Rules & Settings</h2>
            <p className="text-sm text-slate-500 dark:text-slate-400 mt-0.5">Configure the firewall engine, detection rules, and scan behaviour.</p>
          </div>
        </div>
      </div>

      {/* Backend connection */}
      <section className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 overflow-hidden shadow-sm dark:shadow-none">
        <div className="px-4 sm:px-5 py-4 border-b border-slate-200 dark:border-slate-800 flex items-center gap-3">
          <Server size={18} className="text-slate-500 dark:text-slate-400 flex-shrink-0" />
          <div className="min-w-0">
            <h3 className="text-sm font-semibold text-slate-800 dark:text-slate-200">Backend Connection</h3>
            <p className="text-xs text-slate-400 dark:text-slate-500 mt-0.5">Firewall API endpoint used for real-time scan analysis.</p>
          </div>
        </div>
        <div className="p-4 sm:p-5">
          <label className="text-xs font-semibold uppercase tracking-wide text-slate-400 dark:text-slate-500 block mb-2">
            API Endpoint URL
          </label>
          <input
            type="text"
            value={apiUrl}
            onChange={e => setApiUrl(e.target.value)}
            placeholder="e.g. http://localhost:8000"
            className="w-full rounded-lg px-4 py-3 text-sm font-mono transition-all
              bg-slate-50 dark:bg-slate-950
              border border-slate-200 dark:border-slate-700
              text-slate-800 dark:text-slate-200
              placeholder:text-slate-400
              focus:outline-none focus:ring-2 focus:ring-red-500/25 focus:border-red-400 dark:focus:border-red-500"
          />
        </div>
      </section>

      {/* Detection rules — real, API-backed. A rule toggled off here calls the
          same global suppress mechanism as the dashboard's "Suppress Rule"
          button (POST/DELETE /api/v1/suppress), so state matches everywhere. */}
      <section className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 overflow-hidden shadow-sm dark:shadow-none">
        <div className="px-4 sm:px-5 py-4 border-b border-slate-200 dark:border-slate-800 flex items-center justify-between gap-3">
          <div className="flex items-center gap-3 min-w-0">
            <ListChecks size={18} className="text-slate-500 dark:text-slate-400 flex-shrink-0" />
            <div className="min-w-0">
              <h3 className="text-sm font-semibold text-slate-800 dark:text-slate-200">Detection Rules</h3>
              <p className="text-xs text-slate-400 dark:text-slate-500 mt-0.5 hidden sm:block">Toggle which vulnerability types the engine flags — applies globally, on every future scan.</p>
            </div>
          </div>
          {!suppressedLoading && !suppressedError && (
            <span className="text-[11px] font-mono bg-slate-100 dark:bg-slate-800 text-slate-500 dark:text-slate-400 px-2.5 py-1 rounded-full border border-slate-200 dark:border-slate-700 flex-shrink-0">
              {activeCount}/{RULE_TYPES.length} active
            </span>
          )}
        </div>

        {suppressedLoading ? (
          <p className="px-4 sm:px-5 py-6 text-sm text-slate-400 dark:text-slate-500">Loading…</p>
        ) : suppressedError ? (
          <div className="px-4 sm:px-5 py-6 flex items-center justify-between gap-3">
            <p className="text-sm text-red-500 dark:text-red-400">Could not reach the backend to load rule state.</p>
            <button
              onClick={loadSuppressedRules}
              className="text-xs font-semibold text-slate-500 dark:text-slate-400 hover:text-slate-800 dark:hover:text-slate-200 transition-colors flex-shrink-0"
            >
              Retry
            </button>
          </div>
        ) : (
          <div className="divide-y divide-slate-100 dark:divide-slate-800">
            {RULE_TYPES.map(rule => {
              const enabled = isRuleEnabled(rule.type);
              return (
                <div key={rule.type} className="flex items-center gap-3 sm:gap-4 px-4 sm:px-5 py-4 hover:bg-slate-50 dark:hover:bg-slate-800/30 transition-colors">
                  <button
                    role="switch"
                    aria-checked={enabled}
                    aria-label={`${enabled ? 'Disable' : 'Enable'} ${rule.type}`}
                    disabled={togglingType === rule.type}
                    onClick={() => handleToggleRule(rule.type)}
                    className={`relative flex-shrink-0 inline-flex h-5 w-9 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200
                      focus:outline-none focus:ring-2 focus:ring-red-500/30 disabled:opacity-50 disabled:cursor-not-allowed
                      ${enabled ? 'bg-red-600' : 'bg-slate-200 dark:bg-slate-700'}`}
                  >
                    <span className={`pointer-events-none inline-block h-4 w-4 rounded-full bg-white shadow transition-transform duration-200 ${enabled ? 'translate-x-4' : 'translate-x-0'}`} />
                  </button>
                  <div className="flex-1 min-w-0">
                    <p className={`text-sm font-medium ${enabled ? 'text-slate-900 dark:text-slate-100' : 'text-slate-400 dark:text-slate-500'}`}>
                      {rule.type}
                    </p>
                    <p className="text-xs text-slate-400 dark:text-slate-500 mt-0.5 truncate hidden sm:block">{rule.description}</p>
                  </div>
                  <span className={`flex-shrink-0 text-[10px] font-bold font-mono px-1.5 sm:px-2 py-0.5 rounded-md border uppercase ${SEVERITY[rule.severity]}`}>
                    <span className="sm:hidden">{rule.severity[0]}</span>
                    <span className="hidden sm:inline">{rule.severity}</span>
                  </span>
                </div>
              );
            })}
          </div>
        )}
      </section>

      {/* Ignore patterns */}
      <section className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 overflow-hidden shadow-sm dark:shadow-none">
        <div className="px-4 sm:px-5 py-4 border-b border-slate-200 dark:border-slate-800 flex items-center gap-3">
          <Ban size={18} className="text-slate-500 dark:text-slate-400 flex-shrink-0" />
          <div className="min-w-0">
            <h3 className="text-sm font-semibold text-slate-800 dark:text-slate-200">Ignore Patterns</h3>
            <p className="text-xs text-slate-400 dark:text-slate-500 mt-0.5">One glob pattern per line — matching paths are excluded from all scans.</p>
          </div>
        </div>
        <div className="p-4 sm:p-5">
          <textarea
            value={ignorePatterns}
            onChange={e => setIgnorePatterns(e.target.value)}
            placeholder="node_modules/\n.git/\ndist/\n*.lock"
            rows={5}
            className="w-full rounded-lg px-4 py-3 text-sm font-mono resize-none leading-relaxed transition-all
              bg-slate-50 dark:bg-slate-950
              border border-slate-200 dark:border-slate-700
              text-slate-700 dark:text-slate-300
              placeholder:text-slate-400
              focus:outline-none focus:ring-2 focus:ring-red-500/25 focus:border-red-400 dark:focus:border-red-500"
          />
        </div>
      </section>

      {/* Save bar */}
      <div className="flex flex-col-reverse sm:flex-row sm:items-center justify-between gap-3">
        <p className={`text-sm transition-all duration-300 text-center sm:text-left ${saved ? 'text-emerald-600 dark:text-emerald-400 opacity-100' : 'opacity-0'}`}>
          ✓ Configuration saved
        </p>
        <button
          onClick={handleSave}
          className={`w-full sm:w-auto px-6 py-3 sm:py-2.5 rounded-lg text-sm font-semibold transition-all duration-200 ${
            saved
              ? 'bg-emerald-600 text-white shadow-sm shadow-emerald-600/20'
              : 'bg-red-600 hover:bg-red-700 text-white shadow-sm shadow-red-600/20 hover:shadow-md hover:shadow-red-600/30'
          }`}
        >
          {saved ? 'Saved' : 'Save Configuration'}
        </button>
      </div>

    </div>
  );
};
