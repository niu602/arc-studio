import type { ModelSelection } from '../types';
import type { HistoryItem } from '../mock/data';

const KEY_API = 'arc_api_key';
const KEY_BASE = 'arc_base_url';
const KEY_MODELS = 'arc_models';

export function getApiKey(): string {
  return localStorage.getItem(KEY_API) ?? '';
}

export function setApiKey(v: string): void {
  localStorage.setItem(KEY_API, v ?? '');
}

export function getBaseUrl(): string {
  return localStorage.getItem(KEY_BASE) ?? 'https://api.deepseek.com/v1';
}

export function setBaseUrl(v: string): void {
  localStorage.setItem(KEY_BASE, v ?? '');
}

export function getModels(): ModelSelection | null {
  const raw = localStorage.getItem(KEY_MODELS);
  if (!raw) return null;
  try {
    return JSON.parse(raw) as ModelSelection;
  } catch {
    return null;
  }
}

export function setModels(v: ModelSelection): void {
  localStorage.setItem(KEY_MODELS, JSON.stringify(v));
}

// ===== 编译历史（localStorage）=====
const KEY_HISTORY = 'arc_history';
const KEY_DEMO = 'arc_demo_mode';

export function getDemoMode(): boolean {
  return localStorage.getItem(KEY_DEMO) === 'true';
}

export function setDemoMode(v: boolean): void {
  localStorage.setItem(KEY_DEMO, v ? 'true' : 'false');
}

export function getHistory(): HistoryItem[] {
  const raw = localStorage.getItem(KEY_HISTORY);
  if (!raw) return [];
  try {
    const arr = JSON.parse(raw) as HistoryItem[];
    return Array.isArray(arr) ? arr : [];
  } catch {
    return [];
  }
}

export function addHistory(item: HistoryItem): HistoryItem[] {
  const list = [item, ...getHistory()].slice(0, 30);
  localStorage.setItem(KEY_HISTORY, JSON.stringify(list));
  return list;
}
