# Contributing to KShield

Thank you for your interest in contributing. KShield is a local-first security tool — every contribution helps developers write safer code without giving up their privacy.

By participating in this project, you're expected to uphold our [Code of Conduct](CODE_OF_CONDUCT.md). Found a security vulnerability instead of a regular bug? See [SECURITY.md](SECURITY.md) — please don't open a public issue for it.

---

## Before You Start

- Read the [README](README.md) to understand what the tool does and why
- Read [docs/architecture.md](docs/architecture.md) to understand the system design
- Read [SKILLS.md](SKILLS.md) for the coding rules that govern this codebase — AI agents and human contributors follow the same rules

---

## Ways to Contribute

| Type | Examples |
|---|---|
| Bug reports | Scanner misses a vulnerability, `kshield init` fails on a specific platform, UI breaks at a viewport |
| Feature requests | New detection rule, new dashboard chart, Windows support, new CI integration |
| Code | Fix a bug, add a detection rule, improve a CLI command, improve a UI component |
| Docs | Clearer setup instructions, missing troubleshooting entry, better examples |
| Testing | Add test cases that cover edge cases in the analysis engine or CLI |

---

## Reporting a Bug

1. Check existing issues to avoid duplicates
2. Open a new issue with:
   - **One-line summary** in the title
   - **Steps to reproduce** (exact commands or UI actions)
   - **Expected behaviour** vs **actual behaviour**
   - **Environment** (OS + arch, Python version, Rust version, Node version)
   - **Relevant logs** (`~/.kshield/backend.log`, browser console, cargo output)

Security vulnerabilities should **not** be reported as public issues — see [SECURITY.md](SECURITY.md) for how to report them responsibly.

---

## Suggesting a Feature

Open an issue with the label `enhancement`. Describe:
- The problem you are trying to solve
- Why it can't be solved with the current tool
- A rough idea of how it could work

Large features (new engine rules, new UI sections, new integrations, new install paths) should be discussed in an issue before a PR is opened.

---

## Development Setup

Follow [docs/setup.md](docs/setup.md) to get the full stack running locally.

Quick start:
```bash
git clone https://github.com/YTT-Global/kshield.git
cd kshield

# Backend
cd backend && python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
SQLITE_FALLBACK=true uvicorn app.main:app --reload --port 8000 &

# Frontend
cd ../frontend && npm install && npm run dev

# CLI (dev build)
cd ../cli && cargo build
./target/debug/kshield status

# VS Code extension (dev build — press F5 in VS Code to launch it)
cd ../vscode-extension && npm install && npm run compile
```

Or use the managed install for the backend:
```bash
./target/debug/kshield setup
./target/debug/kshield start
```

---

## Branch Naming

```
feature/short-description       # new capability
fix/short-description           # bug fix
docs/short-description          # documentation only
refactor/short-description      # no behaviour change
```

All branches must fork from `main`.

---

## Making a Pull Request

1. Fork the repo and create your branch from `main`
2. Make your changes — see coding standards below
3. Run the relevant checks:

   ```bash
   # CLI
   cd cli && cargo build && cargo test

   # Backend
   # backend/tests/ is gitignored and not part of the public repo — verify
   # backend changes by starting the server and exercising the endpoint(s)
   # you touched (see docs/setup.md), not via an automated suite here.

   # Frontend
   cd frontend && npm run build && npm run lint

   # VS Code extension
   cd vscode-extension && npm run compile
   ```

4. Write a clear PR description:
   - **What changed** (one or two sentences)
   - **Why** (link to the issue if applicable)
   - **How to test** (exact steps a reviewer should follow)
5. Keep PRs focused — one concern per PR

---

## Coding Standards

### General
- Match the style of the surrounding code
- No dead code, no commented-out blocks, no TODO comments (open an issue instead)
- No `console.log` in production frontend code
- No raw error stack traces rendered in the UI

### Rust (CLI)

**Module responsibilities — do not cross them:**
| Module | Owns |
|---|---|
| `main.rs` | Command parsing, top-level command handlers only |
| `setup.rs` | Backend lifecycle: find, download, venv, install, spawn, PID |
| `http.rs` | All HTTP calls to the backend: health check, scan |
| `scanner.rs` | Git integration: staged files, HEAD SHA |
| `ui.rs` | All terminal output (ANSI colour, layout) |
| `types.rs` | Shared data types only — no logic |

Additional rules:
- All async functions must use `.await` — never create a nested `tokio::Runtime` inside an async context
- Use `anyhow::Result` for all fallible functions
- Keep `ui.rs` functions free of logic — they only format and print

### Python (Backend)
- Async all the way — no blocking calls in route handlers
- Pydantic models for all request/response shapes
- Engine modules must not import from each other — all orchestration happens in `scan.py`
- New detection rules go in `backend/app/engine/ast_rules.py` or `entropy.py`, not in the router
- `session.py` is the only place that touches the database URL or engine configuration

### TypeScript / React (Frontend)
- Use `import type` for type-only imports (required by Rolldown / Vite 8)
- No inline SVGs — use `lucide-react` for all icons
- All colours must have both a light and a `dark:` variant
- Components live in `frontend/src/components/` — one component per file
- No hardcoded mock data in components that will be wired to the API

---

## Testing the Zero-Friction Install

If you change `install.sh`, `npm/`, `pyproject.toml`, or `homebrew/kshield.rb`, test the install path end-to-end in a clean environment before submitting:

```bash
# Test shell installer syntax
bash -n install.sh

# Test npm wrapper JS
node npm/bin/kshield.js --version

# Test pip package structure
pip install -e . --dry-run
```

For the Homebrew formula, test with:
```bash
brew install --build-from-source homebrew/kshield.rb
```

---

## Commit Messages

```
type: short summary in present tense

Optional longer explanation of why, not what.
```

Types: `feat` · `fix` · `docs` · `refactor` · `test` · `chore`

Examples:
```
feat: add path traversal detection rule to AST engine
fix: try_start_backend uses tokio::time::sleep instead of nested runtime
docs: add uninstall section to setup guide
chore: update homebrew formula sha256 for v1.0.1
```

---

## Code Review

All PRs require at least one review before merging. Reviewers will check:

- Does it follow the coding standards above?
- Does the feature make sense for a local-first, privacy-first tool?
- Does `kshield init` still work end-to-end after the change?
- Are there new failure modes that need handling?
- Are UI changes tested in both light and dark mode?
- Are UI changes tested on mobile viewport?

---

## Licence

By contributing, you agree that your contributions will be licensed under the [MIT License](LICENSE) that covers this project.

---

Questions? Open a discussion or email `accounts@ytt.global`.
