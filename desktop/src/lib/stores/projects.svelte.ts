import { api } from '../api/client';
import type { Folder, Project } from '../api/types';
import { onEvent } from './connection.svelte';
import { persistPrefs, prefs } from './prefs.svelte';

export const projects = $state({ list: [] as Project[], loaded: false });

export function currentProject(): Project | null {
  return projects.list.find((p) => p.id === prefs.projectId) ?? null;
}

export function currentFolder(): Folder | null {
  const p = currentProject();
  return p?.folders.find((f) => f.id === prefs.folderId) ?? null;
}

export function selectProject(projectId: string | null, folderId: string | null = null) {
  prefs.projectId = projectId;
  prefs.folderId = folderId;
  persistPrefs();
}

/** Destination for new generations / conversations. */
export function destination() {
  return { project_id: prefs.projectId, folder_id: prefs.folderId };
}

export function folderTree(p: Project, parent: string | null = null): (Folder & { children: any[]; depth: number })[] {
  const walk = (parentId: string | null, depth: number): any[] =>
    p.folders
      .filter((f) => f.parent_id === parentId)
      .sort((a, b) => a.name.localeCompare(b.name))
      .map((f) => ({ ...f, depth, children: walk(f.id, depth + 1) }));
  return walk(parent, 0);
}

export function folderPath(p: Project | null, folderId: string | null): string {
  if (!p || !folderId) return p?.name ?? 'Unfiled';
  const parts: string[] = [];
  let cur = p.folders.find((f) => f.id === folderId);
  while (cur) {
    parts.unshift(cur.name);
    cur = cur.parent_id ? p.folders.find((f) => f.id === cur!.parent_id) : undefined;
  }
  return [p.name, ...parts].join(' / ');
}

export async function loadProjects() {
  projects.list = await api.get<Project[]>('/v1/projects');
  projects.loaded = true;
  if (prefs.projectId && !projects.list.some((p) => p.id === prefs.projectId)) selectProject(null);
}

export async function createProject(name: string) {
  const p = await api.post<Project>('/v1/projects', { name });
  await loadProjects();
  return p;
}

export async function createFolder(project_id: string, name: string, parent_id: string | null = null) {
  const f = await api.post<Folder>('/v1/folders', { project_id, name, parent_id });
  await loadProjects();
  return f;
}

export async function renameProject(id: string, name: string) {
  await api.patch(`/v1/projects/${id}`, { name });
  await loadProjects();
}

export async function renameFolder(id: string, name: string) {
  await api.patch(`/v1/folders/${id}`, { name });
  await loadProjects();
}

export async function deleteProject(id: string) {
  await api.del(`/v1/projects/${id}`);
  if (prefs.projectId === id) selectProject(null);
  await loadProjects();
}

export async function deleteFolder(id: string) {
  await api.del(`/v1/folders/${id}`);
  if (prefs.folderId === id) prefs.folderId = null;
  await loadProjects();
}

let wired = false;
export function wireProjectEvents() {
  if (wired) return;
  wired = true;
  onEvent('projects.changed', () => loadProjects().catch(() => {}));
}
