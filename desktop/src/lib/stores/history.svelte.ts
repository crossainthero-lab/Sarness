// Per-kind generation history used by the Images and Videos studios.
import { api, qs } from '../api/client';
import type { Generation, Page } from '../api/types';
import { onEvent } from './connection.svelte';
import { onGeneration } from './jobs.svelte';

export function createHistory(kind: 'image' | 'video') {
  const h = $state({
    items: [] as Generation[],
    index: 0,
    loading: false,
    cursor: null as number | null,
    loaded: false,
    follow: new Set<string>(), // job ids submitted from this studio
  });

  async function load() {
    h.loading = true;
    try {
      const page = await api.get<Page<Generation>>(`/v1/generations${qs({ type: kind, limit: 60 })}`);
      h.items = page.items;
      h.cursor = page.next_cursor;
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
    if (g.type !== kind || h.items.some((x) => x.id === g.id)) return;
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
