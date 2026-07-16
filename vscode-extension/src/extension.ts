import * as vscode from 'vscode';
import { checkHealth, scanFile, suppressRule } from './apiClient';
import { AnomalyStore, buildDiagnostics } from './diagnostics';
import { KShieldHoverProvider } from './hoverProvider';
import { KShieldCodeActionProvider } from './codeActionProvider';
import { KShieldStatusBar } from './statusBar';
import { applyUnifiedDiff } from './patch';

let diagnosticCollection: vscode.DiagnosticCollection;
let store: AnomalyStore;
let statusBar: KShieldStatusBar;
const debounceTimers = new Map<string, ReturnType<typeof setTimeout>>();

function config() {
  return vscode.workspace.getConfiguration('kshield');
}

export function activate(context: vscode.ExtensionContext): void {
  diagnosticCollection = vscode.languages.createDiagnosticCollection('kshield');
  store = new AnomalyStore();
  statusBar = new KShieldStatusBar();

  context.subscriptions.push(diagnosticCollection, statusBar);

  context.subscriptions.push(
    vscode.languages.registerHoverProvider('*', new KShieldHoverProvider(store, diagnosticCollection)),
    vscode.languages.registerCodeActionsProvider('*', new KShieldCodeActionProvider(store), {
      providedCodeActionKinds: KShieldCodeActionProvider.providedCodeActionKinds,
    })
  );

  context.subscriptions.push(
    vscode.workspace.onDidSaveTextDocument((document) => scheduleScan(document)),
    vscode.workspace.onDidCloseTextDocument((document) => {
      clearDebounce(document.uri);
      diagnosticCollection.delete(document.uri);
      store.clear(document.uri);
    })
  );

  context.subscriptions.push(
    vscode.commands.registerCommand('kshield.scanActiveFile', () => {
      const editor = vscode.window.activeTextEditor;
      if (editor) {
        void runScan(editor.document);
      }
    }),
    vscode.commands.registerCommand('kshield.applyFix', (uri: vscode.Uri, anomalyId: string) => applyFix(uri, anomalyId)),
    vscode.commands.registerCommand('kshield.suppressRule', (ruleType: string) => handleSuppressRule(ruleType)),
    vscode.commands.registerCommand('kshield.restartBackendCheck', () => refreshBackendStatus())
  );

  void refreshBackendStatus();
}

function scheduleScan(document: vscode.TextDocument): void {
  if (!config().get<boolean>('enabled', true) || !config().get<boolean>('scanOnSave', true)) {
    return;
  }
  if (document.uri.scheme !== 'file') {
    return;
  }

  clearDebounce(document.uri);
  const delay = config().get<number>('debounceMs', 800);
  const timer = setTimeout(() => void runScan(document), delay);
  debounceTimers.set(document.uri.toString(), timer);
}

function clearDebounce(uri: vscode.Uri): void {
  const key = uri.toString();
  const existing = debounceTimers.get(key);
  if (existing) {
    clearTimeout(existing);
    debounceTimers.delete(key);
  }
}

async function runScan(document: vscode.TextDocument): Promise<void> {
  const filename = vscode.workspace.asRelativePath(document.uri, false);
  statusBar.setScanning();
  try {
    const result = await scanFile(filename, document.getText());
    store.set(document.uri, result.anomalies);
    diagnosticCollection.set(document.uri, buildDiagnostics(document, result.anomalies));
    statusBar.setConnected();
  } catch (err) {
    statusBar.setDisconnected();
    console.error('[KShield] scan failed:', err);
  }
}

async function applyFix(uri: vscode.Uri, anomalyId: string): Promise<void> {
  const anomaly = store.get(uri, anomalyId);
  if (!anomaly || !anomaly.remediation.patch_diff) {
    return;
  }

  const document = await vscode.workspace.openTextDocument(uri);
  const patched = applyUnifiedDiff(document.getText(), anomaly.remediation.patch_diff);
  if (patched === null) {
    void vscode.window.showWarningMessage(
      'KShield: could not apply the fix automatically — the file changed since the finding was generated. Re-scan and try again.'
    );
    return;
  }

  const fullRange = new vscode.Range(document.positionAt(0), document.positionAt(document.getText().length));
  const edit = new vscode.WorkspaceEdit();
  edit.replace(uri, fullRange, patched);
  await vscode.workspace.applyEdit(edit);
  await document.save();
  await runScan(document);
}

async function handleSuppressRule(ruleType: string): Promise<void> {
  try {
    await suppressRule(ruleType);
    void vscode.window.showInformationMessage(`KShield: "${ruleType}" findings suppressed globally.`);
    const editor = vscode.window.activeTextEditor;
    if (editor) {
      await runScan(editor.document);
    }
  } catch (err) {
    void vscode.window.showErrorMessage(`KShield: failed to suppress rule — ${(err as Error).message}`);
  }
}

async function refreshBackendStatus(): Promise<void> {
  const healthy = await checkHealth();
  if (healthy) {
    statusBar.setConnected();
  } else {
    statusBar.setDisconnected();
  }
}

export function deactivate(): void {
  for (const timer of debounceTimers.values()) {
    clearTimeout(timer);
  }
  debounceTimers.clear();
}
