use anyhow::{bail, Result};
use std::path::PathBuf;
use std::process::Command;

pub struct StagedFile {
    pub filename: String,
    pub content: String,
}

/// `git diff --cached --name-only` / `git ls-files` both return paths relative to
/// the repo root — not the caller's current directory, which may be a subdirectory
/// of the repo. The backend's apply-patch endpoint looks the file up by that exact
/// `filename` string later (from a different process, with its own unrelated cwd),
/// so a repo-relative path is nearly always wrong by the time it gets there. Resolve
/// to an absolute path here, once, so it's unambiguous no matter who reads it next.
fn repo_root() -> Result<PathBuf> {
    let output = Command::new("git")
        .args(["rev-parse", "--show-toplevel"])
        .output()?;

    if !output.status.success() {
        bail!(
            "git rev-parse --show-toplevel failed: {}",
            String::from_utf8_lossy(&output.stderr)
        );
    }

    Ok(PathBuf::from(
        String::from_utf8(output.stdout)?.trim().to_string(),
    ))
}

/// Returns the list of staged files with their content as they exist in the index.
///
/// Every git subprocess here is pinned to the repo root via `.current_dir(&root)`,
/// deliberately, not left to inherit the caller's cwd. Two real bugs came from
/// trusting git's default path-relativity: `git diff --cached --name-only` happens
/// to already be repo-root-relative by default, which made an earlier version of
/// this function look correct when tested from a subdirectory — but `git show
/// :{filename}` interprets that same repo-relative path *relative to cwd*, so a
/// staged file outside the invoking subdirectory would silently fail to resolve.
/// Pinning cwd to root removes the ambiguity for every call, not just the ones a
/// test happened to exercise.
pub fn get_staged_files() -> Result<Vec<StagedFile>> {
    let root = repo_root()?;

    let output = Command::new("git")
        .args(["diff", "--cached", "--name-only", "--diff-filter=ACM"])
        .current_dir(&root)
        .output()?;

    if !output.status.success() {
        bail!(
            "git diff failed: {}",
            String::from_utf8_lossy(&output.stderr)
        );
    }

    let filenames: Vec<String> = String::from_utf8(output.stdout)?
        .lines()
        .filter(|l| !l.is_empty())
        .map(String::from)
        .collect();

    let mut staged = Vec::new();

    for filename in filenames {
        // Read content from the git index (staged version, not working tree).
        let blob = Command::new("git")
            .args(["show", &format!(":{}", filename)])
            .current_dir(&root)
            .output();

        match blob {
            Ok(out) if out.status.success() => {
                if let Ok(content) = String::from_utf8(out.stdout) {
                    let absolute = root.join(&filename).to_string_lossy().to_string();
                    staged.push(StagedFile { filename: absolute, content });
                }
                // Binary files silently skipped (UTF-8 parse fails)
            }
            _ => {
                // File may have been deleted between diff and show — skip
            }
        }
    }

    Ok(staged)
}

/// Returns every git-tracked file in the repo with its current working-tree content.
/// Used for full-repo audits (`kshield agent <name>`), unlike `get_staged_files`
/// which only covers the pre-commit diff.
pub fn get_tracked_files() -> Result<Vec<StagedFile>> {
    let root = repo_root()?;

    // Real bug: `git ls-files` (unlike `git diff`) defaults to a scope AND a
    // path format both relative to the caller's cwd, not the repo root —
    // running `kshield agent` from any subdirectory silently audited only
    // that subdirectory's files (or, combined with the absolute-path
    // reconstruction below, could produce paths that don't exist at all).
    // Pinning `.current_dir(&root)` fixes both the scope (whole repo, not
    // just cwd's subtree) and the path format (root-relative) in one move.
    let output = Command::new("git")
        .args(["ls-files"])
        .current_dir(&root)
        .output()?;

    if !output.status.success() {
        bail!(
            "git ls-files failed: {}",
            String::from_utf8_lossy(&output.stderr)
        );
    }

    let filenames: Vec<String> = String::from_utf8(output.stdout)?
        .lines()
        .filter(|l| !l.is_empty())
        .map(String::from)
        .collect();

    let mut tracked = Vec::new();

    for filename in filenames {
        let absolute = root.join(&filename);
        // Binary files silently skipped (UTF-8 read fails)
        if let Ok(content) = std::fs::read_to_string(&absolute) {
            tracked.push(StagedFile { filename: absolute.to_string_lossy().to_string(), content });
        }
    }

    Ok(tracked)
}

/// Returns the short SHA of the current HEAD commit (empty string on a brand-new repo).
pub fn get_head_sha() -> String {
    Command::new("git")
        .args(["rev-parse", "--short", "HEAD"])
        .output()
        .ok()
        .and_then(|o| String::from_utf8(o.stdout).ok())
        .map(|s| s.trim().to_string())
        .unwrap_or_default()
}
