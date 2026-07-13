use anyhow::{bail, Result};
use std::process::Command;

pub struct StagedFile {
    pub filename: String,
    pub content: String,
}

/// Returns the list of staged files with their content as they exist in the index.
pub fn get_staged_files() -> Result<Vec<StagedFile>> {
    let output = Command::new("git")
        .args(["diff", "--cached", "--name-only", "--diff-filter=ACM"])
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
        // Read content from the git index (staged version, not working tree)
        let blob = Command::new("git")
            .args(["show", &format!(":{}", filename)])
            .output();

        match blob {
            Ok(out) if out.status.success() => {
                if let Ok(content) = String::from_utf8(out.stdout) {
                    staged.push(StagedFile { filename, content });
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
