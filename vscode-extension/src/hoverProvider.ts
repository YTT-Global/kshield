import * as vscode from 'vscode';
import { AnomalyStore, KSHIELD_SOURCE } from './diagnostics';

export class KShieldHoverProvider implements vscode.HoverProvider {
  constructor(
    private readonly store: AnomalyStore,
    private readonly diagnostics: vscode.DiagnosticCollection
  ) {}

  provideHover(document: vscode.TextDocument, position: vscode.Position): vscode.Hover | undefined {
    const fileDiagnostics = this.diagnostics.get(document.uri) ?? [];
    const hit = fileDiagnostics.find((d) => d.source === KSHIELD_SOURCE && d.range.contains(position));
    if (!hit || typeof hit.code !== 'string') {
      return undefined;
    }

    const anomaly = this.store.get(document.uri, hit.code);
    if (!anomaly) {
      return undefined;
    }

    const md = new vscode.MarkdownString(undefined, true);
    md.appendMarkdown(`**KShield · ${anomaly.severity} · ${anomaly.type}**\n\n`);
    md.appendMarkdown(`${anomaly.description}\n`);
    if (anomaly.remediation.explanation) {
      md.appendMarkdown(`\n---\n${anomaly.remediation.explanation}\n`);
    }
    return new vscode.Hover(md, hit.range);
  }
}
