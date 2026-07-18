import * as vscode from 'vscode';

export class KShieldStatusBar implements vscode.Disposable {
  private readonly item: vscode.StatusBarItem;

  constructor() {
    this.item = vscode.window.createStatusBarItem(vscode.StatusBarAlignment.Right, 100);
    this.item.command = 'kshield.restartBackendCheck';
    this.setUnknown();
    this.item.show();
  }

  setUnknown(): void {
    this.item.text = '$(shield) KShield';
    this.item.tooltip = 'KShield: checking backend connection…';
    this.item.backgroundColor = undefined;
  }

  setScanning(): void {
    this.item.text = '$(sync~spin) KShield';
    this.item.tooltip = 'KShield: scanning…';
    this.item.backgroundColor = undefined;
  }

  setConnected(): void {
    this.item.text = '$(shield) KShield';
    this.item.tooltip = 'KShield backend connected';
    this.item.backgroundColor = undefined;
  }

  setDisconnected(): void {
    this.item.text = '$(shield) KShield $(warning)';
    this.item.tooltip = 'KShield backend unreachable — run "kshield start", then click to retry.';
    this.item.backgroundColor = new vscode.ThemeColor('statusBarItem.warningBackground');
  }

  dispose(): void {
    this.item.dispose();
  }
}
