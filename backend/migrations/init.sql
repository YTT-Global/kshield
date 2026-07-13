-- Enable extension capability maps securely
CREATE EXTENSION IF NOT EXISTS pgvector;

-- Scan history table
CREATE TABLE IF NOT EXISTS scans (
    id VARCHAR(255) PRIMARY KEY,
    filename VARCHAR(512) NOT NULL,
    commit_sha VARCHAR(255),
    is_safe BOOLEAN DEFAULT TRUE NOT NULL,
    issues_count INT DEFAULT 0 NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL
);

-- Vulnerability findings table
CREATE TABLE IF NOT EXISTS vulnerabilities (
    id VARCHAR(255) PRIMARY KEY,
    scan_id VARCHAR(255) REFERENCES scans(id) ON DELETE CASCADE NOT NULL,
    line_number INT NOT NULL,
    anomaly_type VARCHAR(255) NOT NULL,
    severity VARCHAR(50) NOT NULL,
    description TEXT NOT NULL,
    code_snippet TEXT NOT NULL,
    embedding vector(1536),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL
);

-- False positive suppression table
CREATE TABLE IF NOT EXISTS false_positives (
    id VARCHAR(255) PRIMARY KEY,
    file_signature VARCHAR(255) NOT NULL,
    rule_id VARCHAR(255) NOT NULL,
    justification TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL
);

-- Engine configuration table
CREATE TABLE IF NOT EXISTS configurations (
    key VARCHAR(255) PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL
);

-- Create optimal index configurations for production lookup loads
CREATE INDEX IF NOT EXISTS idx_scans_filename ON scans(filename);
CREATE INDEX IF NOT EXISTS idx_vulnerabilities_anomaly ON vulnerabilities(anomaly_type);
CREATE INDEX IF NOT EXISTS idx_vulnerabilities_severity ON vulnerabilities(severity);
