mod config;
mod http;
mod scanner;
mod setup;
mod types;
mod ui;

use anyhow::Result;
use clap::{Parser, Subcommand};
use reqwest::Client;

#[derive(Parser)]
#[command(
    name = "kshield",
    version = env!("CARGO_PKG_VERSION"),
    about = "Local-first AI code review firewall.",
    long_about = "Catches secrets, broken access control, and AI hallucinations before they reach your main branch. Runs entirely on your machine — no data leaves your laptop."
)]
struct Cli {
    #[command(subcommand)]
    command: Commands,
}

#[derive(Subcommand)]
enum Commands {
    /// Set up KShield in the current git repository
    Init,
    /// Install Python backend into ~/.kshield/ (called automatically by init)
    Setup,
    /// Start the backend in the background
    Start,
    /// Stop the background backend
    Stop,
    /// Check backend and hook status
    Status,
    /// Run the pre-commit scan (called automatically by the git hook)
    Hook,
    /// Scan a specific file
    Scan {
        /// Path to the file to scan
        file: std::path::PathBuf,
    },
}

#[tokio::main]
async fn main() -> Result<()> {
    let cli = Cli::parse();
    match cli.command {
        Commands::Init   => cmd_init().await,
        Commands::Setup  => cmd_setup().await,
        Commands::Start  => cmd_start().await,
        Commands::Stop   => cmd_stop(),
        Commands::Status => cmd_status().await,
        Commands::Hook   => cmd_hook().await,
        Commands::Scan { file } => cmd_scan(file).await,
    }
}

// ── init ──────────────────────────────────────────────────────────────────────

async fn cmd_init() -> Result<()> {
    ui::print_init_header();

    // 1. Verify git repo
    let in_git = std::process::Command::new("git")
        .args(["rev-parse", "--git-dir"])
        .output()
        .map(|o| o.status.success())
        .unwrap_or(false);

    if !in_git {
        eprintln!("  Not a git repository. Run inside a git repo.");
        std::process::exit(1);
    }
    ui::print_init_step("Git repository detected");

    // 2. Install the git hook
    install_hook()?;
    ui::print_init_step("Pre-commit hook installed  (.git/hooks/pre-commit)");

    // 3. Check if backend is already running
    let client = Client::new();
    let mut backend_ok = http::health_check(&client).await;

    if !backend_ok {
        // 3a. Check if managed venv already exists → just start it
        let af_dir = setup::kshield_dir()?;
        let venv_py = setup::venv_python(&af_dir);
        let backend_dir = setup::find_backend_dir();

        if venv_py.exists() && backend_dir.is_some() {
            ui::print_init_step("Backend environment found — starting...");
            http::try_start_backend().await;
            backend_ok = http::health_check(&client).await;
        } else {
            // 3b. No environment — run full setup
            ui::print_init_warn("Backend not installed — running setup (one-time)...");
            match setup::run_setup(true).await {
                Ok(_) => {
                    ui::print_init_step("Python environment ready");
                    http::try_start_backend().await;
                    backend_ok = http::health_check(&client).await;
                }
                Err(e) => {
                    ui::print_init_warn(&format!("Setup could not complete: {e}"));
                    ui::print_init_warn("Run  kshield setup  manually after installing Python 3.10+");
                }
            }
        }
    } else {
        ui::print_init_step(&format!("Backend running at  {}", http::backend_url()));
    }

    ui::print_init_done(backend_ok);
    Ok(())
}

// ── setup ─────────────────────────────────────────────────────────────────────

async fn cmd_setup() -> Result<()> {
    println!();
    println!("\x1b[1m\x1b[36m  KShield  ·  Setup\x1b[0m");
    println!();

    match setup::run_setup(true).await {
        Ok(backend_dir) => {
            println!("  \x1b[32m✓\x1b[0m  Backend installed at: {}", backend_dir.display());
            println!();
            println!("  Start the backend with:  \x1b[1mkshield start\x1b[0m");
            println!();
        }
        Err(e) => {
            eprintln!("  \x1b[31m✗\x1b[0m  Setup failed: {e}");
            std::process::exit(1);
        }
    }
    Ok(())
}

// ── start / stop ──────────────────────────────────────────────────────────────

async fn cmd_start() -> Result<()> {
    let client = Client::new();

    if setup::backend_pid_running() || http::health_check(&client).await {
        println!("\x1b[32m  Backend is already running at {}\x1b[0m", http::backend_url());
        return Ok(());
    }

    // Ensure setup is done first
    let backend_dir = if let Some(d) = setup::find_backend_dir() {
        d
    } else {
        println!("  Backend not found — running setup first...");
        setup::run_setup(true).await?
    };

    println!("  Starting backend...");
    match setup::start_backend_process(&backend_dir) {
        Ok(_) => {
            // Poll until healthy (async — no nested runtime)
            let became_healthy = http::try_start_backend().await;
            if became_healthy {
                println!("  \x1b[32m✓\x1b[0m  Backend running at {}", http::backend_url());
                println!("  \x1b[2m  Logs: ~/.kshield/backend.log\x1b[0m");
            } else {
                eprintln!("  \x1b[33m!\x1b[0m  Backend started but health check timed out.");
                eprintln!("  Check logs: ~/.kshield/backend.log");
            }
        }
        Err(e) => {
            eprintln!("  \x1b[31m✗\x1b[0m  Could not start backend: {e}");
            eprintln!("  Run  kshield setup  to install the Python environment.");
            std::process::exit(1);
        }
    }
    Ok(())
}

