import { api, qs } from '../api/client';
import type { Generation, Job, NodeState, Workflow } from '../api/types';
import { onEvent } from './connection.svelte';
import { toast } from './toast.svelte';

interface LiveProgress {
  progress: number;
  text: string | null;
  node_id: string | null;
  step: number | null;
  total: number | null;
}

export const jobs = $state({
  byId: {} as Record<string, Job>,
  progress: {} as Record<string, LiveProgress>,
  previews: {} as Record<string, string>,
  nodeStates: {} as Record<string, Record<string, NodeState>>,
  loaded: false,
});

/** Callbacks fired when a generation is created (views append to their history). */
const genListeners = new Set<(g: Generation) => void>();
export function onGeneration(fn: (g: Generation) => void) {
  genListeners.add(fn);
  return () => genListeners.delete(fn);
}

export function activeJobs(kind?: 'image' | 'video'): Job[] {
  return Object.values(jobs.byId)
    .filter((j) => (j.status === 'queued' || j.status === 'running') && (!kind || j.kind === kind))
    .sort((a, b) => a.created_at - b.created_at);
}

export function recentJobs(limit = 30): Job[] {
  return Object.values(jobs.byId).sort((a, b) => b.created_at - a.created_at).slice(0, limit);
}

export async function loadJobs() {
  const list = await api.get<Job[]>(`/v1/jobs${qs({ limit: 80 })}`);
  for (const j of list) jobs.byId[j.id] = j;
  jobs.loaded = true;
}

export async function submitJob(body: {
  kind: 'image' | 'video';
  simple?: Record<string, unknown>;
  workflow?: Workflow;
  project_id?: string | null;
  folder_id?: string | null;
  title?: string;
}): Promise<Job> {
  const job = await api.post<Job>('/v1/jobs', body);
  jobs.byId[job.id] = job;
  return job;
}

export async function cancelJob(id: string) {
  const j = await api.post<Job>(`/v1/jobs/${id}/cancel`);
  jobs.byId[id] = { ...jobs.byId[id], ...j };
}

export async function retryJob(id: string, newSeed = false) {
  const j = await api.post<Job>(`/v1/jobs/${id}/retry`, { new_seed: newSeed });
  jobs.byId[j.id] = j;
  return j;
}

let wired = false;
export function wireJobEvents() {
  if (wired) return;
  wired = true;
  onEvent('job.created', (e) => {
    jobs.byId[e.data.id] = { ...(jobs.byId[e.data.id] ?? {}), ...e.data };
  });
  onEvent('job.updated', (e) => {
    const j = e.data as Job;
    const prev = jobs.byId[j.id];
    jobs.byId[j.id] = { ...(prev ?? {}), ...j };
    if (j.status !== 'running') {
      delete jobs.progress[j.id];
    }
    if (j.status === 'completed' || j.status === 'failed' || j.status === 'cancelled') {
      delete jobs.previews[j.id];
      if (j.node_states) jobs.nodeStates[j.id] = j.node_states;
    }
    if (prev && prev.status !== j.status && j.status === 'failed') {
      toast('error', `${j.kind === 'video' ? 'Video' : 'Image'} generation failed`, j.error?.message ?? undefined);
    }
  });
  onEvent('job.progress', (e) => {
    jobs.progress[e.data.id] = e.data;
    const j = jobs.byId[e.data.id];
    if (j) {
      j.progress = e.data.progress;
      j.progress_text = e.data.text;
      if (j.status === 'queued') j.status = 'running';
    }
  });
  onEvent('job.preview', (e) => {
    jobs.previews[e.data.id] = e.data.image;
  });
  onEvent('job.node', (e) => {
    const { id, node_id, ...state } = e.data;
    if (!jobs.nodeStates[id]) jobs.nodeStates[id] = {};
    jobs.nodeStates[id][node_id] = state;
  });
  onEvent('generation.created', (e) => {
    for (const fn of genListeners) fn(e.data as Generation);
  });
  onEvent('connection.restored', () => {
    loadJobs().catch(() => {});
  });
}
