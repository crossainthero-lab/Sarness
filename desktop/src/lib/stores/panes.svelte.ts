// Tiled workspace state: up to four independent panes, each hosting a chat,
// code, image or video session. Panes stay mounted while hidden (minimised or
// behind a maximised pane), so state and running jobs are never lost.

export type PaneKind = 'chat' | 'code' | 'image' | 'video';
export interface Pane {
  id: string;
  kind: PaneKind;
}
export type Orientation = 'cols' | 'rows';

interface WorkspaceState {
  panes: Pane[];
  minimized: string[];
  maximized: string | null;
  focus: string | null;
  orientation: Orientation; // how two panes are split
  colRatio: number; // left column share (0.2–0.8)
  rowRatio: number; // top row share
}

export const MAX_PANES = 4;
const KEY = 'sarness.workspace.v1';

let seq = 0;
function newId() {
  return `p${Date.now().toString(36)}${(seq++).toString(36)}`;
}

function initial(): WorkspaceState {
  return {
    panes: [{ id: newId(), kind: 'chat' }],
    minimized: [],
    maximized: null,
    focus: null,
    orientation: 'cols',
    colRatio: 0.5,
    rowRatio: 0.5,
  };
}

function load(): WorkspaceState {
  try {
    const raw = localStorage.getItem(KEY);
    if (raw) {
      const s = JSON.parse(raw) as WorkspaceState;
      if (Array.isArray(s.panes) && s.panes.length && s.panes.length <= MAX_PANES) {
        const ids = new Set(s.panes.map((p) => p.id));
        return {
          ...initial(),
          ...s,
          minimized: (s.minimized ?? []).filter((i) => ids.has(i)),
          maximized: s.maximized && ids.has(s.maximized) ? s.maximized : null,
          focus: s.focus && ids.has(s.focus) ? s.focus : s.panes[0].id,
        };
      }
    }
  } catch {
    /* ignore corrupt state */
  }
  const s = initial();
  s.focus = s.panes[0].id;
  return s;
}

export const ws = $state<WorkspaceState>(load());

let timer: ReturnType<typeof setTimeout> | null = null;
export function persistWorkspace() {
  if (timer) clearTimeout(timer);
  timer = setTimeout(() => {
    try {
      localStorage.setItem(KEY, JSON.stringify($state.snapshot(ws)));
    } catch {
      /* storage unavailable */
    }
  }, 120);
}

export function visiblePanes(): Pane[] {
  if (ws.maximized) return ws.panes.filter((p) => p.id === ws.maximized);
  return ws.panes.filter((p) => !ws.minimized.includes(p.id));
}

export function addPane(kind: PaneKind): string | null {
  if (ws.panes.length >= MAX_PANES) return null;
  const p = { id: newId(), kind };
  ws.panes.push(p);
  ws.maximized = null;
  ws.focus = p.id;
  persistWorkspace();
  return p.id;
}

export function closePane(id: string) {
  if (ws.panes.length <= 1) return;
  ws.panes = ws.panes.filter((p) => p.id !== id);
  ws.minimized = ws.minimized.filter((i) => i !== id);
  if (ws.maximized === id) ws.maximized = null;
  if (ws.focus === id) ws.focus = ws.panes[0]?.id ?? null;
  clearPaneStorage(id);
  persistWorkspace();
}

export function setKind(id: string, kind: PaneKind) {
  const p = ws.panes.find((x) => x.id === id);
  if (p) {
    p.kind = kind;
    persistWorkspace();
  }
}

export function toggleMinimize(id: string) {
  if (ws.minimized.includes(id)) ws.minimized = ws.minimized.filter((i) => i !== id);
  else if (ws.panes.length - ws.minimized.length > 1) ws.minimized = [...ws.minimized, id];
  if (ws.maximized === id) ws.maximized = null;
  persistWorkspace();
}

