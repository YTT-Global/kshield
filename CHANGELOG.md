# Changelog

All notable changes to KShield are documented here.

## [Unreleased]

### Added
- `kshield-vscode` is now live on the VS Code Marketplace as [`YTTGlobal.kshield-vscode`](https://marketplace.visualstudio.com/items?itemName=YTTGlobal.kshield-vscode). Docs updated to lead with `code --install-extension YTTGlobal.kshield-vscode` ahead of the manual `.vsix` build steps.

## [1.1.0] — 2026-07-17

### Added
- **VS Code extension** (`vscode-extension/`): inline security warnings as you type. Scans on file save (debounced), surfaces findings as editor diagnostics with hover explanations, and offers Quick Fix actions to apply remediation patches or suppress a rule globally. Talks to the same local backend the CLI manages.
- **VS Code extension packaging**: `repository` field added to `vscode-extension/package.json` and a bundled `LICENSE` so `vsce package` produces a clean `.vsix` with no warnings — installable locally via `code --install-extension` or publishable to the Marketplace.
- **Root `LICENSE` file** (MIT) added, matching the license already declared in `pyproject.toml` and `vscode-extension/package.json`.
- **PyPI publishing**: release pipeline now builds and publishes the backend package to PyPI on every non-prerelease tag.

### Fixed
- All download routes (curl installer, npm installer, Homebrew formula, pip package URLs, CLI's own backend-download URL, VS Code extension repository link, in-app Docs page) pointed at the old GitHub org `YTTGlobalServices` and 404'd after the org moved to `YTT-Global`. Repointed everywhere, including two spots (`cli/src/setup.rs`, `frontend/src/components/Docs.tsx`) that a prior pass missed.
- Homebrew formula's release-CI step was patching the wrong SHA-256 placeholder strings for macOS builds, leaving stale checksums in published formula updates.
- `backend/requirements.txt` was missing `numpy`, despite `app/engine/model.py` importing it directly — added `numpy>=1.26` as an explicit dependency instead of relying on it being pulled in transitively by `tensorflow`.

## [1.0.0] — 2026-07-14

### Initial Release

KShield is a local-first AI code review firewall designed to catch secrets, broken access control, and AI hallucinations before they reach your main branch.

### Key Highlights & Features

#### Accuracy — Trust Through Accuracy
- **Secrets & Entropy Engine (`entropy.py`)**:
  - Expanded named-token signatures for 30+ categories (VCS tokens, cloud credentials, AI APIs, payment platforms, package registries, messaging tokens, etc.).
  - Entropy threshold optimized at 4.8 to reduce false positives on long variable names.
  - Minimum string length set to 24 characters to eliminate noise on short tokens.
  - Integrated allowlist to skip hashes, UUIDs, and semver strings.
  - Deduplicated matches to prevent double-reporting across multiple engines.
- **AST Engine (`ast_rules.py`)**:
  - Full support for `async def` FastAPI routes to ensure comprehensive security analysis.
  - Public path allowlist (`/health`, `/healthz`, `/metrics`, etc.) to suppress false authorization flags.
  - Detection of `dependencies=[Depends(...)]` decorator keyword arguments for accurate auth-guard verification.
  - Differentiated severity: POST/PUT/DELETE/PATCH without auth is HIGH; GET without auth is MEDIUM.
- **Hallucination Classifier (`model.py`)**:
  - 60+ regex patterns across 5 categories (placeholders, credential stubs, mock imports, AI artifacts, dead code) to detect AI-generated hallucinations.
  - Automatic exemption of test files (`test_*.py`, `*_test.py`, or `tests/` directory) to support legitimate mock stubs in test suites.
  - One finding per line maximum to keep reports clean.
- **Dependency Sandbox (`sandbox.py`)**:
  - Support for Go module dependency parsing and verification against `proxy.golang.org`.
  - Support for Ruby gem dependency checks against `rubygems.org`.
  - Precise line number reporting for imports.
  - Deduplicated checks per package/file to optimize performance.
- **Engine Tests**:
  - `backend/tests/test_engines.py` includes 35 accuracy regression tests covering both true positives and false-positive suppression.

#### System Architecture & CLI
- **Rust CLI**: High-performance utilities for `init`, `setup`, `start`, `stop`, `status`, `hook`, and `scan`.
- **Zero-Friction Installers**: Multi-channel installation via `curl | bash`, npm `npx`, pip `pip install`, and Homebrew.
- **Local-first & Secure**: All scanning runs on-device; no source code or credentials ever leave the local machine.
- **FastAPI Backend**: High-performance local scanning engine with flexible SQLite and PostgreSQL options.
- **pgvector Integration**: 1536-dimensional semantic search embeddings for historic scan analysis.
- **Enterprise Dashboard**: Modern React + Tailwind CSS v4 interface featuring light/dark theme, responsive sidebar, and an interactive slide-over anomaly drawer.
- **Custom Brand Identity**: Professional enterprise badge and custom SVG logo integrated into the dashboard and favicon.

#### Security & Quality Hardening
- Explicit origin allowlist for CORS via `CORS_ORIGINS` environment variable.
- Secured PyPI registry sandbox URL endpoints.
- Secured npm sandbox URL endpoints.
- Python standard library bypass list expanded using `sys.stdlib_module_names`.
- Timezone-aware UTC timestamps throughout the system.
- AST auth-guard detection extended to support keyword-only arguments.
- Deterministic embedding generation using MD5.
- GitHub Actions CI for automated testing, security scanning, and cross-platform build verification.
- Multi-platform binary publishing via GitHub Actions for macOS (arm64, x86) and Linux (x86, arm64).

#### Dashboard & Design System
- **Design System**: Full component library at `frontend/src/design-system/` — design tokens, `Button`, `Badge` (Severity / Method / Status / Label), `Card`, `CodeBlock` with copy, `DiffViewer`, `Table`, `FieldTable`, `Alert`, `StatusDot`, `LivePill`, `PageHeader`, `SectionHeader`, `Drawer`, and `EmptyState`.
- **Custom SVG Icons**: `WorkspacesIcon`, `StructuralHazardsIcon`, and `EngineActiveIcon` — purpose-built for the dashboard panel headers.
- **Typography**: Exo 2 (sans-serif) + JetBrains Mono loaded via Google Fonts — consistent across all views.
- **In-app Documentation**: "How to Use" page in the sidebar with two tabs — User Guide (Quick Start, Install, CLI, What It Detects, Managed Directory) and API Reference (endpoint overview, full request/response schema, error codes).
- **API Reference tab**: Documents `GET /health` and `POST /api/v1/scan` with request body table, example JSON, response schema, and error code reference.

#### Bug Fixes
- Fixed `NameError: CodeExecutionPayload` in `backend/app/api/v1/scan.py` — renamed to match the defined `ScanRequest` Pydantic model.
- Fixed stale `.venv` interpreter path after project rename from `ai-firewall` to `kshield`.
