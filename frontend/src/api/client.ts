import type { ScanResult, GlobalTelemetry, SuppressedRule } from '../types/scan';

const BASE = 'http://localhost:8000/api/v1';

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE}${path}`);
  if (!res.ok) throw new Error(`KShield API ${path} → ${res.status}`);
  return res.json() as Promise<T>;
}

async function post<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(`KShield API ${path} → ${res.status}`);
  return res.json() as Promise<T>;
}

async function del<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE}${path}`, { method: 'DELETE' });
  if (!res.ok) throw new Error(`KShield API ${path} → ${res.status}`);
  return res.json() as Promise<T>;
}

export const api = {
  scans:            (): Promise<ScanResult[]>      => get('/scans'),
  telemetry:        (): Promise<GlobalTelemetry>   => get('/telemetry'),
  suppress:         (rule_type: string)            => post('/suppress', { rule_type }),
  suppressedRules:  (): Promise<SuppressedRule[]>  => get('/suppress'),
  unsuppress:       (rule_type: string)            => del(`/suppress/${encodeURIComponent(rule_type)}`),
  applyPatch:       (vulnerability_id: string)     => post('/apply-patch', { vulnerability_id }),
};