export function toggleMaximize(id: string) {
  ws.maximized = ws.maximized === id ? null : id;
  ws.minimized = ws.minimized.filter((i) => i !== id);
  ws.focus = id;
  persistWorkspace();
}

export function focusPane(id: string) {
  if (ws.focus !== id) {
    ws.focus = id;
    persistWorkspace();
  }
}

export function swapPanes(a: string, b: string) {
  if (a === b) return;
  const i = ws.panes.findIndex((p) => p.id === a);
  const j = ws.panes.findIndex((p) => p.id === b);
  if (i < 0 || j < 0) return;
  const next = [...ws.panes];
  [next[i], next[j]] = [next[j], next[i]];
  ws.panes = next;
  persistWorkspace();
}

export function movePane(id: string, dir: -1 | 1) {
  const i = ws.panes.findIndex((p) => p.id === id);
  const j = i + dir;
  if (i < 0 || j < 0 || j >= ws.panes.length) return;
  swapPanes(ws.panes[i].id, ws.panes[j].id);
}

/** Quick layout presets: open/close panes so that `n` panes are visible. */
export function setLayout(n: 1 | 2 | 3 | 4, orientation: Orientation = ws.orientation) {
  ws.maximized = null;
  ws.orientation = orientation;
  const kinds: PaneKind[] = ['chat', 'code', 'image', 'video'];
  ws.minimized = [];
  while (ws.panes.length < n) {
    const used = new Set(ws.panes.map((p) => p.kind));
    const kind = kinds.find((k) => !used.has(k)) ?? 'chat';
    ws.panes.push({ id: newId(), kind });
  }
  // Extra panes beyond `n` are minimised rather than destroyed.
  ws.minimized = ws.panes.slice(n).map((p) => p.id);
  persistWorkspace();
}

export function resetRatios() {
  ws.colRatio = 0.5;
  ws.rowRatio = 0.5;
  persistWorkspace();
}

/** Per-pane persisted key helper. */
export const paneKey = (paneId: string, name: string) => `pane.${paneId}.${name}`;

function clearPaneStorage(id: string) {
  try {
    const prefix = `sarness.pane.${id}.`;
    for (let i = localStorage.length - 1; i >= 0; i--) {
      const k = localStorage.key(i);
      if (k?.startsWith(prefix)) localStorage.removeItem(k);
    }
  } catch {
    /* ignore */
  }
}

/** Panes that currently have outstanding work, for status chips. */
export function paneById(id: string) {
  return ws.panes.find((p) => p.id === id);
}

/** Bring a session of `kind` into view: focus an existing one or open a pane. */
export function openPane(kind: PaneKind): string {
  const existing = ws.panes.find((p) => p.kind === kind);
  if (existing) {
    ws.minimized = ws.minimized.filter((i) => i !== existing.id);
    if (ws.maximized && ws.maximized !== existing.id) ws.maximized = existing.id;
    ws.focus = existing.id;
    persistWorkspace();
    return existing.id;
  }
  const id = addPane(kind);
  if (id) return id;
  const target = ws.focus ?? ws.panes[0].id;
  setKind(target, kind);
  return target;
}

/** Request that a chat/code pane open a stored conversation. */
export const convRequest = $state({ paneId: null as string | null, convId: null as string | null, n: 0 });

export function openConversation(convId: string, preferred: PaneKind = 'chat') {
  let target = ws.panes.find((p) => p.id === ws.focus && (p.kind === 'chat' || p.kind === 'code'));
  target ??= ws.panes.find((p) => p.kind === preferred) ?? ws.panes.find((p) => p.kind === 'chat' || p.kind === 'code');
  const id = target?.id ?? openPane(preferred);
  if (ws.minimized.includes(id)) ws.minimized = ws.minimized.filter((i) => i !== id);
  ws.focus = id;
  persistWorkspace();
  convRequest.paneId = id;
  convRequest.convId = convId;
  convRequest.n++;
}
