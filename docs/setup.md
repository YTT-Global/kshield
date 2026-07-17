# Setup Guide

Complete instructions for running KShield — from first install through full production deployment.

---

## Prerequisites

| Tool | Minimum | Required for |
|---|---|---|
| macOS or Linux | — | Binary install (Windows not yet supported) |
| Python | 3.10 | Backend (auto-installed by `kshield setup`) |
| Node.js | 20 | Frontend development only |
| Rust | 1.78 | Building the CLI from source only |
| Docker | 24 | Production PostgreSQL only — not needed locally |

---

## Quick Install (Recommended)

```bash
curl -fsSL https://raw.githubusercontent.com/YTT-Global/kshield/main/install.sh | bash
```

Then inside any git repo:

```bash
kshield init
```

That's it. The backend is downloaded, a Python venv is created, the database is set up, and the pre-commit hook is installed — all automatically.

---

## All Install Methods

### curl | bash
```bash
curl -fsSL https://raw.githubusercontent.com/YTT-Global/kshield/main/install.sh | bash
```
Downloads a pre-built binary for your platform and installs it to `/usr/local/bin`.

### Homebrew (macOS)
```bash
brew install ytt-global/tap/kshield
```

### npx (Node.js)
```bash
npx kshield init
```
Downloads the platform binary on first run via the `kshield` npm package.

### pip (Python)
```bash
pip install kshield
kshield-backend &   # start backend in background
kshield init        # install git hook
```

### Build from source (Rust)
```bash
git clone https://github.com/YTT-Global/kshield.git
cd kshield/cli
cargo build --release
cp target/release/kshield /usr/local/bin/
```

---

## What `kshield init` Does

Run once inside each git repo you want to protect:

```
✓  Git repository detected
✓  Pre-commit hook installed  (.git/hooks/pre-commit)
✓  Python environment ready   (~/.kshield/venv)
✓  Backend started            (SQLite, no Docker needed)
✓  Ready. Make a commit to run your first scan.
```

Step by step:
1. Verifies the directory is a git repository
2. Writes `.git/hooks/pre-commit` (calls `kshield hook` on every commit)
3. Runs `kshield setup` if the Python backend isn't installed yet
4. Starts the backend via `kshield start`

---

## Managed Directory (`~/.kshield/`)

After `init`, everything lives in your home directory:

```
~/.kshield/
├── backend/        Python backend source (downloaded from GitHub release)
├── venv/           Isolated Python virtual environment
├── kshield.db     SQLite scan history database
├── backend.pid     PID of the running backend process
└── backend.log     Backend stdout / stderr logs
```

This directory is self-contained. Deleting it fully uninstalls the backend. The git hook and binary remain until removed manually.

---

## CLI Command Reference

```bash
kshield init              # Set up hook + backend in current repo
kshield setup             # Install Python backend into ~/.kshield/
kshield start             # Start the backend in the background
kshield stop              # Stop the background backend
kshield status            # Check backend health and hook status
kshield scan <file>       # Manually scan a single file
kshield hook              # Run pre-commit scan (called by git hook)
kshield --version         # Print CLI version
```

---

## Backend Management

### Start
```bash
kshield start
```
Starts the FastAPI backend as a background process. Writes PID to `~/.kshield/backend.pid`. Logs go to `~/.kshield/backend.log`.

### Stop
```bash
kshield stop
```

### Check status
```bash
kshield status

# KShield · Status
# ●  Backend   Running   http://127.0.0.1:8000
# ●  Git hook  Installed
```

### View logs
```bash
tail -f ~/.kshield/backend.log
```

### Change backend port
```bash
KSHIELD_BACKEND=http://127.0.0.1:9000 kshield status
```

---

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `KSHIELD_BACKEND` | `http://127.0.0.1:8000` | Backend URL used by the CLI |
| `SQLITE_FALLBACK` | `true` (managed install) | Use SQLite instead of PostgreSQL |
| `DATABASE_URL` | `sqlite+aiosqlite:///.../kshield.db` | Override database connection string |
| `CORS_ORIGINS` | `http://localhost:5173,http://localhost:3000` | Allowed origins for the API |
| `KSHIELD_VERSION` | latest | Pin version for `install.sh` |
| `KSHIELD_INSTALL_DIR` | `/usr/local/bin` | Override binary install location |

---

## Frontend (React Dashboard)

```bash
cd frontend
npm install
npm run dev
```

Open **http://localhost:5173**

The dashboard uses the same backend at `http://127.0.0.1:8000`. Make sure the backend is running (`kshield start`) before opening the dashboard.

---

## VS Code Extension

Inline diagnostics in the editor, powered by the same local backend. It does not bundle or start the backend — start it first (`kshield start`, or the manual `uvicorn` command above).

**Run from source (Extension Development Host):**
```bash
cd vscode-extension
npm install
npm run compile   # or npm run watch
```
Then open the folder in VS Code and press **F5** to launch a Development Host with the extension loaded.

**Install locally as a real extension (no Marketplace needed):**
```bash
cd vscode-extension
npx @vscode/vsce package                                # → kshield-vscode-<version>.vsix
code --install-extension kshield-vscode-<version>.vsix --force
```
Reload the VS Code window (**Developer: Reload Window**) to activate it.

**Publish to the Marketplace:**
```bash
npx @vscode/vsce login YTTGlobal
npx @vscode/vsce publish
```
Requires a publisher access token and the `repository` + `LICENSE` fields already present in `vscode-extension/package.json`.

---

## Production: Docker Compose + PostgreSQL

For team deployments with a shared PostgreSQL database:

```bash
# Start all services
docker compose up -d

# Services started:
#   PostgreSQL on port 5432  (with pgvector)
#   FastAPI backend on port 8000
#   Nginx frontend on port 3000
```

Point the CLI at the shared backend:
```bash
export KSHIELD_BACKEND=https://kshield.your-company.com
kshield init
```

---

## Uninstall

```bash
# Remove the binary
rm /usr/local/bin/kshield

# Remove managed backend and database
rm -rf ~/.kshield/

# Remove the hook from a specific repo
rm .git/hooks/pre-commit
```

---

## Troubleshooting

**`kshield: command not found`**
The binary is not in `PATH`. If you installed to `~/.local/bin`, add it:
```bash
export PATH="$HOME/.local/bin:$PATH"
```

**`Backend not running` warning on commit**
```bash
kshield start
# or, if setup was never run:
kshield setup && kshield start
```

**`Python 3.10+ not found`**
Install Python 3.11 from https://python.org, then re-run `kshield setup`.

**`pip install` fails inside the managed venv**
```bash
cat ~/.kshield/backend.log  # check for error details
rm -rf ~/.kshield/venv      # delete and recreate
kshield setup
```

**`pgvector` extension missing (PostgreSQL only)**
```sql
CREATE EXTENSION IF NOT EXISTS vector;
```
The Docker image includes it. Only needed when using a self-managed PostgreSQL.

**Frontend shows blank screen**
```bash
cd frontend && npm install && npm run build
# check browser console for errors
```

**Port already in use**
```bash
kshield stop            # stop managed backend
# or:
lsof -ti tcp:8000 | xargs kill -9
```
