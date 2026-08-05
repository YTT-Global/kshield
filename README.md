<div align="center">
  <img src="assets/logo.svg" width="96" alt="KShield logo" />

  # KShield

  **The local-first security firewall for developers**

  Catches hardcoded secrets, broken access control, AI hallucinations, and supply-chain risks — entirely on your machine, one commit or a whole repo at a time — with verified auto-remediation, not fabricated patches.

  [![Build](https://img.shields.io/github/actions/workflow/status/YTT-Global/kshield/ci.yml?label=CI&style=flat-square)](https://github.com/YTT-Global/kshield/actions)
  [![Release](https://img.shields.io/github/v/release/YTT-Global/kshield?style=flat-square)](https://github.com/YTT-Global/kshield/releases/latest)
  [![VS Code Marketplace](https://img.shields.io/visual-studio-marketplace/v/YTTGlobal.kshield-vscode?style=flat-square&label=VS%20Code%20Marketplace)](https://marketplace.visualstudio.com/items?itemName=YTTGlobal.kshield-vscode)
  [![License](https://img.shields.io/badge/license-MIT-blue?style=flat-square)](LICENSE)
  [![Stack](https://img.shields.io/badge/stack-Rust%20·%20FastAPI%20·%20React-red?style=flat-square)](#tech-stack)
</div>

---

## The Problem This Solves

Most security tools run in the cloud, require API keys, and send your source code to third-party servers. KShield runs **entirely on your machine** — no telemetry, no data leaving your laptop. It sits between your `git commit` and your remote, scanning every staged change in real time.

---

## Install

Pick any one — they all end up at the same binary and the same experience:

**macOS / Linux (recommended):**
```bash
curl -fsSL https://raw.githubusercontent.com/YTT-Global/kshield/main/install.sh | bash
```

**Homebrew (macOS):**
```bash
brew install YTT-Global/tap/kshield
```

**npm / npx (JavaScript developers):**
```bash
npx @ytt-global/kshield init
```

**pip (Python developers):**
```bash
pip install kshield
kshield-backend &   # starts the backend
kshield init        # installs the hook
```

---

## First Value in 60 Seconds

After installing, run this inside **any git repo**:

```bash
kshield init
```

That's it. What happens:

```
✓  Git repository detected
✓  Pre-commit hook installed  (.git/hooks/pre-commit)
!  Backend not installed — running setup (one-time)…
✓  Python environment ready   (~/.kshield/venv)
✓  Backend started            (SQLite, no Docker needed)
✓  Ready. Make a commit to run your first scan.
```

Now make any commit — the firewall runs automatically:

```
KShield · Pre-Commit Scan
Scanning 2 staged files…

  server.py      ██  2 issues
  utils/auth.py  ██  Clean

COMMIT BLOCKED · 2 issues found

  CRITICAL   server.py:12
  Hardcoded Secret · GitHub Token detected
  api_key = 'ghp_<redacted-example-token>'
  ↳ ELI5: Move this value to an environment variable → os.getenv('API_KEY')

  HIGH       server.py:28
  Broken Access Control · Endpoint has no authentication guard
  ↳ ELI5: Add Depends(get_current_user) to protect this route

Fix the issues above, then run  git commit  again.
To skip (not recommended): git commit --no-verify
```

---

## CLI Commands

| Command | What it does |
|---|---|
| `kshield init` | Install hook + set up backend (run once per repo) |
| `kshield setup` | Install Python backend into `~/.kshield/` |
| `kshield start` | Start the backend in the background |
| `kshield stop` | Stop the background backend |
| `kshield status` | Check whether the backend and hook are running |
| `kshield scan <file>` | Manually scan a single file |
| `kshield hook` | Run a pre-commit scan (called by the git hook) |
| `kshield agent <name>` | Repo-wide audit — scans every tracked file at once, not just the diff |

---

## What It Detects

### Hardcoded Secrets — CRITICAL

Named token patterns matched exactly, with zero false positives on hashes or UUIDs:

| Token type | Example prefix |
|---|---|
| GitHub Classic / Fine-grained PAT | `ghp_` · `github_pat_` |
| GitHub OAuth / Actions / Refresh | `gho_` · `ghs_` · `ghr_` |
| GitLab PAT | `glpat-` |
| AWS Access Key | `AKIA...` |
| Google API Key | `AIza...` |
| OpenAI key (classic + project) | `sk-...T3BlbkFJ...` · `sk-proj-` |
| Anthropic API key | `sk-ant-` |
| Stripe live / test / publishable | `sk_live_` · `sk_test_` · `pk_live_` |
| SendGrid API key | `SG.` |
| Twilio / Mailgun | SID + auth token patterns |
| Slack bot / user token | `xoxb-` · `xoxp-` |
| Discord bot token | header + payload + signature |
| npm token | `npm_` |
| PyPI token | `pypi-` |
| HuggingFace token | `hf_` |
| Private key block | `-----BEGIN * PRIVATE KEY-----` |
| Generic assignment | `api_key = 'abc...'` · `secret_key = '...'` |

High-entropy strings (score > 4.8, length ≥ 24) that don't match a named pattern are flagged HIGH. UUIDs, hex hashes (MD5 / SHA-1 / SHA-256 / SHA-512), and semver strings are allowlisted.

### Broken Access Control — HIGH / MEDIUM

Scans Python files for FastAPI route handlers (`sync` and `async`) with no authentication guard:

- No `Depends()` or `Security()` in function signature → flagged
- No `dependencies=[Depends(...)]` on the decorator → flagged
- Severity: POST / PUT / DELETE / PATCH → **HIGH**; GET → **MEDIUM**
- Public paths automatically exempt: `/health`, `/ping`, `/docs`, `/redoc`, `/openapi.json`, `/metrics`, `/status`, `/version`, `/favicon.ico`, and more

### AI Hallucination Placeholders — MEDIUM

60+ patterns across five categories:

| Category | Examples |
|---|---|
| Placeholder markers | `TODO: verify before prod`, `add logic in this spot`, `still needs implementing` |
| Credential stubs | `password = 'hunter2'`, `api_key = 'stub-value'`, `bypass login checks` |
| Hallucinated imports | `from internal_test_ai import`, `mock_-prefixed imports`, `fake_-prefixed imports` |
| AI generation artifacts | `as an AI, I cannot`, `swap this stand-in for your real key`, `written by your AI pair programmer` |
| Dead code stubs | `raise NotImplemented (stub)`, bare `...` function bodies |

Test files (`test_*.py`, `*_test.py`, files under `tests/`) are exempt — stubs are legitimate there.

### Dependency Hallucinations — CRITICAL

Verifies every import against the official registry. Languages supported:

| Language | Files | Registry checked |
|---|---|---|
| Python | `.py` | PyPI (`pypi.org`) |
| JavaScript / TypeScript | `.js` `.ts` `.tsx` `.jsx` `.mjs` | npm (`registry.npmjs.org`) |
| Go | `.go` | Go module proxy (`proxy.golang.org`) |
| Ruby | `.rb` `Gemfile` | RubyGems (`rubygems.org`) |

Standard library modules are always skipped. Network timeouts fail open (commit is not blocked).

### Syntax Violations — MEDIUM

Python files with parse errors are flagged — truncated AI-generated code often fails to parse.

---

## Repo-Wide Audit

`kshield scan`/`hook` only look at the file (or staged diff) in front of you. `kshield agent <name>` audits an **entire repo at once** — every git-tracked file, in one pass:

```bash
kshield agent my-repo
```

```
  KShield · Agent · my-repo
  Building repo graph from 127 tracked files...

  Files scanned       127
  Routes found        8
  Findings            12

  Findings
    HIGH   backend/app/api/v1/actions.py:29
    Broken Access Control
    POST endpoint '/suppress' has no authentication guard.
    ...
```

It builds a full repo graph (imports, symbols, every route and its guards) before scanning, so access-control checks understand which routes are genuinely reachable and which auth dependencies are already proven to work elsewhere in your codebase — not just what's visible in a single diff. Findings you've already dismissed as false positives (`POST /api/v1/audit/dismiss-finding`) are remembered by normalized signature and auto-suppressed on future runs.

`org-audit.sh` chains this across every repo in a GitHub org — clone, `kshield agent <repo>` per repo, and a ranked summary from the local `audit_runs` table at the end.

## Auto-Remediation

Every finding that carries a patch has been **verified before it's shown to you** — kshield proposes a fix, applies it in memory, then re-runs the same check that raised the finding to confirm it's actually gone. If no fix can be proven safe, you get an explanation instead of a fabricated patch. Concretely: hardcoded secrets are extracted to `os.getenv(...)`, broken access control is fixed by reusing an authentication guard already used elsewhere in the same file (never invents a name that might not exist), and typo'd package names are corrected against a curated list of well-known packages — all with zero network calls and zero LLM involvement.

## Key Features

| Feature | Description |
|---|---|
| **Local-first** | Zero data leaves your machine — all analysis runs offline |
| **Zero-friction setup** | `kshield init` does everything: hook + backend + SQLite DB |
| **No Docker required** | Backend runs in a managed venv at `~/.kshield/` |
| **Repo-wide audit** | `kshield agent` scans a whole repo at once with graph-aware access-control checks |
| **Verified remediation** | Every patch is generated, applied in-memory, and re-checked before it's shown — never a fabricated fix |
| **False-positive memory** | Dismiss a finding once; kshield recognizes the same pattern next time and stays quiet |
| **Severity triage** | CRITICAL / HIGH / MEDIUM / LOW with per-rule toggles |
| **Similarity infrastructure** | pgvector embedding column on every finding — semantic ranking is on the roadmap |
| **Dashboard** | React UI with Exo 2 typography, light/dark theme, custom icons, slide-over detail |
| **Design system** | Reusable component library — Badge, Button, Card, CodeBlock, Drawer, and more |
| **In-app docs** | Built-in How to Use page with User Guide + API Reference tabs |
| **Desktop app** | Tauri wrapper packages the dashboard as a native OS window |
| **4 install paths** | `curl`, `npx`, `pip`, `brew` — all pointing to the same binary |

---

## Tech Stack

| Layer | Technology |
|---|---|
| CLI | Rust · Clap · Reqwest · Tokio |
| Backend | FastAPI · SQLAlchemy (async) · NumPy · pgvector |
| Database | PostgreSQL 16 + pgvector (or SQLite for local installs) |
| Frontend | React 19 · Vite 8 · Tailwind CSS v4 · Exo 2 · JetBrains Mono |
| Design System | Custom component library — tokens, 11 components, SVG icon set |
| Desktop | Tauri 2 |
| CI/CD | GitHub Actions (multi-platform release + PR scanning) |
| Infra | Docker Compose (optional, for production) |

---

## Project Structure

```
kshield/
├── cli/                        # Rust binary
│   └── src/
│       ├── main.rs             # CLI entry: init, setup, start, stop, status, hook, scan, agent
│       ├── setup.rs            # Backend lifecycle: download, venv, install, start, stop
│       ├── http.rs             # Backend API calls (health check, scan, audit)
│       ├── scanner.rs          # Git staged/tracked file reader
│       ├── ui.rs               # Colour terminal output
│       └── types.rs            # Shared types (ScanResult, Anomaly, AuditResult, etc.)
├── backend/                    # FastAPI analysis engine
│   └── app/
│       ├── api/v1/
│       │   ├── scan.py         # POST /api/v1/scan — single-file pipeline
│       │   ├── audit.py        # POST /api/v1/audit — repo-wide pipeline (kshield agent)
│       │   ├── actions.py      # POST /suppress, /apply-patch
│       │   ├── history.py      # GET /scans, /telemetry
│       │   └── patterns.py     # GET/POST /api/v1/patterns/auth-keywords
│       ├── engine/
│       │   ├── entropy.py · ast_rules.py · model.py · sandbox.py      # single-file scan engines
│       │   ├── graph_builder.py · access_control.py · orchestrator.py # repo-wide audit engines
│       │   ├── dependency_audit.py · quiet_office.py · pattern_archive.py
│       │   └── ksword.py       # verified auto-remediation agent
│       ├── models/             # SQLAlchemy ORM models
│       └── db/session.py       # Async session + SQLite fallback
├── frontend/                   # React dashboard
│   └── src/
│       ├── api/client.ts       # Backend HTTP client
│       ├── components/         # Dashboard · Settings · Sidebar · Docs
│       └── design-system/      # Component library
│           ├── tokens.ts       # Colors, radius, shadow, font tokens
│           ├── index.ts        # Barrel export
│           └── components/     # Badge · Button · Card · CodeBlock · Table
│                               # Alert · StatusDot · PageHeader · Drawer
│                               # EmptyState · Icons (SVG)
├── vscode-extension/            # VS Code extension — inline warnings as you type
│   └── src/
│       ├── extension.ts        # Activation, save watcher, command wiring
│       ├── apiClient.ts        # Backend HTTP client (/health, /api/v1/scan, /api/v1/suppress)
│       ├── diagnostics.ts      # Finding → vscode.Diagnostic mapping
│       ├── hoverProvider.ts    # ELI5 explanations on hover
│       ├── codeActionProvider.ts # Quick Fix: apply patch / suppress rule
│       ├── statusBar.ts        # Backend reachability indicator
│       └── patch.ts            # Unified diff applier for remediation patches
├── npm/                        # npx @ytt-global/kshield wrapper package
├── homebrew/kshield.rb         # Homebrew formula
├── install.sh                  # curl | bash installer
├── org-audit.sh                # kshield agent, chained across every repo in a GitHub org
├── pyproject.toml              # pip install kshield
├── assets/logo.svg             # Brand mark, used in this README
├── LICENSE                     # MIT
├── CHANGELOG.md
└── docs/
    ├── architecture.md         # Current system diagram — see architecture-v1.md for history
    ├── architecture-v1.md
    ├── setup.md
    └── features.md             # Complete, verified feature reference + known limitations
```

---

## VS Code Extension

Inline diagnostics as you type — scans on save, shows squiggles with hover explanations, and offers Quick Fix actions to apply a patch or suppress a rule. Talks to the same local backend the CLI manages.

**Install from the Marketplace (recommended):** search "KShield" in the Extensions view, or install directly:
```bash
code --install-extension YTTGlobal.kshield-vscode
```
Or via the [Marketplace listing](https://marketplace.visualstudio.com/items?itemName=YTTGlobal.kshield-vscode).

**Build from source instead:**
```bash
cd vscode-extension
npm install
npx @vscode/vsce package
code --install-extension kshield-vscode-<version>.vsix --force
```

See [vscode-extension/README.md](vscode-extension/README.md) for settings and commands.

---

## Managed Directory

After `kshield setup` or `kshield init`, the following is created in your home directory:

```
~/.kshield/
├── backend/          # Python backend source (downloaded from release)
├── venv/             # Isolated Python virtual environment
├── kshield.db       # SQLite database (scan history)
├── backend.pid       # PID of the running backend process
└── backend.log       # Backend stdout / stderr
```

---

## Architecture

See [docs/architecture.md](docs/architecture.md) for the full system diagram.

```
Developer Laptop
      │
      ├── Rust CLI ──── kshield init/hook/scan (single file) · kshield agent (whole repo)
      │        │
      │        └── manages ──► ~/.kshield/ (venv + db + pid)
      │
      └── React Dashboard (browser or Tauri window)
                    │
              HTTP / Webhooks
                    │
             FastAPI Backend  (port 8000)
             ┌────────────────────────────┐   ┌──────────────────────────────┐
             │ Single-file pipeline        │   │ Repo-wide audit pipeline      │
             │ Entropy Scanner             │   │ Graph Builder                 │
             │ AST Engine                  │   │ Graph-Aware Access Control    │
             │ Hallucination Pattern Match │   │ Orchestrator                  │
             │ Dependency Sandbox          │   │ Dependency Hygiene / Typosquat│
             └────────────────────────────┘   │ Quiet Office (FP memory)      │
                    │                          └──────────────────────────────┘
                    └───────────────┬──────────────────┘
                                    ▼
                     ksword — verified auto-remediation
                     (propose → apply → re-check → only then return a patch)
                                    │
             SQLite (local) or PostgreSQL + pgvector
```

---

## API Reference

The backend exposes a REST API at `http://localhost:8000`. Full reference is available in the dashboard under **How to Use → API Reference**.

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/health` | Backend liveness check |
| `POST` | `/api/v1/scan` | Submit a single file for security analysis (used by `hook`/`scan`) |
| `POST` | `/api/v1/audit` | Submit a whole repo's tracked files for a graph-aware audit (used by `agent`) |
| `POST` | `/api/v1/audit/dismiss-finding` | Mark a finding as a false positive so similar future findings are auto-suppressed |
| `GET` | `/api/v1/audit/runs` | List past `kshield agent` runs, ranked by severity |
| `GET` | `/api/v1/scans` | List past single-file scans |
| `GET` | `/api/v1/telemetry` | Aggregate scan/finding counts for the dashboard |
| `POST` | `/api/v1/suppress` | Globally suppress a rule type |
| `POST` | `/api/v1/apply-patch` | Apply a finding's verified remediation patch directly to the file on disk |
| `GET`/`POST` | `/api/v1/patterns/auth-keywords` | List / teach project-specific auth-guard names — e.g. `verify_org_membership` — so `access_control.py` stops flagging routes that already use them |

---

## Roadmap

- [x] Rust CLI — init, setup, start, stop, status, hook, scan, agent
- [x] Zero-friction install (curl, npx, pip, brew)
- [x] SQLite mode — no Docker for first run
- [x] Auto backend lifecycle management (~/.kshield/)
- [x] React dashboard — Exo 2 typography, light/dark, responsive, slide-over detail
- [x] Design system — tokens, 11 components, custom SVG icon set
- [x] In-app documentation — User Guide + API Reference with tab switcher
- [x] GitHub Actions — multi-platform release + PR scan
- [x] Homebrew formula
- [x] Trust Through Accuracy — 30+ secret patterns, async AST, Go/Ruby registries, test file exemption
- [x] Connect React dashboard to live backend endpoints
- [x] Filter chips (CRITICAL / HIGH / MEDIUM / LOW) on anomaly list
- [x] Toast notifications for patch application
- [x] VS Code extension — inline warnings as you type
- [x] Repo-wide audit — graph builder, graph-aware access control, `kshield agent`, org-wide scanning via `org-audit.sh`
- [x] False-positive memory — dismiss a finding once, similar future findings auto-suppress
- [x] Verified auto-remediation (ksword) — every patch is applied and re-checked before it's shown, not fabricated
- [ ] Extend ksword's access-control fix to reuse guards across the whole repo graph, not just the same file
- [ ] Real semantic embeddings — the pgvector column exists but isn't populated with a meaningful vector yet
- [ ] Windows support
- [ ] Tauri desktop build packaging

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for how to get involved. Participation in this project is governed by our [Code of Conduct](CODE_OF_CONDUCT.md).

---

## Security

Found a vulnerability? Please don't open a public issue — see [SECURITY.md](SECURITY.md) for how to report it responsibly.

---

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for version history.

---

## License

MIT — see [LICENSE](LICENSE)

Built for IT Teams by [YTT Global Services](https://ytt.global)
