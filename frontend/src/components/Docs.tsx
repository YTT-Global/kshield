import React, { useState } from 'react';
import {
  BookOpen, Terminal, ShieldCheck, AlertTriangle, Package,
  Zap, FolderOpen, ChevronRight, Copy, Check, Code2,
} from 'lucide-react';

function CodeBlock({ code, language = 'bash' }: { code: string; language?: string }) {
  const [copied, setCopied] = useState(false);

  const copy = () => {
    navigator.clipboard.writeText(code);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="relative group">
      <pre className={`bg-slate-950 dark:bg-black border border-slate-800 rounded-lg p-4 overflow-x-auto text-[12px] font-mono leading-relaxed text-slate-300 lang-${language}`}>
        {code}
      </pre>
      <button
        onClick={copy}
        className="absolute top-2.5 right-2.5 h-7 w-7 flex items-center justify-center rounded-md
          bg-slate-800 hover:bg-slate-700 text-slate-400 hover:text-white transition-colors opacity-0 group-hover:opacity-100"
        title="Copy"
      >
        {copied ? <Check size={12} /> : <Copy size={12} />}
      </button>
    </div>
  );
}

function SectionHeader({ icon: Icon, title, subtitle }: { icon: React.ElementType; title: string; subtitle?: string }) {
  return (
    <div className="flex items-center gap-4 mb-5">
      <div className="h-9 w-9 rounded-lg bg-red-600/10 dark:bg-red-600/20 flex items-center justify-center flex-shrink-0">
        <Icon size={18} className="text-red-600 dark:text-red-500" />
      </div>
      <div>
        <h3 className="text-base font-bold text-slate-900 dark:text-white">{title}</h3>
        {subtitle && <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">{subtitle}</p>}
      </div>
    </div>
  );
}

function Badge({ label, color }: { label: string; color: string }) {
  return (
    <span className={`text-[10px] font-bold font-mono px-2 py-0.5 rounded-md border uppercase ${color}`}>
      {label}
    </span>
  );
}

const SEVERITY_COLORS: Record<string, string> = {
  CRITICAL: 'bg-red-100 text-red-700 border-red-200 dark:bg-red-950 dark:text-red-400 dark:border-red-900',
  HIGH:     'bg-orange-100 text-orange-700 border-orange-200 dark:bg-orange-950 dark:text-orange-400 dark:border-orange-900',
  MEDIUM:   'bg-amber-100 text-amber-700 border-amber-200 dark:bg-amber-950 dark:text-amber-400 dark:border-amber-900',
};

const CLI_COMMANDS = [
  { cmd: 'kshield init',        desc: 'Install the pre-commit hook + set up the backend (run once per repo)' },
  { cmd: 'kshield setup',       desc: 'Install the Python backend into ~/.kshield/' },
  { cmd: 'kshield start',       desc: 'Start the backend in the background' },
  { cmd: 'kshield stop',        desc: 'Stop the background backend process' },
  { cmd: 'kshield status',      desc: 'Check whether the backend and hook are running' },
  { cmd: 'kshield scan <file>', desc: 'Manually scan a single file without committing' },
  { cmd: 'kshield hook',        desc: 'Run a pre-commit scan (called automatically by the git hook)' },
];

const DETECTION_RULES = [
  {
    title: 'Hardcoded Secrets',
    severity: 'CRITICAL',
    description: 'Named token patterns matched exactly — GitHub, GitLab, AWS, Google, OpenAI, Anthropic, Stripe, Slack, Discord, npm, PyPI, HuggingFace, and more. High-entropy strings (score > 4.8, length ≥ 24) are flagged HIGH. UUIDs, hex hashes, and semver strings are allowlisted.',
    examples: ['ghp_xxxxx (GitHub PAT)', 'AKIA... (AWS key)', 'sk-ant- (Anthropic key)', 'api_key = "abc123"'],
  },
  {
    title: 'Broken Access Control',
    severity: 'HIGH',
    description: 'FastAPI route handlers with no authentication guard. Routes missing Depends() or Security() are flagged. POST / PUT / DELETE / PATCH routes are HIGH; GET routes are MEDIUM. Public paths like /health, /docs, /ping are automatically exempt.',
    examples: ['@app.post("/users") with no Depends(get_current_user)', '@app.delete("/records") with no auth guard'],
  },
  {
    title: 'AI Hallucination Placeholders',
    severity: 'MEDIUM',
    description: '60+ patterns across five categories: placeholder markers, credential stubs, hallucinated imports, AI generation artifacts, and dead code stubs. Test files (test_*.py, *_test.py, files under tests/) are automatically exempt.',
    examples: ['TODO: verify with production', 'password = "password"', 'import fake_module', 'raise NotImplementedError'],
  },
  {
    title: 'Dependency Hallucinations',
    severity: 'CRITICAL',
    description: 'Verifies every import against the official registry for Python (PyPI), JavaScript/TypeScript (npm), Go (Go module proxy), and Ruby (RubyGems). Standard library modules are always skipped. Network timeouts fail open — the commit is not blocked.',
    examples: ['import non_existent_package', 'from fake_ai_sdk import generate'],
  },
];

const INSTALL_METHODS = [
  {
    label: 'curl (recommended)',
    platform: 'macOS · Linux',
    code: 'curl -fsSL https://raw.githubusercontent.com/YTTGlobalServices/kshield/main/install.sh | bash',
  },
  {
    label: 'Homebrew',
    platform: 'macOS',
    code: 'brew install YTT-Global/tap/kshield',
  },
  {
    label: 'npm / npx',
    platform: 'JavaScript developers',
    code: 'npx kshield init',
  },
  {
    label: 'pip',
    platform: 'Python developers',
    code: `pip install kshield
kshield-backend &   # start the backend
kshield init        # install the hook`,
  },
];

const TOC_GUIDE = [
  { id: 'quickstart',  label: 'Quick Start' },
  { id: 'install',     label: 'Install' },
  { id: 'cli',         label: 'CLI Commands' },
  { id: 'detection',   label: 'What It Detects' },
  { id: 'directory',   label: 'Managed Directory' },
];

const TOC_API = [
  { id: 'api-overview',  label: 'Overview' },
  { id: 'api-health',    label: 'GET /health' },
  { id: 'api-scan',      label: 'POST /api/v1/scan' },
  { id: 'api-response',  label: 'Response Schema' },
  { id: 'api-errors',    label: 'Error Codes' },
];

const METHOD_COLORS: Record<string, string> = {
  GET:  'bg-emerald-100 text-emerald-700 border-emerald-200 dark:bg-emerald-950 dark:text-emerald-400 dark:border-emerald-900',
  POST: 'bg-blue-100 text-blue-700 border-blue-200 dark:bg-blue-950 dark:text-blue-400 dark:border-blue-900',
};

function MethodBadge({ method }: { method: string }) {
  return (
    <span className={`text-[10px] font-bold font-mono px-2 py-0.5 rounded-md border uppercase ${METHOD_COLORS[method]}`}>
      {method}
    </span>
  );
}

function FieldRow({ name, type, required, desc }: { name: string; type: string; required?: boolean; desc: string }) {
  return (
    <tr className="border-b border-slate-100 dark:border-slate-800 last:border-0">
      <td className="py-2.5 pr-3 align-top">
        <div className="flex items-center gap-1.5">
          <code className="text-[11px] font-mono text-slate-800 dark:text-slate-200">{name}</code>
          {required && <span className="text-[9px] font-bold text-red-500 uppercase">req</span>}
        </div>
      </td>
      <td className="py-2.5 pr-3 align-top">
        <code className="text-[11px] font-mono text-blue-600 dark:text-blue-400">{type}</code>
      </td>
      <td className="py-2.5 text-xs text-slate-500 dark:text-slate-400 leading-relaxed align-top">{desc}</td>
    </tr>
  );
}

export const Docs: React.FC = () => {
  const [activeTab, setActiveTab]       = useState<'guide' | 'api'>('guide');
  const [activeSection, setActiveSection] = useState('quickstart');

  const toc = activeTab === 'guide' ? TOC_GUIDE : TOC_API;

  const scrollTo = (id: string) => {
    setActiveSection(id);
    document.getElementById(id)?.scrollIntoView({ behavior: 'smooth', block: 'start' });
  };

  const switchTab = (tab: 'guide' | 'api') => {
    setActiveTab(tab);
    setActiveSection(tab === 'guide' ? 'quickstart' : 'api-overview');
  };

  return (
    <div className="space-y-6 lg:space-y-7">

      {/* Page header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div className="flex items-center gap-6">
          <div className="h-11 w-11 rounded-xl bg-red-600 flex items-center justify-center text-white shadow-lg shadow-red-600/25 flex-shrink-0">
            <BookOpen size={22} strokeWidth={1.75} />
          </div>
          <div>
            <h2 className="text-xl sm:text-2xl font-bold tracking-tight text-slate-900 dark:text-white">Documentation</h2>
            <p className="text-sm text-slate-500 dark:text-slate-400 mt-0.5">How to install, configure, and use KShield.</p>
          </div>
        </div>

        {/* Tab switcher */}
        <div className="flex items-center gap-1 p-1 rounded-lg bg-slate-100 dark:bg-slate-800 self-start sm:self-auto">
          <button
            onClick={() => switchTab('guide')}
            className={`flex items-center gap-2 px-3 py-1.5 rounded-md text-xs font-semibold transition-all ${
              activeTab === 'guide'
                ? 'bg-white dark:bg-slate-900 text-slate-900 dark:text-white shadow-sm'
                : 'text-slate-500 dark:text-slate-400 hover:text-slate-700 dark:hover:text-slate-200'
            }`}
          >
            <BookOpen size={12} />
            User Guide
          </button>
          <button
            onClick={() => switchTab('api')}
            className={`flex items-center gap-2 px-3 py-1.5 rounded-md text-xs font-semibold transition-all ${
              activeTab === 'api'
                ? 'bg-white dark:bg-slate-900 text-slate-900 dark:text-white shadow-sm'
                : 'text-slate-500 dark:text-slate-400 hover:text-slate-700 dark:hover:text-slate-200'
            }`}
          >
            <Code2 size={12} />
            API Reference
          </button>
        </div>
      </div>

      <div className="flex flex-col xl:flex-row gap-6 xl:gap-8">

        {/* Table of contents — sticky on xl */}
        <aside className="xl:w-44 flex-shrink-0">
          <div className="xl:sticky xl:top-8">
            <p className="text-[10px] font-semibold uppercase tracking-widest text-slate-400 dark:text-slate-600 mb-2 px-1">On this page</p>
            <nav className="space-y-0.5">
              {toc.map(({ id, label }) => (
                <button
                  key={id}
                  onClick={() => scrollTo(id)}
                  className={`flex items-center gap-2 w-full text-left px-2 py-1.5 rounded-md text-xs font-medium transition-colors ${
                    activeSection === id
                      ? 'text-red-600 dark:text-red-500 bg-red-50 dark:bg-red-950/30'
                      : 'text-slate-500 dark:text-slate-400 hover:text-slate-800 dark:hover:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800/50'
                  }`}
                >
                  <ChevronRight size={10} className={activeSection === id ? 'text-red-600 dark:text-red-500' : 'text-slate-400'} />
                  {label}
                </button>
              ))}
            </nav>
          </div>
        </aside>

        {/* Content */}
        <div className="flex-1 min-w-0 space-y-8">

          {activeTab === 'guide' ? (
            <>
              {/* Quick Start */}
              <section id="quickstart" className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl p-6 shadow-sm dark:shadow-none scroll-mt-4">
                <SectionHeader icon={Zap} title="Quick Start" subtitle="First value in 60 seconds" />

                <p className="text-sm text-slate-600 dark:text-slate-400 leading-relaxed mb-4">
                  After installing, run this inside any git repository:
                </p>
                <CodeBlock code="kshield init" />

                <p className="text-sm text-slate-600 dark:text-slate-400 leading-relaxed mt-4 mb-3">
                  KShield will detect your repo, install the pre-commit hook, and start the backend automatically:
                </p>
                <CodeBlock code={`✓  Git repository detected
✓  Pre-commit hook installed  (.git/hooks/pre-commit)
!  Backend not installed — running setup (one-time)...
✓  Python environment ready   (~/.kshield/venv)
✓  Backend started            (SQLite, no Docker needed)
✓  Ready. Make a commit to run your first scan.`} />

                <p className="text-sm text-slate-600 dark:text-slate-400 leading-relaxed mt-4 mb-3">
                  Now make any commit — KShield runs automatically and blocks issues before they reach your remote:
                </p>
                <CodeBlock code={`KShield · Pre-Commit Scan
Scanning 2 staged files...

  server.py      ██  2 issues
  utils/auth.py  ██  Clean

COMMIT BLOCKED · 2 issues found

  CRITICAL   server.py:12
  Hardcoded Secret · GitHub Token detected
  api_key = 'ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx'
  ↳ ELI5: Move this value to an environment variable → os.getenv('API_KEY')

  HIGH       server.py:28
  Broken Access Control · Endpoint has no authentication guard
  ↳ ELI5: Add Depends(get_current_user) to protect this route

Fix the issues above, then run  git commit  again.
To skip (not recommended): git commit --no-verify`} />

                <div className="mt-4 flex items-start gap-3 p-3.5 rounded-lg bg-amber-50 dark:bg-amber-950/30 border border-amber-200 dark:border-amber-900">
                  <AlertTriangle size={14} className="text-amber-600 dark:text-amber-400 mt-0.5 flex-shrink-0" />
                  <p className="text-xs text-amber-700 dark:text-amber-400 leading-relaxed">
                    Using <code className="bg-amber-100 dark:bg-amber-900/50 px-1 rounded font-mono">--no-verify</code> bypasses all hooks. Only use it if you are certain the flagged code is safe and you have a specific reason to skip the scan.
                  </p>
                </div>
              </section>

              {/* Install */}
              <section id="install" className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl p-6 shadow-sm dark:shadow-none scroll-mt-4">
                <SectionHeader icon={Package} title="Install" subtitle="Four paths — same binary, same experience" />

                <div className="space-y-4">
                  {INSTALL_METHODS.map(({ label, platform, code }) => (
                    <div key={label}>
                      <div className="flex items-center gap-2 mb-1.5">
                        <span className="text-xs font-semibold text-slate-700 dark:text-slate-300">{label}</span>
                        <span className="text-[10px] font-mono text-slate-400 dark:text-slate-500 bg-slate-100 dark:bg-slate-800 px-1.5 py-0.5 rounded">{platform}</span>
                      </div>
                      <CodeBlock code={code} />
                    </div>
                  ))}
                </div>
              </section>

              {/* CLI Commands */}
              <section id="cli" className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl p-6 shadow-sm dark:shadow-none scroll-mt-4">
                <SectionHeader icon={Terminal} title="CLI Commands" />

                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b border-slate-200 dark:border-slate-800">
                        <th className="text-left pb-2.5 text-[10px] font-semibold uppercase tracking-wide text-slate-400 dark:text-slate-500 w-[220px]">Command</th>
                        <th className="text-left pb-2.5 text-[10px] font-semibold uppercase tracking-wide text-slate-400 dark:text-slate-500">What it does</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                      {CLI_COMMANDS.map(({ cmd, desc }) => (
                        <tr key={cmd}>
                          <td className="py-3 pr-4 align-top">
                            <code className="text-xs font-mono bg-slate-100 dark:bg-slate-800 text-slate-800 dark:text-slate-200 px-2 py-1 rounded whitespace-nowrap">{cmd}</code>
                          </td>
                          <td className="py-3 text-xs text-slate-600 dark:text-slate-400 leading-relaxed align-top">{desc}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </section>

              {/* What it detects */}
              <section id="detection" className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl p-6 shadow-sm dark:shadow-none scroll-mt-4">
                <SectionHeader icon={ShieldCheck} title="What It Detects" subtitle="Four scan engines run on every staged file" />

                <div className="space-y-5">
                  {DETECTION_RULES.map(({ title, severity, description, examples }) => (
                    <div key={title} className="border border-slate-100 dark:border-slate-800 rounded-lg overflow-hidden">
                      <div className="flex items-center gap-3 px-4 py-3 bg-slate-50 dark:bg-slate-800/50 border-b border-slate-100 dark:border-slate-800">
                        <Badge label={severity} color={SEVERITY_COLORS[severity]} />
                        <span className="text-sm font-semibold text-slate-900 dark:text-white">{title}</span>
                      </div>
                      <div className="px-4 py-3.5 space-y-3">
                        <p className="text-xs text-slate-600 dark:text-slate-400 leading-relaxed">{description}</p>
                        <div>
                          <p className="text-[10px] font-semibold uppercase tracking-widest text-slate-400 dark:text-slate-500 mb-1.5">Examples flagged</p>
                          <ul className="space-y-1">
                            {examples.map(ex => (
                              <li key={ex} className="flex items-center gap-2">
                                <span className="h-1 w-1 rounded-full bg-red-500 flex-shrink-0" />
                                <code className="text-[11px] font-mono text-slate-600 dark:text-slate-400">{ex}</code>
                              </li>
                            ))}
                          </ul>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </section>

              {/* Managed Directory */}
              <section id="directory" className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl p-6 shadow-sm dark:shadow-none scroll-mt-4">
                <SectionHeader icon={FolderOpen} title="Managed Directory" subtitle="Created at ~/.kshield/ after first run" />

                <p className="text-sm text-slate-600 dark:text-slate-400 leading-relaxed mb-4">
                  KShield manages its own isolated directory in your home folder. No system packages are modified.
                </p>
                <CodeBlock code={`~/.kshield/
├── backend/          # Python backend source (downloaded from release)
├── venv/             # Isolated Python virtual environment
├── kshield.db        # SQLite database (scan history)
├── backend.pid       # PID of the running backend process
└── backend.log       # Backend stdout / stderr`} />

                <div className="mt-5 grid grid-cols-1 sm:grid-cols-2 gap-3">
                  {[
                    { file: 'kshield.db',  desc: 'All scan results stored locally. View history in the Dashboard.' },
                    { file: 'backend.log', desc: 'Tail this file to debug backend startup issues.' },
                    { file: 'backend.pid', desc: 'Used by kshield stop to cleanly terminate the background process.' },
                    { file: 'venv/',       desc: 'Self-contained Python env — removing forces a re-setup on next init.' },
                  ].map(({ file, desc }) => (
                    <div key={file} className="flex gap-3 p-3 rounded-lg bg-slate-50 dark:bg-slate-800/50 border border-slate-100 dark:border-slate-800">
                      <code className="text-[11px] font-mono text-slate-700 dark:text-slate-300 whitespace-nowrap flex-shrink-0 mt-0.5">{file}</code>
                      <p className="text-xs text-slate-500 dark:text-slate-400 leading-relaxed">{desc}</p>
                    </div>
                  ))}
                </div>
              </section>
            </>
          ) : (
            <>
              {/* API Overview */}
              <section id="api-overview" className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl p-6 shadow-sm dark:shadow-none scroll-mt-4">
                <SectionHeader icon={Code2} title="API Overview" subtitle="REST API served locally at port 8000" />

                <p className="text-sm text-slate-600 dark:text-slate-400 leading-relaxed mb-4">
                  The KShield backend exposes a REST API at <code className="font-mono bg-slate-100 dark:bg-slate-800 px-1.5 py-0.5 rounded text-xs">http://localhost:8000</code>. All requests are local — no data leaves your machine.
                </p>

                <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                  {[
                    { label: 'Base URL',    value: 'http://localhost:8000' },
                    { label: 'API Version', value: '/api/v1' },
                    { label: 'Format',      value: 'JSON (application/json)' },
                  ].map(({ label, value }) => (
                    <div key={label} className="p-3 rounded-lg bg-slate-50 dark:bg-slate-800/50 border border-slate-100 dark:border-slate-800">
                      <p className="text-[10px] font-semibold uppercase tracking-widest text-slate-400 dark:text-slate-500 mb-1">{label}</p>
                      <code className="text-xs font-mono text-slate-700 dark:text-slate-300">{value}</code>
                    </div>
                  ))}
                </div>
              </section>

              {/* GET /health */}
              <section id="api-health" className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl p-6 shadow-sm dark:shadow-none scroll-mt-4">
                <div className="flex items-center gap-3 mb-5">
                  <MethodBadge method="GET" />
                  <code className="text-sm font-mono font-semibold text-slate-900 dark:text-white">/health</code>
                  <span className="text-xs text-slate-400 dark:text-slate-500">— Backend liveness check</span>
                </div>

                <p className="text-sm text-slate-600 dark:text-slate-400 leading-relaxed mb-4">
                  Returns the health status of the backend process. The CLI polls this endpoint after starting the backend to confirm it is ready.
                </p>

                <p className="text-[10px] font-semibold uppercase tracking-widest text-slate-400 dark:text-slate-500 mb-2">Response — 200 OK</p>
                <CodeBlock language="json" code={`{
  "status": "healthy",
  "service": "kshield_backend"
}`} />

                <p className="text-sm text-slate-600 dark:text-slate-400 leading-relaxed mt-4">
                  A non-200 response or connection error means the backend is not running. Run <code className="font-mono bg-slate-100 dark:bg-slate-800 px-1 rounded text-xs">kshield start</code> or <code className="font-mono bg-slate-100 dark:bg-slate-800 px-1 rounded text-xs">kshield status</code> to diagnose.
                </p>
              </section>

              {/* POST /api/v1/scan */}
              <section id="api-scan" className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl p-6 shadow-sm dark:shadow-none scroll-mt-4">
                <div className="flex items-center gap-3 mb-5">
                  <MethodBadge method="POST" />
                  <code className="text-sm font-mono font-semibold text-slate-900 dark:text-white">/api/v1/scan</code>
                  <span className="text-xs text-slate-400 dark:text-slate-500">— Submit a file for analysis</span>
                </div>

                <p className="text-sm text-slate-600 dark:text-slate-400 leading-relaxed mb-5">
                  Runs all four scan engines (entropy, AST, ML classifier, dependency hallucination) on the provided file content and returns a list of findings with remediation patches.
                </p>

                <p className="text-[10px] font-semibold uppercase tracking-widest text-slate-400 dark:text-slate-500 mb-3">Request Body</p>
                <div className="overflow-x-auto mb-5">
                  <table className="w-full text-sm border border-slate-100 dark:border-slate-800 rounded-lg overflow-hidden">
                    <thead>
                      <tr className="bg-slate-50 dark:bg-slate-800/50 border-b border-slate-100 dark:border-slate-800">
                        <th className="text-left px-4 py-2.5 text-[10px] font-semibold uppercase tracking-wide text-slate-400 dark:text-slate-500 w-[120px]">Field</th>
                        <th className="text-left px-4 py-2.5 text-[10px] font-semibold uppercase tracking-wide text-slate-400 dark:text-slate-500 w-[100px]">Type</th>
                        <th className="text-left px-4 py-2.5 text-[10px] font-semibold uppercase tracking-wide text-slate-400 dark:text-slate-500">Description</th>
                      </tr>
                    </thead>
                    <tbody className="px-4">
                      <FieldRow name="filename"   type="string"       required desc="Relative path of the file being scanned (e.g. src/server.py). Used to determine language and apply exemptions." />
                      <FieldRow name="content"    type="string"       required desc="Full text content of the file. Send the raw source — do not base64 encode." />
                      <FieldRow name="commit_sha" type="string | null"         desc="Optional git commit SHA to associate with this scan record. Pass null or omit for manual scans." />
                    </tbody>
                  </table>
                </div>

                <p className="text-[10px] font-semibold uppercase tracking-widest text-slate-400 dark:text-slate-500 mb-2">Example Request</p>
                <CodeBlock language="json" code={`POST http://localhost:8000/api/v1/scan
Content-Type: application/json

{
  "filename": "src/server.py",
  "content": "import os\\napi_key = 'ghp_xxxxxxxxxxxx'\\n",
  "commit_sha": "a1b2c3d"
}`} />
              </section>

              {/* Response Schema */}
              <section id="api-response" className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl p-6 shadow-sm dark:shadow-none scroll-mt-4">
                <SectionHeader icon={Terminal} title="Response Schema" subtitle="POST /api/v1/scan — 200 OK" />

                <div className="overflow-x-auto mb-5">
                  <table className="w-full text-sm border border-slate-100 dark:border-slate-800 rounded-lg overflow-hidden">
                    <thead>
                      <tr className="bg-slate-50 dark:bg-slate-800/50 border-b border-slate-100 dark:border-slate-800">
                        <th className="text-left px-4 py-2.5 text-[10px] font-semibold uppercase tracking-wide text-slate-400 dark:text-slate-500 w-[180px]">Field</th>
                        <th className="text-left px-4 py-2.5 text-[10px] font-semibold uppercase tracking-wide text-slate-400 dark:text-slate-500 w-[100px]">Type</th>
                        <th className="text-left px-4 py-2.5 text-[10px] font-semibold uppercase tracking-wide text-slate-400 dark:text-slate-500">Description</th>
                      </tr>
                    </thead>
                    <tbody>
                      <FieldRow name="scan_id"                  type="string"    desc="UUID identifying this scan record in the local database." />
                      <FieldRow name="filename"                 type="string"    desc="The filename passed in the request." />
                      <FieldRow name="safe"                     type="boolean"   desc="True if no anomalies were found; false if the commit should be blocked." />
                      <FieldRow name="vulnerabilities_discovered" type="number"  desc="Total count of anomalies found across all engines." />
                      <FieldRow name="anomalies"                type="Anomaly[]" desc="Array of finding objects. Empty array when safe is true." />
                      <FieldRow name="anomalies[].id"           type="string"    desc="UUID for this specific finding." />
                      <FieldRow name="anomalies[].line"         type="number"    desc="Line number where the issue was detected." />
                      <FieldRow name="anomalies[].type"         type="string"    desc='Engine-specific label, e.g. "Hardcoded Secret", "Broken Access Control".' />
                      <FieldRow name="anomalies[].severity"     type="string"    desc="CRITICAL | HIGH | MEDIUM | LOW" />
                      <FieldRow name="anomalies[].description"  type="string"    desc="Human-readable description of what was found." />
                      <FieldRow name="anomalies[].remediation.explanation" type="string" desc="Plain-English (ELI5) explanation of the issue and how to fix it." />
                      <FieldRow name="anomalies[].remediation.patch_diff" type="string" desc="Unified diff patch that can be applied to resolve the issue." />
                    </tbody>
                  </table>
                </div>

                <p className="text-[10px] font-semibold uppercase tracking-widest text-slate-400 dark:text-slate-500 mb-2">Example Response</p>
                <CodeBlock language="json" code={`{
  "scan_id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
  "filename": "src/server.py",
  "safe": false,
  "vulnerabilities_discovered": 1,
  "anomalies": [
    {
      "id": "3d6f4444-8cb9-11ee-b9d1-0242ac120002",
      "line": 2,
      "type": "Hardcoded Secret",
      "severity": "CRITICAL",
      "description": "GitHub Personal Access Token detected in assignment.",
      "remediation": {
        "explanation": "Move this value to an environment variable and read it with os.getenv('GITHUB_TOKEN'). Never commit tokens to source control.",
        "patch_diff": "--- a/src/server.py\\n+++ b/src/server.py\\n@@ -1,2 +1,2 @@\\n import os\\n-api_key = 'ghp_xxxxxxxxxxxx'\\n+api_key = os.getenv('GITHUB_TOKEN')"
      }
    }
  ]
}`} />
              </section>

              {/* Error Codes */}
              <section id="api-errors" className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl p-6 shadow-sm dark:shadow-none scroll-mt-4">
                <SectionHeader icon={AlertTriangle} title="Error Codes" />

                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b border-slate-200 dark:border-slate-800">
                        <th className="text-left pb-2.5 text-[10px] font-semibold uppercase tracking-wide text-slate-400 dark:text-slate-500 w-[80px]">Status</th>
                        <th className="text-left pb-2.5 text-[10px] font-semibold uppercase tracking-wide text-slate-400 dark:text-slate-500 w-[160px]">When</th>
                        <th className="text-left pb-2.5 text-[10px] font-semibold uppercase tracking-wide text-slate-400 dark:text-slate-500">Body</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                      {[
                        { status: '200', when: 'Scan completed',        body: 'Full scan result object (safe or not).' },
                        { status: '422', when: 'Invalid request body',  body: '{ "detail": [...] } — Pydantic validation errors. Check required fields.' },
                        { status: '500', when: 'Engine fault',          body: '{ "detail": "KShield scan engine fault: <reason>" }' },
                      ].map(({ status, when, body }) => (
                        <tr key={status}>
                          <td className="py-3 pr-4 align-top">
                            <code className={`text-xs font-mono font-bold px-2 py-0.5 rounded ${
                              status === '200'
                                ? 'bg-emerald-100 dark:bg-emerald-950 text-emerald-700 dark:text-emerald-400'
                                : 'bg-red-100 dark:bg-red-950 text-red-700 dark:text-red-400'
                            }`}>{status}</code>
                          </td>
                          <td className="py-3 pr-4 text-xs text-slate-600 dark:text-slate-400 align-top">{when}</td>
                          <td className="py-3 text-xs text-slate-500 dark:text-slate-500 font-mono align-top">{body}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>

                <div className="mt-4 flex items-start gap-3 p-3.5 rounded-lg bg-slate-50 dark:bg-slate-800/50 border border-slate-200 dark:border-slate-800">
                  <Terminal size={14} className="text-slate-500 dark:text-slate-400 mt-0.5 flex-shrink-0" />
                  <p className="text-xs text-slate-600 dark:text-slate-400 leading-relaxed">
                    Network timeouts on dependency checks fail open — the scan returns 200 and the commit is not blocked. Check <code className="font-mono bg-slate-100 dark:bg-slate-700 px-1 rounded">~/.kshield/backend.log</code> for timeout details.
                  </p>
                </div>
              </section>
            </>
          )}

        </div>
      </div>
    </div>
  );
};
