# Changelog

All notable changes to KShield are documented here.

## [Unreleased]

### Added
- **Repo-wide audit** (`kshield agent <name>`, `POST /api/v1/audit`): scans every git-tracked file in one pass instead of just the staged diff.
  - `graph_builder.py` builds a full repo graph (imports, symbols, every route with its guards, parse errors) before any check runs.
  - `access_control.py` is a graph-aware Broken Access Control check — reuses guard names already proven elsewhere in the repo, exempts public paths, escalates severity on sensitive paths (`/admin`, `/payment`, etc.), and recognizes webhook signature-verification as a valid guard shape even when it isn't a `Depends()`.
  - `orchestrator.py` sequences the audit: graph build → access control → a single batched, concurrency-bounded pass over every dependency registry lookup in the repo (was previously one-at-a-time per file, which timed out on large monorepos) → per-file entropy/hallucination/dependency scans reusing that cache.
  - `dependency_audit.py` adds two new finding types: **Possible Typosquat** (Levenshtein distance against a curated popular-package list) and **Undeclared Dependency** (import not found in `requirements.txt`/`pyproject.toml`/`package.json`).
  - `quiet_office.py` + `pattern_archive.py`: dismissing a finding (`POST /api/v1/audit/dismiss-finding`) is remembered by normalized signature and auto-suppresses matching findings on future runs; project-specific auth-keyword names learned this way persist across audits.
  - `audit_runs` table + `GET /api/v1/audit/runs` — every audit run is persisted with file/finding/severity counts.
  - `org-audit.sh` — chains `kshield agent` across every non-archived repo in a GitHub org, cloning in parallel and reporting a ranked summary from `audit_runs`.
- **Verified auto-remediation agent (`ksword.py`)**, replacing the old `remediation.py`. Every strategy proposes a fix, applies it in-memory, then re-runs the *same check* that raised the original finding against the patched result — a patch is only ever returned if that re-check confirms the finding actually cleared. No network calls, no model inference.
  - Hardcoded Secret / High Entropy Credential → extracted to `os.getenv("VAR_NAME")`, adding `import os` if missing.
  - Broken Access Control → reuses a `Depends()`/`Security()` guard already proven to work elsewhere in the same file; declines rather than inventing a guard name that might not exist.
  - Possible Typosquat → corrects the import to the well-known package name identified by the typosquat check.
  - Dependency Hallucination / Syntax Violation / AI Structural Hallucination → explanation-only by design; a rule engine can't safely fabricate business logic or guess a real package name.
  - Wired into `/api/v1/scan`, `/api/v1/audit`, and `/api/v1/apply-patch`. The Rust CLI's `agent` output now renders remediation diffs the same way `scan`/`hook` already did.
