# AI Capabilities & System Architecture Blueprint

This document is the authoritative system manual for AI development agents (Claude Code, Cursor, Copilot) and human contributors to safely extend, modify, and optimise **KShield** without introducing breaking structural changes.

_Last verified against the codebase: 2026-07-19 (`dev` branch). If you change a schema, file, or stack item described here, update this document in the same change — a stale manual is worse than no manual._

---

## 1. Rust CLI & Terminal Engine (`/cli`)

**Stack:** Rust · Clap (derive) · Reqwest (rustls-tls) · Tokio · Anyhow · Serde / serde_json / serde_yaml

Output is plain ANSI colour codes printed directly (`src/ui.rs`) — there is no TUI framework (no Ratatui, no Crossterm) anywhere in this binary. Don't introduce one without discussing it; the terminal output is intentionally simple, scriptable, and log-friendly.

### File Responsibilities

| File | Owns |
|---|---|
| `src/main.rs` | Entry point, `clap` subcommand parsing, exit-code chain |
| `src/setup.rs` | Backend lifecycle — download, venv creation, pip install, start/stop, PID file |
| `src/http.rs` | Reqwest calls to the backend (`health_check`, `scan_file`, `audit_repo`) |
| `src/scanner.rs` | Git staged-file reader (`git diff --cached`), tracked-file reader for `agent` — every git subprocess is pinned to the repo root via `.current_dir()`, deliberately (see below) |
| `src/ui.rs` | All ANSI colour output — `print_blocked`, `print_clean`, `print_audit_summary`, etc. |
| `src/types.rs` | Shared types mirroring the backend's JSON contracts (`Anomaly`, `Remediation`, `AuditFinding`, `AuditResult`) |
| `src/config.rs` | `.kshield.yml` suppress-config parsing |

### Commands

`init` · `setup` · `start` · `stop` · `status` · `hook` · `scan <file>` · `agent <name>`

`hook` and `scan` call `POST /api/v1/scan` (single file). `agent` reads every git-tracked file in the current repo and calls `POST /api/v1/audit` (repo-wide) — this is the CLI entry point for the graph-aware audit engine described in §2b. `org-audit.sh` at the repo root chains `kshield agent` across every non-archived repo in a GitHub org, one clone per repo, then reports from the `audit_runs` table.

### Extension Rules

- **Adding a new terminal view**: add a `print_*` function in `src/ui.rs` using plain `println!` + the `RESET`/colour constants already defined there. Do not introduce a rendering framework.
- **Changing exit behaviour**: `hook` and `agent` **must exit `1`** when any `CRITICAL` or `HIGH` finding is unmitigated (see `cmd_hook`/`cmd_agent` in `main.rs`). Do not swallow errors silently.
- **Changing the finding schema**: `AuditFinding`/`Anomaly` in `src/types.rs` must mirror the backend's JSON response *field for field*, including the `remediation: Remediation` struct — if you add a field to a backend finding dict, add it here too or `serde` will silently drop it.
- **Never trust a git subcommand's default path-relativity.** `git diff --cached --name-only` is repo-root-relative by default; `git ls-files` is cwd-relative by default (both scope *and* format) — two different defaults for two very similar-looking commands. A real bug shipped because of this: `kshield agent` run from any subdirectory silently audited only that subdirectory, and `git show :{filename}` (used to read a staged blob) interpreted an already-root-relative path as cwd-relative and could fail to find files outside the invoking directory. Every git subprocess in `scanner.rs` now runs with `.current_dir(&root)` explicitly — don't add a new git call there without doing the same, and don't assume any git subcommand's default matches another's.

---

## 2. Asynchronous FastAPI Core (`/backend/app`)

**Stack:** Python 3.11 · FastAPI · Asyncio · HTTPX · SQLAlchemy 2.0 (async) · Pydantic v2 · NumPy

`tensorflow` is listed in `requirements.txt` but is **not imported anywhere in `app/`** — there is no ML model. `model.py`'s "classifier" is a hardcoded regex list. Don't build on the assumption that a model exists; if you actually need a real classifier, that's new work, not an extension of existing code.

