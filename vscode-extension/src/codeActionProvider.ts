import * as vscode from 'vscode';
import { AnomalyStore, KSHIELD_SOURCE } from './diagnostics';

export class KShieldCodeActionProvider implements vscode.CodeActionProvider {
  static readonly providedCodeActionKinds = [vscode.CodeActionKind.QuickFix];

  constructor(private readonly store: AnomalyStore) {}

  provideCodeActions(
    document: vscode.TextDocument,
    _range: vscode.Range,
    context: vscode.CodeActionContext
  ): vscode.CodeAction[] {
    const actions: vscode.CodeAction[] = [];

    for (const diagnostic of context.diagnostics) {
      if (diagnostic.source !== KSHIELD_SOURCE || typeof diagnostic.code !== 'string') {
        continue;
      }
      const anomaly = this.store.get(document.uri, diagnostic.code);
      if (!anomaly) {
        continue;
      }

      if (anomaly.remediation.patch_diff) {
        const fix = new vscode.CodeAction(`KShield: Apply fix — ${anomaly.type}`, vscode.CodeActionKind.QuickFix);
        fix.diagnostics = [diagnostic];
        fix.command = {
          command: 'kshield.applyFix',
          title: 'Apply KShield fix',
          arguments: [document.uri, anomaly.id],
        };
        actions.push(fix);
      }

      const suppress = new vscode.CodeAction(
        `KShield: Suppress "${anomaly.type}" findings`,
        vscode.CodeActionKind.QuickFix
      );
      suppress.diagnostics = [diagnostic];
      suppress.command = {
        command: 'kshield.suppressRule',
        title: 'Suppress KShield rule',
        arguments: [anomaly.type],
      };
      actions.push(suppress);
    }

    return actions;
  }
}
