export interface Remediation {
  explanation: string;
  patch_diff: string;
}

export interface Anomaly {
  id: string;
  line: number;
  type: string;
  severity: 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW';
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

export interface GlobalTelemetry {
  totalScans: number;
  cleanFiles: number;
  openVulnerabilities: number;
  breakdown: {
    critical: number;
    high: number;
    medium: number;
    low: number;
  };
}
