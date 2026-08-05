# KShield — Feature Reference

A complete, accurate account of what KShield actually does today. Unlike the README (which sells it), this document is meant to be checked against — every claim here has been verified live against a running backend, not just read from source. Where something is a known gap rather than a feature, it's listed as one; see [Known Limitations](#known-limitations).

For the system diagrams behind these features, see [architecture.md](architecture.md). For the actual math behind each detector — formulas, thresholds, complexity — see [algorithms.md](algorithms.md).

---

## Two scanning pipelines

KShield has two genuinely different entry points, not one feature with two names:

| | Single-file scan | Repo-wide audit |
|---|---|---|
| Triggered by | `kshield hook` (every `git commit`), `kshield scan <file>` | `kshield agent <name>` |
| Backend endpoint | `POST /api/v1/scan` | `POST /api/v1/audit` |
| Scope | One file (or the staged diff) | Every git-tracked file, in one pass |
| Access-control engine | `ast_rules.py` — simple, no cross-file context | `access_control.py` — graph-aware, reuses guards proven elsewhere in the repo |
| Typosquat / undeclared-dependency checks | Not available | Available (`dependency_audit.py`) |
| False-positive memory | Not applied | Applied (`quiet_office.py` + `pattern_archive.py`) |

Both pipelines feed the same remediation agent (`ksword.py`) and the same finding schema, so CLI/dashboard/VS Code rendering is identical either way.

---

## Detection capabilities

### Hardcoded Secrets — CRITICAL
30+ named token signatures (GitHub, AWS, Google, Stripe, SendGrid, Twilio, Slack, Discord, npm, PyPI, HuggingFace, OpenAI, Anthropic, private key blocks, and a generic `api_key = "..."`-shaped catch-all), plus a Shannon-entropy fallback (score > 4.8, length ≥ 24) for anything that doesn't match a named pattern. UUIDs, MD5/SHA-1/SHA-256/SHA-512 hex, semver strings, and short base64 are allowlisted. **Language-agnostic** — this works on any text file, not just Python.

### Broken Access Control — MEDIUM / HIGH / CRITICAL
**Python/FastAPI only.** Flags route handlers with no `Depends()`/`Security()` guard, in either the function signature or the decorator's `dependencies=[...]`. Severity: GET → MEDIUM, mutating methods → HIGH, escalated one step further if the path touches something sensitive (`/admin`, `/payment`, `/billing`, etc.). Public paths (`/health`, `/docs`, `/metrics`, ...) are exempt. The graph-aware version (repo-wide audit only) also recognizes inline signature/HMAC verification in a handler's body as a valid guard shape, for webhook-style routes that can never carry a logged-in-user dependency.

