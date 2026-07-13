# AI Capabilities & System Architecture Blueprint

This document is the authoritative system manual for AI development agents (Claude Code, Cursor, Copilot) and human contributors to safely extend, modify, and optimise the **KShield** without introducing breaking structural changes.

---

## 1. Rust CLI & Terminal Engine (`/cli`)

**Stack:** Rust · Cargo · Ratatui · Crossterm · Reqwest · Tokio

### File Responsibilities

| File | Owns |
|---|---|
| `src/main.rs` | Entry point, arg parsing, pre-commit hook exit-code chain |
| `src/ui.rs` | All Ratatui draw calls, layout constraints, colour palette |
| `src/scanner.rs` | Git staging ingress (`git diff --cached`), file chunking |
| `src/http.rs` | Non-blocking Reqwest calls to backend on `http://localhost:8000` |

### Extension Rules

- **Adding a new terminal screen**: add a new `render_*` function in `src/ui.rs` using `ratatui::layout::Constraint` arrays. Never hard-code pixel sizes — use percentage or min/max constraints so compact terminals don't clip.
- **Changing exit behaviour**: the hook **must exit `1`** when any `CRITICAL` or `HIGH` finding is unmitigated. The exit-code chain lives in `src/main.rs`. Do not swallow errors silently.
- **HTTP timeouts**: `src/http.rs` enforces a 5-second connect timeout and 30-second read timeout via `reqwest::ClientBuilder`. Do not raise these — CI runners must not hang on an unavailable backend.
- **Adding a new diff view column**: update the column width ratio in the `Layout::default().constraints()` call inside `src/ui.rs`. Always keep left/right panes equal-width for the unified diff view.

---

## 2. Asynchronous FastAPI Core (`/backend/app`)

**Stack:** Python 3.12 · FastAPI · Asyncio · HTTPX · SQLAlchemy (async) · Pydantic v2

### File Responsibilities

| File | Owns |
|---|---|
| `app/main.py` | FastAPI app factory, lifespan handler, middleware |
| `app/api/v1/scan.py` | POST `/v1/scan` route — orchestrates all engine calls |
| `app/engine/ast_rules.py` | Python AST visitor rules |
| `app/engine/entropy.py` | Regex patterns + Shannon entropy scanner |
| `app/engine/sandbox.py` | Async PyPI / npm registry verification |
| `app/engine/remediation.py` | Unified diff patch builder + ELI5 text generator |
| `app/engine/model.py` | Local TensorFlow token classifier |
| `app/db/session.py` | Async SQLAlchemy engine + session factory |

### Extension Rules

**Adding a new AST rule**
1. Open `app/engine/ast_rules.py`.
2. Subclass `ast.NodeVisitor`.
3. Your `visit_*` method must `append` to `self.findings` using exactly this schema:
   ```python
   {"line": int, "type": str, "severity": str, "description": str}
   ```
   Valid `severity` values: `"CRITICAL"` · `"HIGH"` · `"MEDIUM"` · `"LOW"` · `"INFO"`
4. Register the visitor in the `run_ast_checks(source: str)` coordinator function at the bottom of the file.

**Adding a new registry mirror (e.g., Cargo, RubyGems)**
1. Open `app/engine/sandbox.py`.
2. Add an async function that uses a shared `httpx.AsyncClient` (the module-level singleton).
3. Cache responses with the in-memory `TTLCache` using the package name as the key — never hit a registry twice for the same package in one scan session.
4. Return `{"package": str, "exists": bool, "registry": str}`.

**Changing the scan route response shape**
- The Pydantic response model is defined in `app/api/v1/scan.py`. Update it there, then update the matching TypeScript type in `frontend/src/types/scan.ts` and the Rust struct in `cli/src/http.rs`.

---

## 3. Database Vector Topology (`/backend/app/models`, PostgreSQL + pgvector)

**Stack:** PostgreSQL 16 · pgvector · asyncpg · SQLModel · Alembic

### Schema Overview

| Model file | Table | Notes |
|---|---|---|
| `models/scans.py` | `scans` | One row per scan request, links to N vulnerabilities |
| `models/vulnerabilities.py` | `vulnerabilities` | Finding rows; carries 1536-dim vector embedding |
| `models/false_positives.py` | `false_positives` | Developer-confirmed FP overrides |
| `models/configurations.py` | `configurations` | Per-repo rule enable/disable flags |

