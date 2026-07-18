import * as vscode from 'vscode';
import { Anomaly, Severity } from './types';

export const KSHIELD_SOURCE = 'KShield';

const SEVERITY_MAP: Record<Severity, vscode.DiagnosticSeverity> = {
  CRITICAL: vscode.DiagnosticSeverity.Error,
  HIGH: vscode.DiagnosticSeverity.Error,
  MEDIUM: vscode.DiagnosticSeverity.Warning,
  LOW: vscode.DiagnosticSeverity.Information,
};

/** Keeps the full finding (including remediation) addressable by diagnostic id, per file. */
export class AnomalyStore {
  private byUri = new Map<string, Map<string, Anomaly>>();

  set(uri: vscode.Uri, anomalies: Anomaly[]): void {
    const byId = new Map<string, Anomaly>();
    for (const anomaly of anomalies) {
      byId.set(anomaly.id, anomaly);
    }
    this.byUri.set(uri.toString(), byId);
  }

  get(uri: vscode.Uri, id: string): Anomaly | undefined {
    return this.byUri.get(uri.toString())?.get(id);
  }

  clear(uri: vscode.Uri): void {
    this.byUri.delete(uri.toString());
  }
}

export function buildDiagnostics(document: vscode.TextDocument, anomalies: Anomaly[]): vscode.Diagnostic[] {
  return anomalies.map((anomaly) => {
    const lineIndex = Math.max(0, Math.min(anomaly.line - 1, document.lineCount - 1));
    const line = document.lineAt(lineIndex);
    const range = new vscode.Range(lineIndex, line.firstNonWhitespaceCharacterIndex, lineIndex, line.text.length);

    const diagnostic = new vscode.Diagnostic(
      range,
      `${anomaly.type}: ${anomaly.description}`,
      SEVERITY_MAP[anomaly.severity] ?? vscode.DiagnosticSeverity.Warning
    );
    diagnostic.source = KSHIELD_SOURCE;
    diagnostic.code = anomaly.id;
    return diagnostic;
  });
}