### Two pipelines, two schemas

There are **two distinct entry points** with different data shapes — do not conflate them.

**Finding dicts (internal, produced by every `engine/*.py` module and consumed by `ksword.py`):**
```python
{"line_number": int, "anomaly_type": str, "severity": str, "description": str, "code_snippet": str}
# + "filename": str  (present on every finding once it leaves orchestrator.py / audit.py)
```
Valid `severity`: `"CRITICAL"` · `"HIGH"` · `"MEDIUM"` · `"LOW"`. There is no `"INFO"` level anywhere in this codebase.

**API response shape (`POST /api/v1/scan`, `POST /api/v1/audit`) — renamed for the client contract:**
```python
{"line": int, "type": str, "severity": str, "description": str, "remediation": {"explanation": str, "patch_diff": str}}
```
The rename happens in `app/api/v1/scan.py`'s `computed_vulnerabilities` construction. If you change either shape, update the other side of the rename *and* `cli/src/types.rs`, `frontend/src/types/scan.ts`, and `vscode-extension/src/types.ts` in the same change.

### File Responsibilities — single-file pipeline (`POST /api/v1/scan`)

| File | Owns |
|---|---|
| `app/main.py` | FastAPI app factory, lifespan (`init_db`/`close_db`), CORS |
| `app/api/v1/scan.py` | Route orchestration: entropy + AST + hallucination + sandbox + ksword, persists `Scan`/`Vulnerability` rows |
| `app/engine/entropy.py` | Named-token secret regexes + Shannon-entropy fallback scanner |
| `app/engine/ast_rules.py` | Single-file AST visitor — Broken Access Control, Syntax Violation |
| `app/engine/model.py` | Regex-based "AI Structural Hallucination" pattern matcher (not ML) |
| `app/engine/sandbox.py` | Async PyPI / npm / Go proxy / RubyGems registry verification, with a `collect_only` batching mode used by the audit pipeline |

### File Responsibilities — repo-wide audit pipeline (`POST /api/v1/audit`, i.e. `kshield agent`)

| File | Owns |
|---|---|
| `app/api/v1/audit.py` | Route orchestration for `run_audit`, persists `AuditRun` rows, attaches ksword remediation per finding |
| `app/engine/graph_builder.py` | Builds a `RepoGraph` (imports, symbols, routes, parse errors) from every file in one pass — Python via `ast`, JS/TS via regex |
| `app/engine/access_control.py` | Graph-aware Broken Access Control — same-file guard reuse, public-path exemption, sensitive-path severity escalation, webhook signature-guard recognition |
| `app/engine/orchestrator.py` | `run_audit()` — sequences graph build → access control → dependency registry checks (batched, concurrency-bounded) → per-file entropy/hallucination/dependency scans → suppression pass |
| `app/engine/dependency_audit.py` | Declared-dependency parsing (`requirements.txt` / `pyproject.toml` / `package.json`) + Levenshtein-distance typosquat detection against a curated popular-package list |
| `app/engine/quiet_office.py` | Signature-based false-positive suppression — a dismissed finding's normalized description is remembered and matched against future findings of the same `anomaly_type` |
| `app/engine/pattern_archive.py` | Persists repo-specific extra auth-keyword strings (via `Configuration` rows) so `access_control.py` learns project-specific guard names over time |

### Remediation (`app/engine/ksword.py`)

**Not an LLM agent and not a template engine.** Every strategy runs propose → apply-in-memory → re-run-the-same-check-that-raised-the-finding → only return the diff if that re-check confirms the finding actually cleared. No network calls, no model inference. This replaced the old `app/engine/remediation.py`, which fabricated patches referencing symbols (`AuthenticationGuard`) that didn't exist in the target file and corrupted files on `git apply` — the verify-before-return step is the entire point; do not add a strategy that skips it.

