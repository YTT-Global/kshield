use serde::{Deserialize, Serialize};
use std::path::Path;

/// Suppression rules read from .kshield.yml in the repo root.
#[derive(Debug, Default, Serialize, Deserialize, Clone)]
pub struct SuppressConfig {
    /// Severity levels to completely ignore: LOW, MEDIUM, HIGH, CRITICAL
    #[serde(default)]
    pub severities: Vec<String>,

    /// Exact rule-type names to ignore, e.g. "AI Hallucination", "Syntax Violation"
    #[serde(default)]
    pub rules: Vec<String>,

    /// Glob path patterns to skip entirely, e.g. "tests/**", "migrations/**"
    #[serde(default)]
    pub paths: Vec<String>,
}

#[derive(Debug, Default, Deserialize)]
struct KshieldConfig {
    #[serde(default)]
    suppress: SuppressConfig,
}

/// Reads `.kshield.yml` from the repo root (current directory).
/// Returns an empty config if the file is absent or unparseable.
pub fn load() -> SuppressConfig {
    let path = Path::new(".kshield.yml");
    let Ok(text) = std::fs::read_to_string(path) else {
        return SuppressConfig::default();
    };
    match serde_yaml::from_str::<KshieldConfig>(&text) {
        Ok(cfg) => cfg.suppress,
        Err(e) => {
            eprintln!("kshield: warning — could not parse .kshield.yml: {e}");
            SuppressConfig::default()
        }
    }
}