### Extension Rules

- **Vector dimension is fixed at 1536.** If you swap the embedding source (e.g., replace the local model with an external LLM), you must update the `Vector(1536)` column type in `models/vulnerabilities.py` **and** the `init.sql` column definition to the new dimension before running migrations.
- **Cosine similarity queries** must use the SQLAlchemy vector operator wrapper, not raw SQL strings:
  ```python
  # Correct
  stmt = select(Vulnerability).order_by(Vulnerability.embedding.cosine_distance(query_vec)).limit(5)
  # Wrong — breaks portability
  stmt = text("SELECT * FROM vulnerabilities ORDER BY embedding <=> :v LIMIT 5")
  ```
- **Telemetry pipeline**: The optional anonymised telemetry serialiser lives in `app/engine/telemetry.py`. It strips file paths and repo identifiers before serialising. Never add fields that could leak user identity. The pipeline is opt-in via `TELEMETRY_ENABLED=true` env var.

---

## 4. Tauri + React Dashboard (`/frontend`)

**Stack:** Vite · React 18 · TypeScript · Tailwind CSS · Tauri v2

### File Responsibilities

| File | Owns |
|---|---|
| `src/App.tsx` | Root router, global providers |
| `src/components/Dashboard.tsx` | Main scan results view |
| `src/components/Settings.tsx` | Rule configuration UI |
| `src-tauri/src/main.rs` | Tauri commands, IPC bridge |
| `src-tauri/tauri.conf.json` | Window config, allowed domains, CSP |

### Extension Rules

- **All OS-level operations** (file I/O, process spawning) must go through a Tauri command declared in `src-tauri/src/main.rs` and invoked via `invoke()` from `@tauri-apps/api/core`. Never call Node.js APIs or shell exec from the React layer.
- **API keys and secrets** must never appear in the frontend bundle. Any backend URL override goes in the Tauri `allowlist` config — not in a `.env` file committed to the repo.
- **Theme**: The colour system is defined in `tailwind.config.js` under the `dark` variant. All new components must use CSS variable tokens (`bg-surface`, `text-primary`, etc.) — never hardcode hex values. This keeps both the browser and the Tauri window frame visually consistent.
- **Adding a new dashboard panel**: create a component in `src/components/`, register a route in `App.tsx`, and add a nav entry in `src/components/Sidebar.tsx`. Do not break the existing route structure.

---

## 5. GitHub Actions CI Pipeline (`.github/workflows/kshield-ci.yml`)

**Trigger:** `pull_request` on `main` and `develop`

### What it does

1. Checks out the PR branch.
2. Identifies changed files using `git diff --name-only origin/main...HEAD`.
3. Sends the changed file payloads to a self-hosted runner running the Docker stack.
4. Receives structured findings JSON from the backend.
5. Posts inline PR review comments via the GitHub REST API (`POST /repos/{owner}/{repo}/pulls/{pull_number}/reviews`).

### Extension Rules

- **Adding a new severity label**: update the `SEVERITY_EMOJI` map inside the workflow's inline Python script, then update the matching constant in `cli/src/main.rs` to keep exit-code behaviour aligned.
- **Changing the backend URL**: set the `KSHIELD_BACKEND` repository secret — never hard-code the host in the YAML file.
- **Matrix builds** (multi-language repos): extend the `strategy.matrix.language` array and add a corresponding `if:` condition guard on the relevant scan step.

---

## 6. Integrity Invariants — Never Break These

| # | Rule |
|---|---|
| 1 | CLI must exit `1` on any unmitigated `CRITICAL` or `HIGH` finding. |
| 2 | Vector dimension is 1536 across Python model, SQL schema, and any external embedding provider. |
| 3 | Registry sandbox must cache per-session — never make two HTTP requests for the same package name. |
| 4 | All OS calls from the frontend go through Tauri IPC — never direct. |
| 5 | AST rule output schema `{line, type, severity, description}` is the contract between engine and API; changing it breaks the CLI renderer and the GitHub annotation poster simultaneously. |
| 6 | Telemetry serialiser must strip all path and identity fields before transmission. |
