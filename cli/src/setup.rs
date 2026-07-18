use anyhow::{bail, Result};
use std::path::PathBuf;
use std::process::{Command, Stdio};

// ── Paths ─────────────────────────────────────────────────────────────────────

pub fn kshield_dir() -> Result<PathBuf> {
    let home = std::env::var("HOME")
        .or_else(|_| std::env::var("USERPROFILE"))
        .map(PathBuf::from)
        .map_err(|_| anyhow::anyhow!("Could not determine home directory"))?;
    Ok(home.join(".kshield"))
}

pub fn venv_python(af_dir: &PathBuf) -> PathBuf {
    if cfg!(target_os = "windows") {
        af_dir.join("venv/Scripts/python.exe")
    } else {
        af_dir.join("venv/bin/python")
    }
}

/// Searches common locations for the Python backend directory.
pub fn find_backend_dir() -> Option<PathBuf> {
    let candidates: Vec<Option<PathBuf>> = vec![
        // ~/.kshield/backend  (managed install)
        kshield_dir().ok().map(|d| d.join("backend")),
        // Binary-relative: e.g. /usr/local/lib/kshield/backend
        std::env::current_exe()
            .ok()
            .and_then(|p| p.parent().map(|d| d.join("../backend"))),
        // Source tree (dev mode): ./backend relative to CWD
        Some(PathBuf::from("backend")),
        Some(PathBuf::from("./backend")),
    ];

    candidates
        .into_iter()
        .flatten()
        .find(|p| p.join("app/main.py").exists())
}

// ── Python detection ──────────────────────────────────────────────────────────

/// Returns the first Python 3.10+ executable found in PATH.
pub fn find_python() -> Option<String> {
    for candidate in ["python3.13", "python3.12", "python3.11", "python3.10", "python3", "python"] {
        if let Ok(out) = Command::new(candidate).arg("--version").output() {
            let ver = String::from_utf8_lossy(&out.stdout).to_string()
                + &String::from_utf8_lossy(&out.stderr);
            if out.status.success()
                && (ver.contains("3.10")
                    || ver.contains("3.11")
                    || ver.contains("3.12")
                    || ver.contains("3.13"))
            {
                return Some(candidate.to_string());
            }
        }
    }
    None
}

// ── Setup ─────────────────────────────────────────────────────────────────────

/// Full managed setup: creates ~/.kshield/, venv, and installs backend deps.
/// Returns the path to the backend directory.
pub async fn run_setup(verbose: bool) -> Result<PathBuf> {
    let af_dir = kshield_dir()?;
    std::fs::create_dir_all(&af_dir)?;

    // 1. Locate or download the backend Python code
    let backend_dir = if let Some(local) = find_backend_dir() {
        if verbose {
            println!("  Using backend at: {}", local.display());
        }
        local
    } else {
        let dest = af_dir.join("backend");
        if verbose {
            println!("  Downloading backend...");
        }
        download_backend(&dest).await?;
        dest
    };

    // 2. Create virtual environment if missing
    let venv_dir = af_dir.join("venv");
    if !venv_dir.exists() {
        let python = find_python().ok_or_else(|| {
            anyhow::anyhow!(
                "Python 3.10+ not found.\n  Install it from https://python.org and re-run."
            )
        })?;
        if verbose {
            println!("  Creating virtual environment with {python}...");
        }
        create_venv(&python, &venv_dir)?;
    }

    // 3. Install Python dependencies
    let reqs = backend_dir.join("requirements.txt");
    if reqs.exists() {
        if verbose {
            println!("  Installing Python dependencies...");
        }
        install_requirements(&venv_dir, &reqs)?;
    }

    Ok(backend_dir)
}

fn create_venv(python: &str, venv_dir: &PathBuf) -> Result<()> {
    let status = Command::new(python)
        .args(["-m", "venv", venv_dir.to_str().unwrap_or("~/.kshield/venv")])
        .stdout(Stdio::null())
        .stderr(Stdio::null())
        .status()?;
    if !status.success() {
        bail!("Failed to create virtual environment");
    }
    Ok(())
}