fn cmd_stop() -> Result<()> {
    let af_dir = setup::kshield_dir()?;
    let pid_path = af_dir.join("backend.pid");

    let pid_str = std::fs::read_to_string(&pid_path)
        .unwrap_or_default();
    let pid = pid_str.trim().to_string();

    if pid.is_empty() {
        println!("  Backend is not running (no PID file found).");
        return Ok(());
    }

    let killed = std::process::Command::new("kill")
        .arg(&pid)
        .status()
        .map(|s| s.success())
        .unwrap_or(false);

    if killed {
        std::fs::remove_file(&pid_path).ok();
        println!("  \x1b[32m✓\x1b[0m  Backend stopped (PID {pid})");
    } else {
        eprintln!("  Could not stop backend (PID {pid}). It may have already exited.");
    }
    Ok(())
}

// ── status ────────────────────────────────────────────────────────────────────

async fn cmd_status() -> Result<()> {
    let client = Client::new();
    let ok = http::health_check(&client).await;
    ui::print_status(ok, &http::backend_url());
    Ok(())
}

// ── hook (pre-commit) ─────────────────────────────────────────────────────────

async fn cmd_hook() -> Result<()> {
    let staged = match scanner::get_staged_files() {
        Ok(files) if files.is_empty() => return Ok(()),
        Ok(files) => files,
        Err(e) => {
            eprintln!("kshield: could not read staged files: {e}");
            return Ok(()); // don't block commits on internal errors
        }
    };

    let client = Client::new();

    if !http::health_check(&client).await {
        // Try to start silently and retry once
        http::try_start_backend().await;
        if !http::health_check(&client).await {
            ui::print_backend_warning();
            return Ok(());
        }
    }

    ui::print_header(staged.len());

    let sha = scanner::get_head_sha();
    let sha_ref = if sha.is_empty() { None } else { Some(sha.as_str()) };
    let suppress = config::load();

    let mut all_findings: Vec<(String, Vec<types::Anomaly>)> = Vec::new();
    let mut blocked = false;

    for file in &staged {
        match http::scan_file(&client, &file.filename, &file.content, sha_ref, suppress.clone()).await {
            Ok(result) => {
                ui::print_file_result(&file.filename, &result);
                let has_critical = result
                    .anomalies
                    .iter()
                    .any(|a| matches!(a.severity.as_str(), "CRITICAL" | "HIGH"));
                if has_critical {
                    blocked = true;
                    all_findings.push((file.filename.clone(), result.anomalies));
                }
            }
            Err(e) => {
                eprintln!("  kshield: scan failed for {}: {e}", file.filename);
            }
        }
    }

    if blocked {
        ui::print_blocked(&all_findings);
        std::process::exit(1);
    } else {
        ui::print_clean(staged.len());
    }

    Ok(())
}

// ── scan (manual) ─────────────────────────────────────────────────────────────

async fn cmd_scan(file: std::path::PathBuf) -> Result<()> {
    let content = std::fs::read_to_string(&file)?;
    let filename = file.to_string_lossy().to_string();
    let client = Client::new();

    if !http::health_check(&client).await {
        eprintln!("Backend is not running. Start it with: kshield start");
        std::process::exit(1);
    }

    let suppress = config::load();
    ui::print_header(1);
    let result = http::scan_file(&client, &filename, &content, None, suppress).await?;
    ui::print_file_result(&filename, &result);

    if !result.safe {
        let findings = vec![(filename, result.anomalies)];
        ui::print_blocked(&findings);
        std::process::exit(1);
    } else {
        ui::print_clean(1);
    }
    Ok(())
}

// ── hook installer ────────────────────────────────────────────────────────────

fn install_hook() -> Result<()> {
    use std::fs;
    #[cfg(unix)]
    use std::os::unix::fs::PermissionsExt;

    let git_dir_out = std::process::Command::new("git")
        .args(["rev-parse", "--git-dir"])
        .output()?;
    let git_dir = String::from_utf8(git_dir_out.stdout)?.trim().to_string();
    let hook_dir = std::path::PathBuf::from(&git_dir).join("hooks");
    fs::create_dir_all(&hook_dir)?;

    let hook_path = hook_dir.join("pre-commit");
    let binary = std::env::current_exe()
        .ok()
        .and_then(|p| p.to_str().map(String::from))
        .unwrap_or_else(|| "kshield".to_string());

    let script = format!(
        "#!/bin/sh\n# KShield pre-commit hook\n\"{binary}\" hook\n"
    );
    fs::write(&hook_path, &script)?;

    #[cfg(unix)]
    fs::set_permissions(&hook_path, fs::Permissions::from_mode(0o755))?;

    Ok(())
}
