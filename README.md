# KShield

> The pre-commit security firewall for developers. Catches hardcoded secrets, broken access control, AI hallucinations, and supply-chain risks — entirely on your machine, before a single line reaches your remote.

[![Build](https://img.shields.io/github/actions/workflow/status/YTTGlobalServices/kshield/kshield-ci.yml?label=CI&style=flat-square)](https://github.com/YTTGlobalServices/kshield/actions)
[![Release](https://img.shields.io/github/v/release/YTTGlobalServices/kshield?style=flat-square)](https://github.com/YTTGlobalServices/kshield/releases/latest)
[![License](https://img.shields.io/badge/license-MIT-blue?style=flat-square)](LICENSE)
[![Stack](https://img.shields.io/badge/stack-Rust%20·%20FastAPI%20·%20React-red?style=flat-square)](#tech-stack)

---

## The Problem This Solves

Most security tools run in the cloud, require API keys, and send your source code to third-party servers. KShield runs **entirely on your machine** — no telemetry, no data leaving your laptop. It sits between your `git commit` and your remote, scanning every staged change in real time.

---

## Install

Pick any one — they all end up at the same binary and the same experience:

**macOS / Linux (recommended):**
```bash
curl -fsSL https://raw.githubusercontent.com/YTTGlobalServices/kshield/main/install.sh | bash
```

**Homebrew (macOS):**
```bash
brew install YTT-Global/tap/kshield
```

**npm / npx (JavaScript developers):**
```bash
npx kshield init
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
!  Backend not installed — running setup (one-time)...
✓  Python environment ready   (~/.kshield/venv)
✓  Backend started            (SQLite, no Docker needed)
✓  Ready. Make a commit to run your first scan.
```

Now make any commit — the firewall runs automatically:

```
KShield · Pre-Commit Scan
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
| Placeholder markers | `TODO: verify with production`, `insert logic here`, `not implemented yet` |
| Credential stubs | `password = 'password'`, `api_key = 'fake'`, `disable auth` |
| Hallucinated imports | `from internal_ai_test import`, `import mock_*`, `import fake_*` |
| AI generation artifacts | `as an AI language model`, `replace this with your actual key`, `generated by Copilot` |
| Dead code stubs | `raise NotImplementedError`, bare `...` function bodies |

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

## Key Features

| Feature | Description |
|---|---|
| **Local-first** | Zero data leaves your machine — all analysis runs offline |
| **Zero-friction setup** | `kshield init` does everything: hook + backend + SQLite DB |
| **No Docker required** | Backend runs in a managed venv at `~/.kshield/` |
| **Auto-remediation** | Unified diff patches and ELI5 explanations for every finding |
| **Severity triage** | CRITICAL / HIGH / MEDIUM / LOW with per-rule toggles |
| **Semantic search** | pgvector embeddings for similarity search across scan history |
| **Dashboard** | React UI with light/dark theme, live telemetry, slide-over detail |
| **Desktop app** | Tauri wrapper packages the dashboard as a native OS window |
| **4 install paths** | `curl`, `npx`, `pip`, `brew` — all pointing to the same binary |

---

## Tech Stack

| Layer | Technology |
|---|---|
| CLI | Rust · Clap · Reqwest · Tokio |
| Backend | FastAPI · SQLAlchemy (async) · NumPy · pgvector |
| Database | PostgreSQL 16 + pgvector (or SQLite for local installs) |
| Frontend | React 19 · Vite 8 · Tailwind CSS v4 · Lucide React |
| Desktop | Tauri 2 |
| CI/CD | GitHub Actions (multi-platform release + PR scanning) |
| Infra | Docker Compose (optional, for production) |

---

## Project Structure

```
kshield/
├── cli/                        # Rust binary
│   └── src/
│       ├── main.rs             # CLI entry: init, setup, start, stop, status, hook, scan
│       ├── setup.rs            # Backend lifecycle: download, venv, install, start, stop
│       ├── http.rs             # Backend API calls (health check, scan)
│       ├── scanner.rs          # Git staged file reader
│       ├── ui.rs               # Colour terminal output
│       └── types.rs            # Shared types (ScanResult, Anomaly, etc.)
├── backend/                    # FastAPI analysis engine
│   └── app/
│       ├── api/v1/scan.py      # POST /api/v1/scan endpoint
│       ├── engine/             # entropy · ast_rules · model · sandbox · remediation
│       ├── models/             # SQLAlchemy ORM models
│       └── db/session.py       # Async session + SQLite fallback
├── frontend/                   # React dashboard
│   └── src/components/         # Dashboard · Settings · Sidebar
├── npm/                        # npx kshield wrapper package
├── homebrew/kshield.rb     # Homebrew formula
├── install.sh                  # curl | bash installer
├── pyproject.toml              # pip install kshield
├── CHANGELOG.md
└── docs/
    ├── architecture.md
    └── setup.md
```

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
      ├── Rust CLI ──── kshield init/hook/scan
      │        │
      │        └── manages ──► ~/.kshield/ (venv + db + pid)
      │
      └── React Dashboard (browser or Tauri window)
                    │
              HTTP / Webhooks
                    │
             FastAPI Backend  (port 8000)
             ┌──────────────────────┐
             │ Entropy Scanner       │
             │ AST Engine            │
             │ ML Classifier         │
             │ Hallucination Guard   │
             │ Remediation Engine    │
             └──────────────────────┘
                    │
             SQLite (local) or PostgreSQL + pgvector
```

---

## Roadmap

- [x] Rust CLI — init, setup, start, stop, status, hook, scan
- [x] Zero-friction install (curl, npx, pip, brew)
- [x] SQLite mode — no Docker for first run
- [x] Auto backend lifecycle management (~/.kshield/)
- [x] React dashboard — enterprise custom SVG logo, stacked brand layout, light/dark, responsive, slide-over detail
- [x] GitHub Actions — multi-platform release + PR scan
- [x] Homebrew formula
- [x] Trust Through Accuracy — 30+ secret patterns, async AST, Go/Ruby registries, test file exemption
- [ ] Connect React dashboard to live backend endpoints
- [ ] Filter chips (CRITICAL / HIGH / MEDIUM) on anomaly list
- [ ] Toast notifications for patch application
- [ ] VS Code extension — inline warnings as you type
- [ ] Windows support
- [ ] Tauri desktop build packaging

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for how to get involved.

---

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for version history.

---

## License

MIT — see [LICENSE](LICENSE)

Built by [YTT Global Services](https://ytt.global)