Current strategies: secret → `os.getenv(...)` extraction (Hardcoded Secret / High Entropy Credential), access-control fix by reusing a `Depends()`/`Security()` guard already proven elsewhere in the same file (never invents a guard name), typosquat import correction (Possible Typosquat). Everything else (Dependency Hallucination, Syntax Violation, AI Structural Hallucination, Undeclared Dependency) is explanation-only by design — a rule engine cannot safely fabricate business logic or guess a real package name, so it says so instead of guessing.

The access-control strategy's "guard already proven elsewhere in the same file" check is stricter than it sounds: the reused name must also pass `access_control.py`'s own `_AUTH_KEYWORDS`/`_looks_like_auth` filter, not just match the shape `Depends(name)`. A real bug (found dogfooding `kshield agent` on this repo) reused `get_db_session` as a "guard" — a genuine `Depends()` call, just not an auth one — because nothing checked whether `name` actually looked auth-related; the patch applied cleanly and even "passed verification." That's because verification, at the time, went through `ast_rules.py`'s checker, which has the identical blind spot (any `Depends()` counts as a guard). Verification now goes through `access_control.py`'s graph-aware `check_access_control` instead — if you add a new access-control remediation path, verify against that checker, not `ast_rules.py`'s simpler one.

**Adding a new remediation strategy**: add a `_fix_<type>()` proposer and a `_verify_<type>_fixed()` checker in `ksword.py`, wire both into `construct_remediation_patch()`'s dispatch. The verify function must call back into the *same engine function* that produces that finding type — never assert correctness by inspecting your own patch's text.

**Adding a new AST-based finding (single-file path)**
1. Open `app/engine/ast_rules.py`, subclass/extend `ast.NodeVisitor`.
2. Append to the violations list using the internal schema above — `line_number`/`anomaly_type`, not `line`/`type`.
3. If the same class of finding should also run repo-wide with graph context, add the graph-aware version to `access_control.py` (or a new `engine/*.py` module) and wire it into `orchestrator.py::run_audit`, not `ast_rules.py` — the two pipelines intentionally don't share detection code (see the comment block at the top of `orchestrator.py`).