- `kshield-vscode` is now live on the VS Code Marketplace as [`YTTGlobal.kshield-vscode`](https://marketplace.visualstudio.com/items?itemName=YTTGlobal.kshield-vscode). Docs updated to lead with `code --install-extension YTTGlobal.kshield-vscode` ahead of the manual `.vsix` build steps.
- **Windows release target** (`x86_64-pc-windows-msvc`): `release.yml`'s build matrix now includes a native `windows-latest` runner alongside the existing macOS/Linux targets, producing a `.zip` (the other targets ship `.tar.gz`). The Rust CLI already had real Windows branches from day one (`USERPROFILE` fallback for the home directory, `venv/Scripts/python.exe` vs `venv/bin/python`) — they'd just never been built or shipped. Cross-compiled locally via `x86_64-pc-windows-gnu` + mingw-w64 as a smoke test before wiring up the CI target; **not yet verified on a real Windows machine**, so treat this release's Windows binary as best-effort until someone reports back. `npm/scripts/install.js` and `npm/bin/kshield.js` now detect `win32` and handle the `.exe`/`.zip` difference; `install.sh` (bash-only) now fails fast with a clear pointer to the npm path instead of silently mis-downloading a `.tar.gz` under Git Bash/MSYS.

### Fixed
- **The npm package name `kshield` was squatted** by an unrelated third-party CLI (`kidshield`) — `npx kshield init`, as documented everywhere, silently ran someone else's tool instead of failing loudly. Renamed the package to the scoped `@ytt-global/kshield`; the installed command is still `kshield` (the `bin` field is unchanged), only the install/npx invocation changes. Every reference (`README.md`, `docs/setup.md`, `docs/features.md`, `install.sh`'s error text, the release-notes template, the npm package's own error/warning strings) updated to match.
- **`backend/tests/` is intentionally gitignored, not shipped in the public repo.** This audit-engine work is backed by a 186-test local suite (`test_access_control.py`, `test_ksword.py`, `test_orchestrator.py`, and six others) — all passing — but the test files themselves aren't committed. Practical effect: CI's `pytest tests/ || echo "No tests yet"` step reports "No tests yet" on every run, and a fresh clone has no test suite to run at all. `CONTRIBUTING.md`'s testing section reflects this.
- `remediation.py`'s Broken Access Control patch referenced symbols (`AuthenticationGuard`, `app`) that didn't exist in the target file and could corrupt it when applied via `git apply` — this was the entire reason for the ksword rewrite above. All finding types other than Broken Access Control previously returned no patch at all (an empty `patch_diff`), even where a safe automated fix was possible.
- `.github/workflows/ci.yml`'s backend import-sanity step still referenced the now-deleted `app.engine.remediation` module.
- README's CI badge pointed at a workflow file (`kshield-ci.yml`) that doesn't exist — the real workflow is `ci.yml`.
- `backend/requirements.txt` declared `tensorflow`, `sqlmodel`, and `cachetools` — none are imported anywhere in `app/`. `tensorflow` alone added several hundred MB to every local `kshield setup` and CI install for zero functional benefit; `model.py`'s classifier is regex-based, not ML.
- `backend/Dockerfile` built on `python:3.12-slim` while the rest of the project (pyproject.toml, CI, the local `.venv`) targets 3.11 — repointed to match. It also never installed `curl`, which `docker-compose.yml`'s backend healthcheck requires (`curl -f http://localhost:8000/health`) — on a Debian slim base that command doesn't exist, so the healthcheck would fail indefinitely and `frontend` (which waits on `backend: condition: service_healthy`) would never start.
- **`POST /api/v1/apply-patch` did not actually work end-to-end in any real workflow**, found during a full live-verification pass. Three independent bugs stacked:
  1. `cmd_hook`/`cmd_agent` sent `filename` as the raw string from `git diff --cached --name-only`/`git ls-files` — repo-relative, not absolute. `apply-patch`'s file lookup tries the string as-is, then `~/`, then the *backend daemon's own cwd* — none of which reliably matches a real repo, so the endpoint almost always returned `"File not found on disk"`. Fixed by resolving every path against `git rev-parse --show-toplevel` in `scanner.rs` before it ever leaves the CLI, and canonicalizing `cmd_scan`'s argument the same way.
  2. Once the file *was* found (an absolute path), `ksword.py`'s diff header used the full path (`a/{filename}`) — for an absolute path this produced `a//abs/path`, which `git apply` rejects outright (`error: invalid path`) since the default `-p1` strip still leaves an absolute remainder. Fixed by using the basename in the diff header, independent of whether the caller's `filename` is absolute or relative.
  3. Even with a correct header, the generated `patch_diff` had no trailing newline (`"\n".join(...)` never terminates the final line) — `git apply` treats that as `"corrupt patch at line N"` and refuses the whole file. The `test_ksword.py` helper had been silently adding the missing newline itself before writing the patch to disk, which is why all 12 ksword tests passed while the real endpoint was broken the whole time. Fixed in `ksword.py::_unified_diff` (single source of truth for every consumer), and the test helper now writes `patch_diff` byte-for-byte with an explicit assertion that it already ends in `\n`.
  
  Verified live end-to-end after the fix: `kshield hook` run from a repo subdirectory → correct absolute path in the finding → `apply-patch` → `status: "applied"` → re-scan of the patched file on disk → `safe: true`.
- `kshield agent --help` still described the command as "graph plumbing only — detection findings land in a later milestone", a holdover from before M2–M7 were built. It has produced full findings and remediation for some time; the help text now says so.
- **`ksword.py`'s Broken Access Control fix could reuse a non-auth dependency as the "guard"**, found by running `kshield agent` against kshield's own repo (11 of 46 findings hit this). `_existing_guard_in_file` accepted *any* `Depends()`/`Security()` call found elsewhere in the file — including `get_db_session` — with no check that the name was actually auth-related. The resulting patch applied cleanly and even passed verification, because verification used `ast_rules.py`'s checker, which has the identical blind spot (any `Depends()` counts as a guard — the specific gap `access_control.py`'s M2 fix exists to close, per its own test suite). Net effect: a "verified" patch that added zero real authentication. Fixed by reusing `access_control.py`'s own `_AUTH_KEYWORDS`/`_looks_like_auth` filter when selecting a guard to reuse, and by re-pointing verification at `access_control.py`'s graph-aware checker instead of `ast_rules.py`'s simpler one — strictly stricter than before, so this can only make ksword decline more often, never less safely.
- **`kshield agent`/`kshield hook` silently misbehaved when run from any subdirectory of a repo, not just the root.** `git ls-files` (used by `agent`) defaults to both a cwd-relative *scope* (only that subdirectory's files) and a cwd-relative *path format* — running `kshield agent` from `cli/` audited only `cli/`'s 9 files while reporting no error, not the repo's 145. `git diff --cached --name-only` (used by `hook`) is repo-root-relative by default, which happened to make an earlier fix look correct when tested — but the per-file `git show :{filename}` call that reads each staged blob interprets that same repo-relative path *relative to cwd*, so a staged file outside the invoking subdirectory could silently fail to read. Fixed by pinning every git subprocess in `scanner.rs` to the repo root via `.current_dir()`, rather than relying on each git subcommand's own (inconsistent) default. Verified live: `kshield agent` from `cli/` now reports all 145 files; `kshield hook` run from a subdirectory with the real staged change in a sibling directory now finds and flags it correctly.
- **`kshield agent` silently ignored `.kshield.yml` and the dashboard's global "Suppress Rule" action entirely.** Only `quiet_office.py`'s dismissed-finding memory applied to the repo-wide audit path — unlike `kshield scan`/`hook` (`scan.py`), which already merges both. A rule suppressed via the dashboard, or a severity/path ignored via `.kshield.yml`, would silently reappear the moment you ran a repo-wide audit instead of a single-file scan — same config, two different outcomes. Fixed by wiring the suppress config through the whole path: CLI (`cmd_agent` now calls `config::load()`, same as `cmd_hook`/`cmd_scan`), the wire format (`AuditPayload`/`AuditRequest` gain a `suppress` field), and the backend (`orchestrator.py::run_audit` now merges globally-suppressed rules and calls `suppress.py::apply()`, the same way `scan.py` does). Verified live: a `.kshield.yml` rule suppression that `kshield scan` already respected now also applies to `kshield agent` against the same repo.
  - This surfaced a real ordering bug: `suppress.py` and `quiet_office.py` both unconditionally overwrote a finding's `suppressed` flag, so whichever ran second could silently un-suppress what the first had already suppressed. Both are now "sticky" — a finding already marked suppressed stays suppressed regardless of call order. Covered by six new tests in `test_orchestrator.py`.
  - The CLI's "Quieted" label always said `(matches a previously dismissed finding)`, which stopped being accurate now that a quieted finding can come from three different mechanisms — reworded to name all three.
- **The dashboard's "Detection Rules" section in Settings was entirely client-side mock state** — an empty initial list, a "Save Configuration" button that just flipped a local flag with `setTimeout`, and an "Add New Rule" form implying a custom-rule capability the backend has never had. None of it called the API or persisted anything. Replaced with a real, API-backed list of the 8 actual rule types the engine supports; toggling one now calls the same `POST`/`DELETE /api/v1/suppress` endpoints the dashboard's per-finding "Suppress Rule" button already used, so state is consistent everywhere instead of three disconnected mechanisms (a fake toggle UI, a real global-suppress table, and `.kshield.yml` — see above) each showing something different. The separate "Suppressed Rules" panel added earlier this cycle is folded into this one section rather than kept as a redundant second view of the same state.

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
