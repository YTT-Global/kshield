# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "mcp[cli]>=1.2.0",
#     "httpx>=0.27",
# ]
# ///
"""kshield MCP server.

Exposes the local kshield backend's scan/audit engine as MCP tools, so any
MCP-aware agent (Claude Code, Claude Desktop, etc.) can run kshield's checks
directly instead of shelling out to the CLI.

Talks to the same local FastAPI backend the Rust CLI and desktop app use —
same KSHIELD_BACKEND env var, same default http://127.0.0.1:8000. This
server does no scanning itself; it's a thin MCP-shaped client, matching
kshield's existing "one local backend, many local clients" architecture.

Requires the backend running first: `kshield start` (or, from backend/,
`uvicorn app.main:app`).
"""

import os
import subprocess
from pathlib import Path

import httpx
from mcp.server.fastmcp import FastMCP

BACKEND_URL = os.environ.get("KSHIELD_BACKEND", "http://127.0.0.1:8000")

mcp = FastMCP("kshield")


def _client() -> httpx.AsyncClient:
    return httpx.AsyncClient(base_url=BACKEND_URL, timeout=60.0)


def _git_tracked_files(repo_path: str) -> list[str]:
    """Mirrors the CLI's `Agent` command: every git-tracked file in the repo."""
    result = subprocess.run(
        ["git", "-C", repo_path, "ls-files"],
        capture_output=True,
        text=True,
        check=True,
    )
    return [line for line in result.stdout.splitlines() if line]


@mcp.tool()
async def kshield_health() -> dict:
    """Check whether the local kshield backend is reachable. Call this first —
    if it reports unreachable, tell the user to run `kshield start` before
    anything else."""
    async with _client() as client:
        try:
            resp = await client.get("/health", timeout=5.0)
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPError as e:
            return {"status": "unreachable", "backend_url": BACKEND_URL, "error": str(e)}


@mcp.tool()
async def kshield_scan_file(path: str, commit_sha: str | None = None) -> dict:
    """Scan a single file on disk for secrets, broken access control, and
    AI-hallucinated dependencies/APIs. `path` is a filesystem path readable
    by this server. Returns findings with severity and an auto-generated
    remediation patch per finding, where one exists."""
    file_path = Path(path).expanduser().resolve()
    if not file_path.is_file():
        return {"error": f"No such file: {file_path}"}
    content = file_path.read_text(errors="replace")
    async with _client() as client:
        resp = await client.post(
            "/api/v1/scan",
            json={
                "filename": str(file_path),
                "content": content,
                "commit_sha": commit_sha,
            },
        )
        resp.raise_for_status()
        return resp.json()


@mcp.tool()
async def kshield_audit_repo(repo_path: str, name: str | None = None) -> dict:
    """Repo-wide audit: scans every git-tracked file in `repo_path` at once,
    with graph-aware cross-file access-control checks (not just single-file
    rules). This is kshield's deepest check — use it before a release or when
    reviewing a large diff, not for a quick single-file check (use
    kshield_scan_file for that). Can take a while on large repos."""
    repo = Path(repo_path).expanduser().resolve()
    if not repo.is_dir():
        return {"error": f"No such directory: {repo}"}
    try:
        tracked = _git_tracked_files(str(repo))
    except subprocess.CalledProcessError as e:
        return {"error": f"Not a git repository, or git ls-files failed: {e}"}

    files = []
    for rel_path in tracked:
        full = repo / rel_path
        if not full.is_file():
            continue
        try:
            content = full.read_text(errors="replace")
        except (UnicodeDecodeError, OSError):
            continue
        files.append({"filename": rel_path, "content": content})

    async with _client() as client:
        resp = await client.post(
            "/api/v1/audit",
            json={"name": name or repo.name, "files": files},
        )
        resp.raise_for_status()
        return resp.json()


@mcp.tool()
async def kshield_list_audit_runs() -> dict:
    """List every past repo-wide audit run, most-critical-first."""
    async with _client() as client:
        resp = await client.get("/api/v1/audit/runs")
        resp.raise_for_status()
        return resp.json()


@mcp.tool()
async def kshield_list_scan_history(limit: int = 50) -> dict:
    """List recent single-file scans and their findings."""
    async with _client() as client:
        resp = await client.get("/api/v1/scans", params={"limit": limit})
        resp.raise_for_status()
        return resp.json()


@mcp.tool()
async def kshield_dismiss_finding(
    description: str, anomaly_type: str, justification: str = ""
) -> dict:
    """Mark a specific finding as a false positive. Future findings with a
    closely matching description and the same anomaly_type get auto-quieted
    instead of re-flagged. Use this when a flagged pattern is confirmed safe
    — not to silence something that hasn't actually been checked."""
    async with _client() as client:
        resp = await client.post(
            "/api/v1/audit/dismiss-finding",
            json={
                "description": description,
                "anomaly_type": anomaly_type,
                "justification": justification,
            },
        )
        resp.raise_for_status()
        return resp.json()


@mcp.tool()
async def kshield_apply_patch(vulnerability_id: str) -> dict:
    """Apply the auto-generated remediation patch for a specific finding
    directly to the file on disk via `git apply`. This WRITES to the
    filesystem — only call it after showing the user the finding and patch,
    or when they've explicitly asked to auto-fix. Returns patch_only if the
    file can't be found or the patch can't be applied cleanly; surface the
    raw diff in that case instead of failing silently."""
    async with _client() as client:
        resp = await client.post(
            "/api/v1/apply-patch", json={"vulnerability_id": vulnerability_id}
        )
        resp.raise_for_status()
        return resp.json()


@mcp.tool()
async def kshield_list_suppressed_rules() -> dict:
    """List every globally suppressed rule type, with justification."""
    async with _client() as client:
        resp = await client.get("/api/v1/suppress")
        resp.raise_for_status()
        return {"suppressed": resp.json()}


@mcp.tool()
async def kshield_suppress_rule(rule_type: str, justification: str = "") -> dict:
    """Globally suppress a rule type across all future scans on this backend
    instance. Idempotent. Use sparingly — this silences the rule everywhere,
    not just for one file."""
    async with _client() as client:
        resp = await client.post(
            "/api/v1/suppress",
            json={"rule_type": rule_type, "justification": justification},
        )
        resp.raise_for_status()
        return resp.json()


@mcp.tool()
async def kshield_unsuppress_rule(rule_type: str) -> dict:
    """Remove a global rule suppression, re-enabling that check for future
    scans."""
    async with _client() as client:
        resp = await client.delete(f"/api/v1/suppress/{rule_type}")
        resp.raise_for_status()
        return resp.json()


if __name__ == "__main__":
    mcp.run()
