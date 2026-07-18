// Mirrors backend/app/api/v1/scan.py response shape and cli/src/types.rs.

export type Severity = 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW';

export interface Remediation {
  explanation: string;
  patch_diff: string;
}

export interface Anomaly {
  id: string;
  line: number;
  type: string;
  severity: Severity;
  description: string;
  remediation: Remediation;
}

export interface ScanResult {
  scan_id: string;
  filename: string;
  safe: boolean;
  vulnerabilities_discovered: number;
  anomalies: Anomaly[];
}

export interface SuppressConfig {
  severities: string[];
  rules: string[];
  paths: string[];
}
