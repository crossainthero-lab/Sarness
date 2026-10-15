// Per-kind generation history used by the Images and Videos studios.
import { api, qs } from '../api/client';
import type { Generation, Page } from '../api/types';
import { onEvent } from './connection.svelte';
import { onGeneration } from './jobs.svelte';

const MAX_FOLLOW = 40;

export function createHistory(kind: 'image' | 'video', paneId: string) {
  const storeKey = `sarness.pane.${paneId}.${kind}.jobs`;
  let saved: string[] = [];
  try {
    saved = JSON.parse(localStorage.getItem(storeKey) ?? '[]');
  } catch {
    /* ignore */
  }
  const h = $state({
    items: [] as Generation[],
    index: 0,
    loading: false,
    cursor: null as number | null,
    loaded: false,
    follow: new Set<string>(saved), // job ids submitted from this pane (persisted)
  });

  function track(jobId: string) {
    h.follow.add(jobId);
    try {
      localStorage.setItem(storeKey, JSON.stringify([...h.follow].slice(-MAX_FOLLOW)));
    } catch {
      /* ignore */
    }
  }

  /** A pane's history is its own session: generations of the jobs it submitted. */
  async function load() {
    h.loading = true;
    try {
      const ids = [...h.follow].slice(-MAX_FOLLOW);
      const pages = await Promise.all(
        ids.map((job_id) => api.get<Page<Generation>>(`/v1/generations${qs({ type: kind, job_id, limit: 20 })}`).catch(() => null)),
      );
      const all = pages.flatMap((p) => p?.items ?? []);
      const seen = new Set<string>();
      h.items = all.filter((g) => !seen.has(g.id) && seen.add(g.id)).sort((a, b) => b.created_at - a.created_at);
      h.cursor = null;
      h.index = 0;
      h.loaded = true;
    } finally {
      h.loading = false;
    }
  }

  async function more() {
    if (!h.cursor || h.loading) return;
    h.loading = true;
    try {
      const page = await api.get<Page<Generation>>(`/v1/generations${qs({ type: kind, limit: 60, before: h.cursor })}`);
      h.items.push(...page.items.filter((g) => !h.items.some((x) => x.id === g.id)));
      h.cursor = page.next_cursor;
    } finally {
      h.loading = false;
    }
  }

  onGeneration((g) => {
    if (g.type !== kind || !g.job_id || !h.follow.has(g.job_id) || h.items.some((x) => x.id === g.id)) return;
    const atHead = h.index === 0;
    h.items.unshift(g);
    if (!atHead) h.index += 1;
    // Jump to fresh results of our own jobs.
    if (g.job_id && h.follow.has(g.job_id)) h.index = 0;
  });
  onEvent('generation.updated', (e) => {
    const i = h.items.findIndex((x) => x.id === e.data.id);
    if (i >= 0) h.items[i] = { ...h.items[i], ...e.data };
  });
  onEvent('generations.changed', (e) => {
    if (e.data.action === 'trash' || e.data.action === 'delete') {
      const ids: string[] = e.data.ids ?? [];
      const cur = h.items[h.index]?.id;
      h.items = h.items.filter((x) => !ids.includes(x.id));
      const ni = h.items.findIndex((x) => x.id === cur);
      h.index = ni >= 0 ? ni : Math.min(h.index, Math.max(0, h.items.length - 1));
    }
  });

  return {
    state: h,
    track,
    load,
    more,
    get current(): Generation | null {
      return h.items[h.index] ?? null;
    },
    prev() {
      if (h.index < h.items.length - 1) h.index++;
      if (h.index > h.items.length - 8) more();
    },
    next() {
      if (h.index > 0) h.index--;
    },
    select(id: string) {
      const i = h.items.findIndex((x) => x.id === id);
      if (i >= 0) h.index = i;
    },
  };
}

export type History = ReturnType<typeof createHistory>;
