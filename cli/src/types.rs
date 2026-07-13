use serde::{Deserialize, Serialize};

#[derive(Debug, Deserialize, Serialize, Clone)]
pub struct Anomaly {
    pub id: String,
    pub line: u32,
    #[serde(rename = "type")]
    pub anomaly_type: String,
    pub severity: String,
    pub description: String,
    pub remediation: Remediation,
}

#[derive(Debug, Deserialize, Serialize, Clone)]
pub struct Remediation {
    pub explanation: String,
    pub patch_diff: String,
}

#[derive(Debug, Deserialize, Serialize)]
pub struct ScanResult {
    pub scan_id: String,
    pub filename: String,
    pub safe: bool,
    pub vulnerabilities_discovered: u32,
    pub anomalies: Vec<Anomaly>,
}

#[derive(Debug, Serialize)]
pub struct ScanPayload {
    pub filename: String,
    pub content: String,
    pub commit_sha: Option<String>,
}