**Verified against a real non-Python codebase (a production Fastify payments API) that this does not extend to JS/TS at all today** — see [Known Limitations](#known-limitations).

### AI Structural Hallucination — LOW / MEDIUM / HIGH
Regex-pattern matching (not a trained model, despite `tensorflow` having once been listed as a dependency — it was never imported and has since been removed) across five categories: placeholder markers, credential stubs, hallucinated/mock imports, AI-generation artifacts ("as an AI, I cannot..."), and dead-code stubs (bare `raise NotImplementedError`, trailing `...`). Test files are exempt.

### Dependency Hallucination — CRITICAL
Verifies every import against the real package registry: PyPI, npm, the Go module proxy, RubyGems. Standard-library modules are skipped. Registry timeouts fail open (never blocks a commit on a network hiccup). Known name-mismatches (`yaml`→`PyYAML`, `cv2`→`opencv-python`, etc.) are handled so real packages published under a different import name aren't misflagged.

### Possible Typosquat — HIGH / CRITICAL *(repo-wide audit only)*
Levenshtein-distance check against a curated list of well-known Python/npm packages. An import within edit-distance 2 of a popular name, and not independently verified as its own real package, gets flagged — distance 1 is CRITICAL, distance 2 is HIGH.

### Undeclared Dependency — LOW *(repo-wide audit only)*
An import that isn't in `requirements.txt`/`pyproject.toml`/`package.json` and isn't stdlib, first-party, or a known-popular name. No remediation offered — only the developer can say whether it should be added to a manifest.

### Syntax Violation — MEDIUM
Files that fail to parse are flagged directly — often the signature of AI-generated code truncated mid-edit.

---

## Verified auto-remediation (ksword)

Not a template engine and not an LLM. Every strategy runs a strict loop: **propose a fix → apply it in-memory → re-run the exact check that raised the finding against the patched result → only return the diff if that re-check confirms the finding actually cleared.** No network calls, no model inference — every decision comes from the target file's own AST or text.

| Finding type | What it does |
|---|---|
| Hardcoded Secret / High Entropy Credential | Extracts the literal to `os.getenv("VAR_NAME")`, adding `import os` if missing |
| Broken Access Control | Reuses a `Depends()`/`Security()` guard **already proven to work elsewhere in the same file** — never invents a guard name. Declines if nothing real exists to reuse. |
| Possible Typosquat | Corrects the import to the well-known name already identified by the typosquat check |
| Dependency Hallucination | No patch — offers a "closest well-known name" suggestion instead, since a rule engine can't safely guess the real package |
| Syntax Violation / AI Structural Hallucination / Undeclared Dependency | Explanation only, by design — these require human judgment or the original intent, which a rule engine can't recover |

Every returned `patch_diff` has been proven to `git apply` cleanly and to clear the finding on re-scan — this was not always true (see CHANGELOG for the three-bug chain that made `apply-patch` non-functional until fixed this cycle) but is now verified live end-to-end.

---

## False-positive memory *(repo-wide audit only)*

- **Quiet Office** (`quiet_office.py`): dismiss a finding once (`POST /api/v1/audit/dismiss-finding`) and its normalized signature (quoted identifiers and file paths stripped) is remembered — matching future findings of the same type are auto-suppressed, not just the one exact string.
- **Pattern Archive** (`pattern_archive.py`): teach a project-specific auth-guard name (`POST /api/v1/patterns/auth-keywords`, e.g. `verify_org_membership`) once, and every future audit recognizes it as a real guard — persists across runs via the `configurations` table.

---

## Repo-wide and org-wide audit

- `kshield agent <name>` — scans every git-tracked file in the current repo in one pass, regardless of which subdirectory it's invoked from. Builds a full repo graph (imports, symbols, every route + its guards, parse errors) before any check runs, so access-control checks understand what's genuinely reachable rather than judging one file in isolation.
- `org-audit.sh` — clones every non-archived repo in a GitHub org (via the `gh` CLI) and runs `kshield agent` against each one in parallel, reporting a ranked summary (by CRITICAL/HIGH count) read back from the local `audit_runs` table.
- Every audit run is persisted with file/finding/severity counts (`GET /api/v1/audit/runs`).

---

## Interfaces

- **Rust CLI** (`kshield`) — `init`, `setup`, `start`, `stop`, `status`, `hook`, `scan <file>`, `agent <name>`. Plain ANSI terminal output, no TUI framework.
- **React Dashboard** — scan/audit history, filter chips (severity), slide-over finding detail, one-click patch apply with toast notifications, rule suppression, light/dark theme. Genuinely wired to the live backend (`frontend/src/api/client.ts`), not mock data. A separate public Landing page (zero backend calls) is what actually deploys to GitHub Pages; the live Dashboard only lives behind `/kshield-dashboard/*`.
- **VS Code Extension** — inline diagnostics on save (debounced), hover explanations, Quick Fix actions (apply patch / suppress rule), status-bar backend health.
- **Tauri desktop wrapper** — packages the dashboard as a native window. Packaging itself is not finished (see Known Limitations).
- **GitHub Actions PR scanning** (`ci.yml`, `pr-scan` job) — posts inline PR review comments for changed files. Currently calls the single-file `/api/v1/scan` endpoint per file, not the graph-aware `/api/v1/audit` — see Known Limitations.

---

## Install paths

`curl | bash`, `brew install ytt-global/tap/kshield`, `npx @ytt-global/kshield init`, `pip install kshield` — all four resolve to the same Rust binary and the same experience. `SQLITE_FALLBACK=true` runs entirely on a local SQLite DB (`~/.kshield/kshield.db`) with no Docker needed; a `docker-compose.yml` is available for a shared PostgreSQL + pgvector deployment.

---

## Known Limitations

Listed here deliberately, not buried — these are the gaps that matter most for deciding whether to trust a result:

- **No JS/TS (or any non-Python) access-control detection.** Verified directly against a real production Fastify API: genuine routes with real auth middleware produced zero findings, not because the code is safe, but because the engine can't see it. Secrets and dependency-hallucination checks are language-agnostic and do work on any language; broken-access-control detection does not. A clean `kshield agent` result on a non-Python codebase does not mean "no access-control issues" today.
- **No cross-repo/cross-service auth awareness.** Guard-reuse (both in detection and in `ksword`'s remediation) is scoped to what's visible in the single file or single repo being scanned — a shared auth dependency imported from a separate internal library won't be recognized unless its name happens to match the auth-keyword list.
- **Similarity search is not real yet.** The `vulnerabilities.embedding` pgvector column is populated with an MD5-seeded random vector, not a real embedding — any cosine-similarity feature built on it today would be comparing structured noise, not semantic meaning.
- **PR-scan CI doesn't use the stronger engine.** `ci.yml`'s `pr-scan` job calls per-file `/api/v1/scan`, missing the cross-file guard-reuse and sensitive-path escalation that `/api/v1/audit` (and therefore `kshield agent`) has.
- **No Windows support.** No Rust unit tests either — CLI correctness currently relies entirely on manual/live verification, not an automated regression suite for `cli/`.
- **Tauri desktop packaging is unfinished.**
