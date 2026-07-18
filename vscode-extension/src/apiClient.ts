import * as vscode from 'vscode';
import { ScanResult, SuppressConfig } from './types';

const HEALTH_TIMEOUT_MS = 2000;
const SCAN_TIMEOUT_MS = 30000;

export class BackendUnavailableError extends Error {}

function backendUrl(): string {
  const configured = vscode.workspace.getConfiguration('kshield').get<string>('backendUrl', 'http://127.0.0.1:8000');
  return configured.replace(/\/+$/, '');
}

async function withTimeout(ms: number): Promise<{ signal: AbortSignal; cancel: () => void }> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), ms);
  return { signal: controller.signal, cancel: () => clearTimeout(timer) };
}

export async function checkHealth(): Promise<boolean> {
  const { signal, cancel } = await withTimeout(HEALTH_TIMEOUT_MS);
  try {
    const res = await fetch(`${backendUrl()}/health`, { signal });
    return res.ok;
  } catch {
    return false;
  } finally {
    cancel();
  }
}

export async function scanFile(filename: string, content: string, suppress?: Partial<SuppressConfig>): Promise<ScanResult> {
  const { signal, cancel } = await withTimeout(SCAN_TIMEOUT_MS);
  let res: Response;
  try {
    res = await fetch(`${backendUrl()}/api/v1/scan`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        filename,
        content,
        suppress: { severities: [], rules: [], paths: [], ...suppress },
      }),
      signal,
    });
  } catch (err) {
    throw new BackendUnavailableError(`Could not reach KShield backend at ${backendUrl()}: ${(err as Error).message}`);
  } finally {
    cancel();
  }

  if (!res.ok) {
    const body = await res.text().catch(() => '');
    throw new Error(`KShield scan failed (${res.status}): ${body}`);
  }
  return (await res.json()) as ScanResult;
}

export async function suppressRule(ruleType: string, justification = 'Suppressed from VS Code'): Promise<void> {
  const res = await fetch(`${backendUrl()}/api/v1/suppress`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ rule_type: ruleType, justification }),
  });
  if (!res.ok) {
    const body = await res.text().catch(() => '');
    throw new Error(`KShield: failed to suppress rule (${res.status}): ${body}`);
  }
}
