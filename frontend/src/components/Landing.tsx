import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Terminal, GitCommit, GitBranch, Shield, Zap, Lock, Package,
  ArrowRight, CheckCircle2, Copy, Check, Sun, Moon,
} from 'lucide-react';
import { Button, SeverityBadge, Card } from '../design-system';
import { useTheme } from '../context/ThemeContext';

// ── KShield logo ─────────────────────────────────────────────────────────────

function KShieldLogo({ size = 48 }: { size?: number }) {
  return (
    <svg viewBox="0 0 48 54" fill="none" xmlns="http://www.w3.org/2000/svg"
         style={{ height: size * 1.125, width: size }}
         className="drop-shadow-[0_8px_24px_rgba(185,28,28,0.65)] flex-shrink-0">
      <defs>
        <linearGradient id="ll-body" x1="24" y1="1" x2="24" y2="53" gradientUnits="userSpaceOnUse">
          <stop offset="0%"   stopColor="#ff4d4d" />
          <stop offset="28%"  stopColor="#cc0000" />
          <stop offset="68%"  stopColor="#7a0000" />
          <stop offset="100%" stopColor="#180000" />
        </linearGradient>
        <radialGradient id="ll-gloss" cx="33%" cy="13%" r="44%">
          <stop offset="0%"   stopColor="rgba(255,255,255,0.24)" />
          <stop offset="100%" stopColor="rgba(255,255,255,0)"    />
        </radialGradient>
        <radialGradient id="ll-depth" cx="50%" cy="96%" r="62%">
          <stop offset="0%"   stopColor="rgba(0,0,0,0.65)" />
          <stop offset="100%" stopColor="rgba(0,0,0,0)"    />
        </radialGradient>
        <filter id="ll-k">
          <feDropShadow dx="0" dy="1.5" stdDeviation="2" floodColor="rgba(0,0,0,0.55)" />
        </filter>
      </defs>
      <path d="M24 2L43 9V27C43 39.5 34.5 48.5 24 52C13.5 48.5 5 39.5 5 27V9L24 2Z"
            fill="rgba(80,0,0,0.45)" transform="translate(0,3) scale(1.03,1) translate(-0.72,0)" />
      <path d="M24 2L43 9V27C43 39.5 34.5 48.5 24 52C13.5 48.5 5 39.5 5 27V9L24 2Z" fill="url(#ll-body)" />
      <path d="M24 2L43 9V27C43 39.5 34.5 48.5 24 52C13.5 48.5 5 39.5 5 27V9L24 2Z" fill="url(#ll-gloss)" />
      <path d="M24 2L43 9V27C43 39.5 34.5 48.5 24 52C13.5 48.5 5 39.5 5 27V9L24 2Z" fill="url(#ll-depth)" />
      <path d="M24 2L5 9V27C5 39.5 13.5 48.5 24 52"
            fill="none" stroke="rgba(255,180,180,0.35)" strokeWidth="1.5" strokeLinecap="round" />
      <path d="M24 2L43 9V27C43 39.5 34.5 48.5 24 52"
            fill="none" stroke="rgba(0,0,0,0.55)" strokeWidth="1.5" strokeLinecap="round" />
      <path d="M24 6.5L39.5 13V27C39.5 37.5 32.5 45.5 24 48.5C15.5 45.5 8.5 37.5 8.5 27V13L24 6.5Z"
            fill="none" stroke="rgba(255,255,255,0.09)" strokeWidth="1" />
      <line x1="15.5" y1="17" x2="15.5" y2="39" stroke="white" strokeWidth="6"  strokeLinecap="square" filter="url(#ll-k)" />
      <line x1="15.5" y1="28" x2="33"   y2="17" stroke="white" strokeWidth="5"  strokeLinecap="butt"   filter="url(#ll-k)" />
      <line x1="15.5" y1="28" x2="33"   y2="39" stroke="white" strokeWidth="5"  strokeLinecap="butt"   filter="url(#ll-k)" />
      <path d="M35 26 L39 27.5 L35 29" fill="none" stroke="rgba(255,255,255,0.32)"
            strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

// ── Terminal animation (always dark — it's a code terminal) ──────────────────

const LINES: { text: string; cls: string; delay: number }[] = [
  { text: 'KShield · Pre-Commit Scan',                           cls: 'text-cyan-400 font-bold',   delay: 0    },
  { text: 'Scanning 2 staged files...',                          cls: 'text-slate-400',             delay: 400  },
  { text: '',                                                    cls: '',                           delay: 700  },
  { text: '  server.py      ██  2 issues',                       cls: 'text-slate-300',             delay: 900  },
  { text: '  utils/auth.py  ██  Clean',                          cls: 'text-slate-300',             delay: 1200 },
  { text: '',                                                    cls: '',                           delay: 1500 },
  { text: 'COMMIT BLOCKED · 2 issues found',                     cls: 'text-red-400 font-bold',     delay: 1700 },
  { text: '',                                                    cls: '',                           delay: 1900 },
  { text: '  CRITICAL   server.py:12',                           cls: 'text-red-400',               delay: 2100 },
  { text: '  Hardcoded Secret · GitHub Token detected',          cls: 'text-slate-300',             delay: 2300 },
  { text: "  api_key = 'ghp_xxxxxxxxxxxxxxxx'",                  cls: 'text-amber-400 text-xs',     delay: 2500 }, // kshield: ignore
  { text: '',                                                    cls: '',                           delay: 2700 },
  { text: '  HIGH        server.py:28',                          cls: 'text-orange-400',            delay: 2900 },
  { text: '  Broken Access Control · No auth guard',             cls: 'text-slate-300',             delay: 3100 },
  { text: '',                                                    cls: '',                           delay: 3300 },
  { text: 'Fix the issues above, then run  git commit  again.',  cls: 'text-slate-500 text-xs',     delay: 3500 },
];

function TerminalDemo() {
  const [shown, setShown] = useState<number[]>([]);

  useEffect(() => {
    const t = LINES.map((l, i) => setTimeout(() => setShown(v => [...v, i]), l.delay));
    return () => t.forEach(clearTimeout);
  }, []);

  return (
    <div className="rounded-xl border border-slate-700/60 bg-slate-900 overflow-hidden shadow-2xl shadow-black/30">
      <div className="flex items-center gap-2 px-4 py-3 border-b border-slate-800 bg-slate-800/60">
        <span className="h-3 w-3 rounded-full bg-red-500/80" />
        <span className="h-3 w-3 rounded-full bg-yellow-500/80" />
        <span className="h-3 w-3 rounded-full bg-emerald-500/80" />
        <span className="ml-3 text-xs font-mono text-slate-500">git commit -m "add payment endpoint"</span>
      </div>
      <div className="p-5 font-mono text-sm space-y-1 min-h-[280px]">
        {LINES.map((line, i) => (
          <div key={i} className={`transition-opacity duration-300 ${shown.includes(i) ? 'opacity-100' : 'opacity-0'} ${line.cls}`}>
            {line.text || ' '}
          </div>
        ))}
        {shown.length === LINES.length && (
          <span className="inline-block w-2 h-4 bg-slate-400 animate-pulse" />
        )}
      </div>
    </div>
  );
}

// ── Data ─────────────────────────────────────────────────────────────────────

type Severity = 'CRITICAL' | 'HIGH' | 'MEDIUM';

const DETECTIONS: { Icon: React.FC<{ size: number; className: string }>; label: string; severity: Severity; description: string }[] = [
  { Icon: Lock,    label: 'Hardcoded Secrets',        severity: 'CRITICAL', description: '30+ named token patterns — GitHub, AWS, OpenAI, Stripe, Slack and more. Zero false positives on hashes or UUIDs.' },
  { Icon: Shield,  label: 'Broken Access Control',    severity: 'HIGH',     description: 'Detects FastAPI routes with no authentication guard. Severity scales by HTTP method.' },
  { Icon: Zap,     label: 'AI Hallucinations',        severity: 'MEDIUM',   description: '60+ patterns across placeholders, credential stubs, dead code, and AI generation artifacts. Test files exempt.' },
  { Icon: Package, label: 'Dependency Hallucinations',severity: 'CRITICAL', description: 'Verifies every import against PyPI, npm, Go proxy, and RubyGems before they ship.' },
];

const INSTALL_TABS = [
  { label: 'curl', cmd: 'curl -fsSL https://raw.githubusercontent.com/YTT-Global/kshield/main/install.sh | bash' },
  { label: 'brew', cmd: 'brew install YTT-Global/tap/kshield' },
  { label: 'npm',  cmd: 'npx kshield init' },
  { label: 'pip',  cmd: 'pip install kshield && kshield-backend &' },
];

const STATS = [
  { value: '30+', label: 'Secret patterns'      },
  { value: '60+', label: 'Hallucination checks' },
  { value: '4',   label: 'Package registries'   },
  { value: '0',   label: 'Data sent to cloud'   },
];

const FEATURES = [
  'Local-first — zero data leaves your machine',
  'No Docker required for first run',
  'SQLite by default, PostgreSQL for teams',
  'Auto-remediation diff patches per finding',
  'Suppression config via .kshield.yml',
  'React dashboard with live scan telemetry',
  'Tauri desktop app for native experience',
  'GitHub Actions CI integration built-in',
  'Homebrew · npm · pip · curl install paths',
];

// ── Landing ──────────────────────────────────────────────────────────────────

export const Landing: React.FC = () => {
  const navigate            = useNavigate();
  const onLaunch            = () => navigate('/kshield-dashboard');
  const [tab, setTab]       = useState(0);
  const [copied, setCopied] = useState(false);
  const { theme, toggle }   = useTheme();

  const copy = () => {
    navigator.clipboard.writeText(INSTALL_TABS[tab].cmd);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="min-h-screen bg-white dark:bg-slate-950 text-slate-900 dark:text-white transition-colors duration-200">

      {/* ── Nav ─────────────────────────────────────────────────────────── */}
      <nav className="fixed top-0 inset-x-0 z-50 border-b border-slate-200/60 dark:border-slate-800/60 bg-white/80 dark:bg-slate-950/80 backdrop-blur-md transition-colors duration-200">
        <div className="max-w-6xl mx-auto px-6 h-14 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <KShieldLogo size={26} />
            <span className="font-bold tracking-widest uppercase text-sm">KShield</span>
            <span className="text-[10px] font-mono text-slate-400 dark:text-slate-500 border border-slate-200 dark:border-slate-700 px-1.5 py-0.5 rounded">v1.0.0</span>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={toggle}
              className="h-9 w-9 flex items-center justify-center rounded-lg transition-colors
                text-slate-500 dark:text-slate-400
                hover:bg-slate-100 dark:hover:bg-slate-800
                hover:text-slate-700 dark:hover:text-slate-200"
              aria-label="Toggle theme"
            >
              {theme === 'dark' ? <Sun size={16} /> : <Moon size={16} />}
            </button>
            <a href="https://github.com/YTT-Global/kshield" target="_blank" rel="noreferrer"
               className="flex items-center gap-2 text-sm text-slate-500 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white transition-colors px-3 py-1.5">
              <GitBranch size={16} />
              <span className="hidden sm:inline">GitHub</span>
            </a>
            <button
              onClick={() => navigate('/kshield-dashboard?tab=docs')}
              className="hidden sm:flex items-center gap-1.5 text-sm text-slate-500 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white transition-colors px-3 py-1.5"
            >
              Docs
              <ArrowRight size={13} />
            </button>
            <Button variant="primary" size="sm" iconRight={ArrowRight} onClick={onLaunch}>
              Dashboard
            </Button>
          </div>
        </div>
      </nav>

      {/* ── Hero ────────────────────────────────────────────────────────── */}
      <section className="pt-32 pb-20 px-6">
        <div className="max-w-6xl mx-auto grid lg:grid-cols-2 gap-12 lg:gap-16 items-center">

          <div>
            <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full border border-red-200 dark:border-red-900/50 bg-red-50 dark:bg-red-950/30 text-red-600 dark:text-red-400 text-[10px] font-bold font-mono uppercase tracking-widest mb-6">
              <span className="h-1.5 w-1.5 rounded-full bg-red-500 animate-pulse" />
              Local-first · Zero telemetry · No data leaves your machine
            </div>

            <h1 className="text-4xl sm:text-5xl lg:text-[52px] font-black leading-[1.08] tracking-tight mb-6">
              The pre-commit<br />
              <span className="text-red-500">security firewall</span><br />
              for developers.
            </h1>

            <p className="text-lg text-slate-600 dark:text-slate-400 leading-relaxed mb-8 max-w-lg">
              Catches hardcoded secrets, broken access control, AI hallucinations,
              and supply-chain risks — entirely on your machine, before a single line
              reaches your remote.
            </p>

            <div className="flex flex-wrap gap-3">
              <Button
                variant="primary" size="lg" icon={Terminal}
                onClick={() => document.getElementById('install')?.scrollIntoView({ behavior: 'smooth' })}
              >
                Install in 60 seconds
              </Button>
              <a href="https://github.com/YTT-Global/kshield" target="_blank" rel="noreferrer">
                <Button variant="secondary" size="lg" icon={GitBranch}>
                  View on GitHub
                </Button>
              </a>
            </div>

            {/* Stats */}
            <div className="grid grid-cols-4 gap-4 mt-10 pt-10 border-t border-slate-200 dark:border-slate-800">
              {STATS.map(({ value, label }) => (
                <div key={label}>
                  <p className="text-2xl font-black font-mono text-slate-900 dark:text-white">{value}</p>
                  <p className="text-xs text-slate-500 mt-0.5 leading-tight">{label}</p>
                </div>
              ))}
            </div>
          </div>

          <TerminalDemo />
        </div>
      </section>

      {/* ── Detections ──────────────────────────────────────────────────── */}
      <section className="py-20 px-6 border-t border-slate-200/60 dark:border-slate-800/60">
        <div className="max-w-6xl mx-auto">
          <div className="text-center mb-12">
            <p className="text-[10px] font-bold font-mono text-red-500 uppercase tracking-widest mb-3">Detection Engine</p>
            <h2 className="text-3xl sm:text-4xl font-black">What it catches</h2>
            <p className="text-slate-600 dark:text-slate-400 mt-3 max-w-xl mx-auto text-sm leading-relaxed">
              Four independent engines run in parallel on every commit. No cloud. No API keys. No waiting.
            </p>
          </div>

          <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4">
            {DETECTIONS.map(({ Icon, label, severity, description }) => (
              <Card key={label} className="hover:border-slate-300 dark:hover:border-slate-700 transition-colors">
                <div className="flex items-center justify-between mb-4">
                  <div className="h-9 w-9 rounded-lg bg-red-50 dark:bg-red-600/10 border border-red-200 dark:border-red-900/30 flex items-center justify-center">
                    <Icon size={18} className="text-red-500" />
                  </div>
                  <SeverityBadge severity={severity} />
                </div>
                <h3 className="font-bold text-slate-900 dark:text-white text-sm mb-2">{label}</h3>
                <p className="text-xs text-slate-500 dark:text-slate-400 leading-relaxed">{description}</p>
              </Card>
            ))}
          </div>
        </div>
      </section>

      {/* ── How it works ────────────────────────────────────────────────── */}
      <section className="py-20 px-6 border-t border-slate-200/60 dark:border-slate-800/60">
        <div className="max-w-6xl mx-auto">
          <div className="text-center mb-12">
            <p className="text-[10px] font-bold font-mono text-red-500 uppercase tracking-widest mb-3">Zero friction</p>
            <h2 className="text-3xl sm:text-4xl font-black">First value in 60 seconds</h2>
          </div>
          <div className="grid sm:grid-cols-3 gap-8 max-w-3xl mx-auto">
            {[
              { step: '01', Icon: Terminal,  title: 'Install',        body: 'One command installs the binary, Python backend, and SQLite DB into ~/.kshield/' },
              { step: '02', Icon: GitCommit, title: 'Init your repo', body: 'Run kshield init inside any git repo. The pre-commit hook is installed automatically.' },
              { step: '03', Icon: Shield,    title: 'Commit normally', body: 'KShield runs on every commit. Clean code goes through. Issues are blocked with a clear report.' },
            ].map(({ step, Icon, title, body }) => (
              <div key={step}>
                <p className="text-[10px] font-black font-mono text-slate-300 dark:text-slate-700 mb-3">{step}</p>
                <div className="h-10 w-10 rounded-xl bg-red-50 dark:bg-red-600/10 border border-red-200 dark:border-red-900/30 flex items-center justify-center mb-4">
                  <Icon size={18} className="text-red-500" />
                </div>
                <h3 className="font-bold text-slate-900 dark:text-white mb-2">{title}</h3>
                <p className="text-sm text-slate-500 leading-relaxed">{body}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── Install ─────────────────────────────────────────────────────── */}
      <section id="install" className="py-20 px-6 border-t border-slate-200/60 dark:border-slate-800/60">
        <div className="max-w-2xl mx-auto text-center">
          <p className="text-[10px] font-bold font-mono text-red-500 uppercase tracking-widest mb-3">Install</p>
          <h2 className="text-3xl sm:text-4xl font-black mb-4">Pick your path</h2>
          <p className="text-slate-600 dark:text-slate-400 text-sm mb-8">All four point to the same binary and the same experience.</p>

          {/* Install block always dark — it's a code terminal */}
          <div className="rounded-xl border border-slate-700 bg-slate-900 overflow-hidden text-left">
            <div className="flex border-b border-slate-800">
              {INSTALL_TABS.map((t, i) => (
                <button
                  key={t.label}
                  onClick={() => setTab(i)}
                  className={`px-5 py-3 text-sm font-mono font-semibold transition-colors ${
                    tab === i
                      ? 'text-white border-b-2 border-red-500 bg-slate-800/50'
                      : 'text-slate-500 hover:text-slate-300'
                  }`}
                >
                  {t.label}
                </button>
              ))}
            </div>
            <div className="flex items-center justify-between px-5 py-4 gap-4">
              <code className="text-sm text-emerald-400 font-mono flex-1 break-all leading-relaxed">
                {INSTALL_TABS[tab].cmd}
              </code>
              <button
                onClick={copy}
                className={`flex-shrink-0 flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition-all border ${
                  copied
                    ? 'bg-emerald-950 text-emerald-400 border-emerald-800'
                    : 'bg-slate-800 hover:bg-slate-700 text-slate-400 border-slate-700'
                }`}
              >
                {copied ? <Check size={12} /> : <Copy size={12} />}
                {copied ? 'Copied' : 'Copy'}
              </button>
            </div>
          </div>

          <p className="text-slate-400 dark:text-slate-600 text-xs mt-4 font-mono">
            Then inside any git repo: <span className="text-slate-600 dark:text-slate-400">kshield init</span>
          </p>
        </div>
      </section>

      {/* ── Features strip ──────────────────────────────────────────────── */}
      <section className="py-16 px-6 border-t border-slate-200/60 dark:border-slate-800/60 bg-slate-50/80 dark:bg-slate-900/20">
        <div className="max-w-4xl mx-auto grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {FEATURES.map(f => (
            <div key={f} className="flex items-start gap-3">
              <CheckCircle2 size={15} className="text-emerald-500 flex-shrink-0 mt-0.5" />
              <span className="text-sm text-slate-600 dark:text-slate-400">{f}</span>
            </div>
          ))}
        </div>
      </section>

      {/* ── CTA ─────────────────────────────────────────────────────────── */}
      <section className="py-24 px-6 border-t border-slate-200/60 dark:border-slate-800/60 text-center">
        <div className="max-w-xl mx-auto flex flex-col items-center">
          <KShieldLogo size={56} />
          <h2 className="text-3xl sm:text-4xl font-black mt-6 mb-4">Stop shipping secrets.</h2>
          <p className="text-slate-600 dark:text-slate-400 text-sm mb-8">Free. Open source. Runs entirely on your machine.</p>
          <div className="flex flex-wrap justify-center gap-3">
            <Button
              variant="primary" size="lg" iconRight={ArrowRight}
              onClick={() => document.getElementById('install')?.scrollIntoView({ behavior: 'smooth' })}
            >
              Install KShield
            </Button>
            <Button variant="secondary" size="lg" icon={Terminal} onClick={onLaunch}>
              Open Dashboard
            </Button>
          </div>
        </div>
      </section>

      {/* ── Footer ──────────────────────────────────────────────────────── */}
      <footer className="border-t border-slate-200/60 dark:border-slate-800/60 py-8 px-6">
        <div className="max-w-6xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <KShieldLogo size={20} />
            <span className="text-sm text-slate-500 font-mono">KShield · MIT License</span>
          </div>
          <div className="flex items-center gap-6 text-sm text-slate-400 dark:text-slate-600">
            <a href="https://github.com/YTT-Global/kshield" target="_blank" rel="noreferrer" className="hover:text-slate-700 dark:hover:text-slate-400 transition-colors">GitHub</a>
            <a href="https://github.com/YTT-Global/kshield/blob/master/CHANGELOG.md" target="_blank" rel="noreferrer" className="hover:text-slate-700 dark:hover:text-slate-400 transition-colors">Changelog</a>
            <a href="https://ytt.global" target="_blank" rel="noreferrer" className="hover:text-slate-700 dark:hover:text-slate-400 transition-colors">YTT Global</a>
          </div>
        </div>
      </footer>

    </div>
  );
};
