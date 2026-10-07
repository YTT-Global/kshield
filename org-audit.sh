#!/usr/bin/env bash
# Org-wide KShield audit: clones every repo in an org and runs `kshield agent <name>`
# against each one. Per-run summaries land in the local audit_runs table, so the
# final report is read from there rather than parsed out of terminal output.
set -uo pipefail

ORG="${1:?Usage: ./org-audit.sh <org-name>}"
WORKDIR="$HOME/audits/$(date +%F)"
RESULTS="$WORKDIR/results"
mkdir -p "$RESULTS"
cd "$WORKDIR"

kshield start >/dev/null 2>&1 || true

# 1. Inventory non-archived repos
gh repo list "$ORG" --limit 1000 --json name,url,isArchived \
  | jq -r '.[] | select(.isArchived==false) | .url' > repo_urls.txt

echo "Found $(wc -l < repo_urls.txt) repos to audit."

# 2. Clone them in parallel (skip ones already cloned from a prior run)
# -a reads the file directly, but that's GNU-only — BSD xargs (macOS default)
# doesn't support it, so feed the list via stdin instead for portability.
xargs -P 8 -I{} sh -c '
  name=$(basename "{}" .git)
  [ -d "$name" ] || git clone --depth 1 --quiet "{}" "$name"
' < repo_urls.txt

# 3. Run kshield agent <repo-name> per repo
run_names=()
for repo in */; do
  name="${repo%/}"
  [ -d "$repo/.git" ] || continue
  (
    cd "$repo"
    kshield init >/dev/null 2>&1 || true
    kshield agent "$name" > "$RESULTS/${name}.log" 2>&1
  )
  status=$?
  run_names+=("$name")
  if [ "$status" -gt 1 ]; then
    echo "FAILED to audit: $name (exit $status) — see $RESULTS/${name}.log"
  else
    echo "audited: $name"
  fi
done

# 4. Pull the summary for exactly these run names from audit_runs
python3 - "${run_names[@]}" <<'PY'
import sqlite3, sys
from pathlib import Path

names = sys.argv[1:]
db_path = Path.home() / ".kshield" / "kshield.db"
conn = sqlite3.connect(db_path)
placeholders = ",".join("?" * len(names))
rows = conn.execute(
    f"""
    SELECT name, file_count, findings_count, critical_count, high_count
    FROM audit_runs
    WHERE name IN ({placeholders})
    GROUP BY name
    HAVING created_at = MAX(created_at)
    """,
    names,
).fetchall()

print()
print("── Audit summary ──────────────────────────────")
print(f"{'REPO':<30}{'FILES':<8}{'FINDINGS':<10}{'CRITICAL':<10}{'HIGH':<6}")
flagged = 0
for name, files, findings, critical, high in sorted(rows, key=lambda r: -(r[3] + r[4])):
    if critical or high:
        flagged += 1
    print(f"{name:<30}{files:<8}{findings:<10}{critical:<10}{high:<6}")
print("────────────────────────────────────────────────")
print(f"{flagged} of {len(rows)} repo(s) have CRITICAL or HIGH findings.")
PY
