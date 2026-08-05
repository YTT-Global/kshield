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
    pub suppress: crate::config::SuppressConfig,
}

#[derive(Debug, Serialize)]
pub struct AuditFile {
    pub filename: String,
    pub content: String,
}

#[derive(Debug, Serialize)]
pub struct AuditPayload {
    pub name: String,
    pub files: Vec<AuditFile>,
    pub suppress: crate::config::SuppressConfig,
}

#[derive(Debug, Deserialize)]
pub struct AuditRoute {
    pub path: String,
    pub method: String,
    pub handler: String,
    pub filename: String,
    pub line: u32,
}

#[derive(Debug, Deserialize)]
pub struct AuditFinding {
    pub line_number: u32,
    pub anomaly_type: String,
    pub severity: String,
    pub description: String,
    pub filename: String,
    pub remediation: Remediation,
}

#[derive(Debug, Deserialize)]
pub struct AuditResult {
    #[allow(dead_code)]
    pub name: String,
    pub file_count: u32,
    pub route_count: u32,
    pub symbol_count: u32,
    pub import_edge_count: u32,
    pub parse_errors: std::collections::HashMap<String, String>,
    pub findings_count: u32,
    pub quieted_count: u32,
    pub findings: Vec<AuditFinding>,
    pub routes: Vec<AuditRoute>,
}
