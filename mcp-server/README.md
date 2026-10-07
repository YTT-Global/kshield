# kshield MCP server

Exposes the local kshield backend as MCP tools, so any MCP-aware agent
(Claude Code, Claude Desktop) can run kshield's checks directly — scan a
file, run a repo-wide audit, apply a remediation patch — without shelling
out to the CLI.

This is a thin client, same as the Rust CLI: it talks to the same local
FastAPI backend over HTTP (`KSHIELD_BACKEND`, default
`http://127.0.0.1:8000`). It does no scanning of its own. **Start the
backend first** — `kshield start`, or `uvicorn app.main:app` from
`backend/`.

## Tools

| Tool | What it does |
|---|---|
| `kshield_health` | Check the backend is reachable — call this first |
| `kshield_scan_file(path)` | Scan one file on disk |
| `kshield_audit_repo(repo_path)` | Repo-wide audit — every git-tracked file, graph-aware cross-file checks |
| `kshield_list_scan_history(limit)` | Recent single-file scans |
| `kshield_list_audit_runs` | Past repo-wide audits, most-critical-first |
| `kshield_dismiss_finding(description, anomaly_type, justification)` | Mark a finding as a false positive |
| `kshield_apply_patch(vulnerability_id)` | **Writes to disk** — applies the auto-generated patch via `git apply` |
| `kshield_list_suppressed_rules` | List globally suppressed rule types |
| `kshield_suppress_rule(rule_type, justification)` | Globally suppress a rule type |
| `kshield_unsuppress_rule(rule_type)` | Remove a suppression |

Not yet exposed: the `/patterns/auth-keywords` pattern-archive endpoints —
natural next addition, left out of this first pass to keep the tool surface
focused.

## Running it standalone (smoke test)

`server.py` declares its own deps via PEP 723 inline metadata, so `uv run
server.py` *should* just work — but if you're running it from inside the
kshield repo, uv's project auto-detection picks up kshield's own
`pyproject.toml` instead of the script's inline block and the import fails
with `ModuleNotFoundError: No module named 'mcp.server.fastmcp'`. Verified
fix: pass `--no-project` and spell the deps out explicitly:

```bash
uv run --no-project --with "mcp[cli]>=1.2.0" --with "httpx>=0.27" \
  python3 mcp-server/server.py
```

Plain `pip`/`venv` works too if you'd rather not deal with the uv quirk
above:

```bash
cd mcp-server
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python3 server.py
```

Either way it just sits there waiting on stdio — that's correct, it's meant
to be launched by an MCP client, not run interactively.

## Registering with Claude Code

```bash
claude mcp add kshield -- uv run --no-project \
  --with "mcp[cli]>=1.2.0" --with "httpx>=0.27" \
  python3 /Users/YTTGlobalServices/100-percent-code/kshield/mcp-server/server.py
```

(Swap the `uv run ...` command for the venv's `python3 server.py` if you set
up via pip instead.)

## Verified

`kshield_health` and `kshield_scan_file` were tested end-to-end against a
live local backend (2026-08-04) — correctly detected a hardcoded AWS key in
a test file and returned a working auto-generated remediation patch. The
remaining tools are thin, direct passthroughs to already-tested backend
endpoints (see `backend/app/api/v1/`) but weren't each individually
exercised through this MCP layer yet.
