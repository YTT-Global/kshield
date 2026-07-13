"""Entry point for `kshield-backend` CLI command installed via pip."""
import os
import subprocess
import sys
from pathlib import Path


def main() -> None:
    backend_dir = Path(__file__).parent.parent  # backend/

    host = os.getenv("KSHIELD_HOST", "127.0.0.1")
    port = os.getenv("KSHIELD_PORT", "8000")

    env = {
        **os.environ,
        "SQLITE_FALLBACK": os.getenv("SQLITE_FALLBACK", "true"),
    }

    print(f"Starting KShield backend on {host}:{port} (SQLite mode)...")
    print("Press Ctrl+C to stop.\n")

    try:
        subprocess.run(
            [
                sys.executable, "-m", "uvicorn",
                "app.main:app",
                "--host", host,
                "--port", port,
                "--reload",
            ],
            cwd=str(backend_dir),
            env=env,
            check=True,
        )
    except KeyboardInterrupt:
        print("\nBackend stopped.")
    except subprocess.CalledProcessError as e:
        sys.exit(e.returncode)


if __name__ == "__main__":
    main()