fn install_requirements(venv_dir: &PathBuf, reqs: &PathBuf) -> Result<()> {
    let pip = venv_dir.join(if cfg!(target_os = "windows") {
        "Scripts/pip"
    } else {
        "bin/pip"
    });

    let status = Command::new(&pip)
        .args(["install", "-q", "-r", reqs.to_str().unwrap_or("")])
        .stdout(Stdio::null())
        .stderr(Stdio::null())
        .status()?;

    if !status.success() {
        bail!("pip install failed. Check your Python environment.");
    }
    Ok(())
}

async fn download_backend(dest: &PathBuf) -> Result<()> {
    // Derive the release version from this binary's version
    let version = env!("CARGO_PKG_VERSION");
    let url = format!(
        "https://github.com/YTT-Global/kshield/releases/download/v{version}/backend.tar.gz"
    );

    let client = reqwest::Client::new();
    let response = client
        .get(&url)
        .timeout(std::time::Duration::from_secs(30))
        .send()
        .await
        .map_err(|e| anyhow::anyhow!("Download failed: {e}\n  Check: {url}"))?;

    if !response.status().is_success() {
        bail!(
            "Backend download returned HTTP {}\n  URL: {url}",
            response.status()
        );
    }

    let bytes = response.bytes().await?;
    let tmp = dest.parent().unwrap_or(dest).join("backend.tmp.tar.gz");
    std::fs::write(&tmp, &bytes)?;

    std::fs::create_dir_all(dest)?;
    let status = Command::new("tar")
        .args(["-xzf", tmp.to_str().unwrap_or(""), "-C", dest.to_str().unwrap_or("")])
        .status()?;

    std::fs::remove_file(&tmp).ok();

    if !status.success() {
        bail!("Failed to extract backend archive");
    }

    Ok(())
}

// ── Backend process management ────────────────────────────────────────────────

/// Spawns the FastAPI backend as a background process.
/// Uses the managed venv if available, falls back to system uvicorn.
pub fn start_backend_process(backend_dir: &PathBuf) -> std::io::Result<std::process::Child> {
    let af_dir = kshield_dir()
        .map_err(|e| std::io::Error::new(std::io::ErrorKind::Other, e.to_string()))?;
    let venv_py = venv_python(&af_dir);

    let log_path = af_dir.join("backend.log");
    let log_file = std::fs::File::create(&log_path)
        .unwrap_or_else(|_| std::fs::File::open("/dev/null").unwrap());

    let (program, args): (&str, &[&str]) = if venv_py.exists() {
        (
            venv_py.to_str().unwrap_or("python3"),
            &["-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8000"],
        )
    } else {
        ("uvicorn", &["app.main:app", "--host", "127.0.0.1", "--port", "8000"])
    };

    let child = Command::new(program)
        .args(args)
        .current_dir(backend_dir)
        .env("SQLITE_FALLBACK", "true")
        .stdout(log_file.try_clone().unwrap_or_else(|_| unsafe { std::mem::zeroed() }))
        .stderr(log_file)
        .spawn()?;

    // Save PID for later management
    let pid_path = af_dir.join("backend.pid");
    let _ = std::fs::write(&pid_path, child.id().to_string());

    Ok(child)
}

/// Returns true if a backend process started from a previous session is still running.
pub fn backend_pid_running() -> bool {
    let Ok(af_dir) = kshield_dir() else { return false };
    let pid_path = af_dir.join("backend.pid");
    let Ok(pid_str) = std::fs::read_to_string(&pid_path) else { return false };
    let pid = pid_str.trim().to_string();
    if pid.is_empty() { return false; }

    // `kill -0 <pid>` exits 0 if the process exists, non-zero otherwise
    Command::new("kill")
        .args(["-0", &pid])
        .stdout(Stdio::null())
        .stderr(Stdio::null())
        .status()
        .map(|s| s.success())
        .unwrap_or(false)
}