**Adding a new registry mirror (e.g., Cargo, RubyGems is already done)**
1. Open `app/engine/sandbox.py`.
2. Add a case to `evaluate_dependency_hallucinations` using the existing `_check_cached` helper (handles both the direct-check and `collect_only`-batching modes automatically — don't call `_check_registry` directly from a new code path or you'll break the audit pipeline's bulk pre-check).
3. Return findings using the internal schema (`anomaly_type: "Dependency Hallucination"`, `severity: "CRITICAL"`).

**Changing the scan or audit response shape**
- `app/api/v1/scan.py` and `app/api/v1/audit.py` own their respective Pydantic response shapes. Update the matching TypeScript type in `frontend/src/types/scan.ts`, `vscode-extension/src/types.ts`, and the Rust structs in `cli/src/types.rs` in the same change.

---

## 3. Database (`/backend/app/models`, `/backend/app/db`)

**Stack:** SQLAlchemy 2.0 async (declarative `Base`, no ORM abstraction layer like SQLModel) · `aiosqlite` (local/managed installs) · `asyncpg` + pgvector (production). There is **no Alembic** in this codebase — SQLite schemas are created via `Base.metadata.create_all` plus a small hand-written additive migration list in `app/db/session.py::_sqlite_migrate`; PostgreSQL uses the plain SQL in `backend/migrations/init.sql`.

### Schema Overview

| Model file | Table | Notes |
|---|---|---|
| `models/scans.py` | `scans` | One row per `/api/v1/scan` request |
| `models/audit_runs.py` | `audit_runs` | One row per `kshield agent` run — file/finding/severity counts, read by `org-audit.sh` |
| `models/vulnerabilities.py` | `vulnerabilities` | Finding rows; carries a `Vector(1536)` embedding |
| `models/false_positives.py` | `false_positives` | Global rule suppressions (`file_signature="*"`) and quiet-office signature dismissals (`signature` column) |
| `models/configurations.py` | `configurations` | Key/value store — currently used only for `pattern_archive.py`'s extra auth keywords |

### Extension Rules

- **The 1536-dim embedding is not semantically meaningful today.** `model.py::generate_embedding_vector` seeds a random vector from an MD5 hash of the finding's description text — it is deterministic (same text → same vector) but carries no real semantic signal, so any cosine-similarity feature built on `vulnerabilities.embedding` today is comparing structured noise. If you build a real semantic-search feature, replace this generator first; don't assume the column already holds something meaningful.
- **Vector dimension is fixed at 1536.** If you do wire up a real embedding source, update `Vector(1536)` in `models/vulnerabilities.py` **and** `migrations/init.sql` together.
- **SQLite additive changes**: add new `ALTER TABLE` statements to `_sqlite_migrate`'s list in `app/db/session.py` — they run inside a `try/except: pass` so they're safe to re-run against an already-migrated DB.

---

## 4. React Dashboard + Tauri (`/frontend`, `/src-tauri`)

**Stack:** Vite · React 19 · TypeScript · Tailwind CSS v4 · Tauri 2

The dashboard is a real client of the live backend, not a mock — `frontend/src/api/client.ts` calls `GET /api/v1/scans`, `GET /api/v1/telemetry`, `POST /api/v1/suppress`, `POST /api/v1/apply-patch` against `http://localhost:8000`.

### File Responsibilities

| File | Owns |
|---|---|
| `src/App.tsx` | Root layout, view routing |
| `src/components/Dashboard.tsx` | Main scan-history view, polling (`fetchData`), toast state, patch-apply flow |
| `src/components/Settings.tsx` | Backend URL + rule configuration UI |
| `src/components/Docs.tsx` | In-app "How to Use" — User Guide + API Reference tabs |
| `src/design-system/` | Token file + component library (`Badge`, `Button`, `Card`, `CodeBlock`, `Drawer`, etc.) |
| `src-tauri/src/main.rs` | Tauri commands, IPC bridge (desktop packaging is not yet finished — see README roadmap) |

### Extension Rules

- **All OS-level operations** (file I/O, process spawning) must go through a Tauri command in `src-tauri/src/main.rs`, invoked via `invoke()` from `@tauri-apps/api/core`. Never call Node.js APIs or shell exec from the React layer.
- **Styling**: use the design-system tokens in `src/design-system/tokens.ts`, not raw hex values, so light/dark theming stays consistent between the browser and the Tauri window.
- **Adding a new dashboard panel**: create a component in `src/components/`, wire it into `App.tsx`, add a nav entry in `src/components/Sidebar.tsx`.
- **Adding a new backend call**: add it to `src/api/client.ts`'s `api` object — every dashboard data fetch goes through that one file, not ad-hoc `fetch()` calls scattered across components.

---

## 5. GitHub Actions CI Pipeline (`.github/workflows/ci.yml`)

**Trigger:** `push` to `dev`, `pull_request` targeting `dev`/`master`.

### What it actually does

Four independent jobs — `cli` (cargo build + test), `backend` (pip install, an import-sanity check, `pytest`), `frontend` (`tsc --noEmit` + `npm run build`), `vscode-extension` (`npm run compile`) — plus a fifth, `pr-scan`, that only runs on pull requests:

1. Checks out the PR branch with full history (`fetch-depth: 0`).
2. Computes `git diff --name-only origin/<base>...HEAD`, filtered to real files (excludes lockfiles).
3. Starts the backend (`SQLITE_FALLBACK=true uvicorn`) directly on the runner — no self-hosted infrastructure, no Docker.
4. For each changed file, `POST`s it to `http://127.0.0.1:8000/api/v1/scan` and collects `.anomalies`.
5. Posts one PR review via `actions/github-script` + `github.rest.pulls.createReview`, with one inline comment per finding.

There is a separate `release.yml` (tag-triggered multi-platform binary + PyPI build), `deploy-pages.yml` (frontend → GitHub Pages), and `codeql.yml` (weekly + push/PR static analysis, scoped to `python` and `javascript-typescript` — CodeQL has no Rust support, so the CLI's only coverage is `cargo build`/`cargo test` in `ci.yml`) — not covered in detail here.

### Extension Rules

- **The backend `import check` step in `ci.yml` explicitly imports from `app.engine.ksword` and `app.engine.orchestrator`.** If you rename or remove either module, this step breaks the whole `backend` job — update it in the same change (this exact class of bug is what broke the old `remediation.py` reference here before it was fixed).
- **Changing the backend URL for `pr-scan`**: the job starts its own backend on the runner; there is no `KSHIELD_BACKEND` secret to configure for CI today.
- **Adding a new language to the audit matrix**: extend `sandbox.py`/`dependency_audit.py` per §2, not this workflow file — `pr-scan` calls the generic `/api/v1/scan` endpoint and doesn't need per-language CI changes.

---

## 6. VS Code Extension (`/vscode-extension`)

**Stack:** TypeScript · VS Code Extension API · `@vscode/vsce`

### File Responsibilities

| File | Owns |
|---|---|
| `src/extension.ts` | Activation, save-watcher wiring, command registration |
| `src/apiClient.ts` | HTTP client for the local backend (`/health`, `/api/v1/scan`, `/api/v1/suppress`) |
| `src/diagnostics.ts` | Maps backend findings to `vscode.Diagnostic` objects |
| `src/hoverProvider.ts` | ELI5 explanation shown on hover over a squiggle |
| `src/codeActionProvider.ts` | Quick Fix actions — apply patch / suppress rule |
| `src/patch.ts` | Applies unified-diff `patch_diff` strings from remediation findings |
| `src/statusBar.ts` | Backend reachability indicator |
| `src/types.ts` | Mirrors the `/api/v1/scan` response contract — keep in lockstep with `cli/src/types.rs` and `frontend/src/types/scan.ts` |

### Extension Rules

- **The extension never bundles or starts the backend.** It only talks to it over HTTP at `kshield.backendUrl` (default `http://127.0.0.1:8000`). Process-spawning belongs to the CLI (`cli/src/setup.rs`).
- **Packaging**: `package.json` must keep a valid `repository` field and the package must ship with a `LICENSE` file (copied from the repo root) — `vsce package` treats both as required for a warning-free `.vsix`.
- **Auto-apply is patch-only, not type-specific.** `codeActionProvider.ts`'s apply-fix path should key off whether a finding's `remediation.patch_diff` is non-empty, not off a hardcoded list of finding types — ksword decides per-finding, per-file whether a safe patch exists (e.g. Broken Access Control now only gets a patch when a reusable guard exists elsewhere in the same file), and that decision can change file-to-file. All findings without a patch fall back to "Suppress This Rule".
- **Changing the finding schema**: if `app/api/v1/scan.py`'s response model changes, update `src/types.ts` in lockstep with `frontend/src/types/scan.ts` and `cli/src/types.rs`.

---

## 7. Integrity Invariants — Never Break These

| # | Rule |
|---|---|
| 1 | CLI must exit `1` on any unmitigated `CRITICAL` or `HIGH` finding, for both `hook`/`scan` and `agent`. |
| 2 | Internal engine findings use `{line_number, anomaly_type, severity, description, code_snippet}`; the `/api/v1/scan` and `/api/v1/audit` JSON response renames to `{line, type, severity, description, remediation}`. Changing either shape without updating the other breaks the CLI renderer, the dashboard, the VS Code extension, and the CI PR-comment poster simultaneously. |
| 3 | `ksword.py` must never return a non-empty `patch_diff` without having re-run the originating check against the patched content and confirmed the finding cleared. This is the one invariant that exists because it was broken before — do not regress it. |
| 4 | Registry sandbox checks (`sandbox.py`) must be cached per audit run via `registry_cache` — never issue two HTTP requests for the same package name within one `/api/v1/audit` call. |
| 5 | All OS-level calls from the frontend go through Tauri IPC — never direct Node.js/`fetch`-to-filesystem tricks. |
| 6 | Vector dimension is 1536 across the Python model and SQL schema — but see §3: this column is not currently populated with a real embedding, so don't build features that assume otherwise without fixing the generator first. |
