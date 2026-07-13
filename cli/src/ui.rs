use crate::types::{Anomaly, ScanResult};

// ANSI colour helpers
const RESET: &str = "\x1b[0m";
const BOLD: &str = "\x1b[1m";
const DIM: &str = "\x1b[2m";
const RED: &str = "\x1b[31m";
const GREEN: &str = "\x1b[32m";
const YELLOW: &str = "\x1b[33m";
const CYAN: &str = "\x1b[36m";
const WHITE: &str = "\x1b[37m";
const BG_RED: &str = "\x1b[41m";
const BG_GREEN: &str = "\x1b[42m";

fn severity_colour(sev: &str) -> &'static str {
    match sev {
        "CRITICAL" => "\x1b[35m",
        "HIGH" => RED,
        "MEDIUM" => YELLOW,
        "LOW" => CYAN,
        _ => WHITE,
    }
}

fn severity_badge(sev: &str) -> String {
    let col = severity_colour(sev);
    format!("{col}{BOLD} {sev:<8} {RESET}")
}

pub fn print_header(file_count: usize) {
    println!();
    println!("{BOLD}{CYAN}  KShield  ·  Pre-Commit Scan  {RESET}");
    println!(
        "{DIM}  Scanning {file_count} staged file{}...{RESET}",
        if file_count == 1 { "" } else { "s" }
    );
    println!();
}

pub fn print_file_result(filename: &str, result: &ScanResult) {
    let status = if result.safe {
        format!("{BG_GREEN}{BOLD}  Clean  {RESET}")
    } else {
        format!(
            "{BG_RED}{BOLD}  {} issue{}  {RESET}",
            result.vulnerabilities_discovered,
            if result.vulnerabilities_discovered == 1 { "" } else { "s" }
        )
    };
    println!("  {BOLD}{filename}{RESET}  {status}");
}

pub fn print_blocked(all_findings: &[(String, Vec<Anomaly>)]) {
    let total: usize = all_findings.iter().map(|(_, a)| a.len()).sum();

    println!();
    println!(
        "{BG_RED}{BOLD}  COMMIT BLOCKED  ·  {total} issue{} found  {RESET}",
        if total == 1 { "" } else { "s" }
    );
    println!();

    for (filename, findings) in all_findings {
        for f in findings {
            println!(
                "  {}  {DIM}{filename}:{}{RESET}",
                severity_badge(&f.severity),
                f.line
            );
            println!("  {BOLD}{}{RESET}", f.anomaly_type);
            println!("  {DIM}{}{RESET}", f.description);
            if !f.remediation.explanation.is_empty() {
                println!("  {CYAN}↳  {}{RESET}", f.remediation.explanation);
            }
            if !f.remediation.patch_diff.is_empty() {
                println!();
                for line in f.remediation.patch_diff.lines().take(12) {
                    let col = if line.starts_with('+') && !line.starts_with("+++") {
                        GREEN
                    } else if line.starts_with('-') && !line.starts_with("---") {
                        RED
                    } else {
                        DIM
                    };
                    println!("    {col}{line}{RESET}");
                }
            }
            println!("  {DIM}─────────────────────────────────────────{RESET}");
        }
    }

    println!();
    println!(
        "  {DIM}Fix the issues above, then run  {RESET}{BOLD}git commit{RESET}{DIM}  again.{RESET}"
    );
    println!("  {DIM}To skip (not recommended):      {RESET}{BOLD}git commit --no-verify{RESET}");
    println!();
}

pub fn print_clean(file_count: usize) {
    println!();
    println!(
        "{BG_GREEN}{BOLD}  All clear  ·  {file_count} file{} scanned, no issues found  {RESET}",
        if file_count == 1 { "" } else { "s" }
    );
    println!();
}

pub fn print_backend_warning() {
    println!();
    println!("{YELLOW}{BOLD}  ⚠  KShield backend is not running  {RESET}");
    println!("  {DIM}Start it with:  {RESET}{BOLD}kshield start{RESET}");
    println!("  {DIM}Commit will proceed — install backend for full protection.{RESET}");
    println!();
}

pub fn print_init_step(msg: &str) {
    println!("  {GREEN}✓{RESET}  {msg}");
}

pub fn print_init_warn(msg: &str) {
    println!("  {YELLOW}!{RESET}  {msg}");
}

pub fn print_init_header() {
    println!();
    println!("{BOLD}{CYAN}  KShield  ·  Setup{RESET}");
    println!();
}

pub fn print_init_done(backend_ok: bool) {
    println!();
    if backend_ok {
        println!("{BG_GREEN}{BOLD}  Ready  {RESET}  Hook installed · Backend running");
    } else {
        println!("{YELLOW}{BOLD}  Partial  {RESET}  Hook installed · Start backend for full scans:");
        println!("           {DIM}kshield start{RESET}");
    }
    println!();
    println!("  {DIM}Make any commit to run your first scan.{RESET}");
    println!();
}

pub fn print_status(backend_ok: bool, backend_url: &str) {
    println!();
    println!("{BOLD}{CYAN}  KShield  ·  Status{RESET}");
    println!();
    let (icon, label) = if backend_ok {
        (format!("{GREEN}●{RESET}"), format!("{GREEN}Running{RESET}"))
    } else {
        (format!("{RED}●{RESET}"), format!("{RED}Offline{RESET}"))
    };
    println!("  {icon}  Backend   {label}  {DIM}{backend_url}{RESET}");

    let hook_installed = std::path::Path::new(".git/hooks/pre-commit").exists();
    let (hi, hl) = if hook_installed {
        (
            format!("{GREEN}●{RESET}"),
            format!("{GREEN}Installed{RESET}"),
        )
    } else {
        (
            format!("{YELLOW}●{RESET}"),
            format!("{YELLOW}Not installed  —  run: kshield init{RESET}"),
        )
    };
    println!("  {hi}  Git hook  {hl}");
    println!();
}
