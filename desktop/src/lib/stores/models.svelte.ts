import { api } from '../api/client';
import type { CatalogEntry, ChatModel, Download, InstalledModel, LlmStatus, ModelCategory, NodeLibrary } from '../api/types';
import { onEvent } from './connection.svelte';
import { toast } from './toast.svelte';

export const models = $state({
  installed: [] as InstalledModel[],
  catalog: [] as CatalogEntry[],
  downloads: [] as Download[],
  chatModels: [] as ChatModel[],
  llm: null as LlmStatus | null,
  nodes: null as NodeLibrary | null,
  loaded: false,
});

export function byCategory(cat: ModelCategory, supportedOnly = true): InstalledModel[] {
  return models.installed.filter((m) => m.category === cat && (!supportedOnly || m.supported));
}

export function modelById(id: string | null | undefined): InstalledModel | undefined {
  return id ? models.installed.find((m) => m.id === id) : undefined;
}

export async function loadModels() {
  const [installed, downloads, chat, llm] = await Promise.all([
    api.get<InstalledModel[]>('/v1/models'),
    api.get<Download[]>('/v1/downloads'),
    api.get<ChatModel[]>('/v1/llm/models'),
    api.get<LlmStatus>('/v1/llm/status'),
  ]);
  models.installed = installed;
  models.downloads = downloads;
  models.chatModels = chat;
  models.llm = llm;
  models.loaded = true;
}

export async function loadCatalog() {
  models.catalog = await api.get<CatalogEntry[]>('/v1/models/catalog');
}

export async function loadNodeLibrary(force = false) {
  if (models.nodes && !force) return models.nodes;
  models.nodes = await api.get<NodeLibrary>('/v1/nodes');
  return models.nodes;
}

export async function installCatalog(catalog_id: string, quant?: string) {
  const d = await api.post<Download>('/v1/models/install', { catalog_id, quant });
  upsertDownload(d);
  toast('info', 'Download started', d.name);
  return d;
}

export function upsertDownload(d: Partial<Download> & { id: string }) {
  const i = models.downloads.findIndex((x) => x.id === d.id);
  if (i >= 0) models.downloads[i] = { ...models.downloads[i], ...d };
  else models.downloads.unshift(d as Download);
}

let wired = false;
export function wireModelEvents() {
  if (wired) return;
  wired = true;
  onEvent('download.progress', (e) => {
    upsertDownload({ id: e.data.id, done_bytes: e.data.done_bytes, total_bytes: e.data.total_bytes, speed_bps: e.data.speed_bps, status: 'downloading' });
  });
  for (const t of ['download.created', 'download.updated']) {
    onEvent(t, (e) => {
      if (!e.data?.id) return;
      upsertDownload(e.data);
      if (e.data.status === 'completed') toast('success', 'Model installed', e.data.name);
      if (e.data.status === 'failed') toast('error', 'Download failed', e.data.error);
    });
  }
  onEvent('models.changed', () => {
    loadModels().catch(() => {});
    if (models.catalog.length) loadCatalog().catch(() => {});
  });
  onEvent('llm.status', (e) => {
    models.llm = e.data;
  });
  onEvent('connection.restored', () => loadModels().catch(() => {}));
}
