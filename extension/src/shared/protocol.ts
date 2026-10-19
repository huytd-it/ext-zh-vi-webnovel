export const BASE = 'http://127.0.0.1:17865/v1';
export const MODEL_IDS = ['HachimiMT-60', 'MoxhiMT-60', 'HirashibaMT-Medium'];
export type Entry = {source: string; target: string; enabled: boolean};
export type Glossary = {id: string; name: string; entries: Entry[]};
export type Config = {model: string; glossary_id: string | null; device: 'cpu' | 'cuda'};
export type Unit = {id: string; text: string};
export type Result = {id: string; text?: string; warning?: string; error?: string};
export type Job = {id: string; version: string; state: string; results: Result[];
  device: string | null; warning: string | null};
export function unitsValid(value: unknown): value is Unit[] {
  return Array.isArray(value) && value.length > 0 && value.length <= 32 &&
    value.every(u => u && typeof u.id === 'string' && u.id.length <= 80 &&
      typeof u.text === 'string' && u.text.length > 0 && u.text.length <= 16000) &&
    value.reduce((n, u) => n + u.text.length, 0) <= 64000 &&
    new Set(value.map(u => u.id)).size === value.length;
}
export async function message<T = any>(body: unknown): Promise<T> {
  const response = await chrome.runtime.sendMessage(body);
  if (!response?.ok) throw new Error(response?.error || 'Không kết nối được extension.');
  return response.data;
}
