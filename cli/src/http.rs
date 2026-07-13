use anyhow::Result;
use reqwest::Client;

use crate::setup;
use crate::types::{ScanPayload, ScanResult};

const DEFAULT_BACKEND: &str = "http://127.0.0.1:8000";

pub fn backend_url() -> String {
    std::env::var("KSHIELD_BACKEND").unwrap_or_else(|_| DEFAULT_BACKEND.to_string())
}

/// Returns true if the backend is reachable and healthy.
pub async fn health_check(client: &Client) -> bool {
    let url = format!("{}/health", backend_url());
    client
        .get(&url)
        .timeout(std::time::Duration::from_secs(2))
        .send()
        .await
        .map(|r| r.status().is_success())
        .unwrap_or(false)
}

/// Sends file content to the backend scan endpoint.
pub async fn scan_file(
    client: &Client,
    filename: &str,
    content: &str,
    commit_sha: Option<&str>,
) -> Result<ScanResult> {
    let url = format!("{}/api/v1/scan", backend_url());
    let payload = ScanPayload {
        filename: filename.to_string(),
        content: content.to_string(),
        commit_sha: commit_sha.map(String::from),
    };

    let response = client
        .post(&url)
        .json(&payload)
        .timeout(std::time::Duration::from_secs(30))
        .send()
        .await?;

    if !response.status().is_success() {
        let status = response.status();
        let body = response.text().await.unwrap_or_default();
        anyhow::bail!("Backend returned {}: {}", status, body);
    }

    Ok(response.json::<ScanResult>().await?)
}

/// Tries to start the backend, then polls until it becomes healthy.
/// Fully async — no nested runtime, no blocking thread spawning.
pub async fn try_start_backend() -> bool {
    let backend_dir = match setup::find_backend_dir() {
        Some(d) => d,
        None => return false,
    };

    // Spawn is a synchronous OS call — fine to call from async context
    if setup::start_backend_process(&backend_dir).is_err() {
        return false;
    }

    // Poll with async sleeps — no nested tokio runtime needed
    let client = Client::new();
    for _ in 0..12 {
        tokio::time::sleep(std::time::Duration::from_millis(500)).await;
        if health_check(&client).await {
            return true;
        }
    }

    false
}
