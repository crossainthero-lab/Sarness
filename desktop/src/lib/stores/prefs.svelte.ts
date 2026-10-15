// Persisted UI preferences (per desktop). Engine-side data never lives here.

export type View = 'workspace' | 'system' | 'library' | 'models' | 'settings';

interface Prefs {
  view: View;
  sidebarCollapsed: boolean;
  panelSizes: Record<string, number>;
  imageMode: 'simple' | 'advanced';
  videoMode: 'simple' | 'advanced';
  libraryLayout: 'grid' | 'dense';
  libraryThumb: number;
  projectId: string | null;
  folderId: string | null;
  chatShowReasoning: boolean;
  reduceMotion: boolean;
  theme: 'light' | 'dark' | 'system';
  lastChatModel: string | null;
}

const KEY = 'sarness.prefs.v1';

const defaults: Prefs = {
  view: 'workspace',
  sidebarCollapsed: false,
  panelSizes: {},
  imageMode: 'simple',
  videoMode: 'simple',
  libraryLayout: 'grid',
  libraryThumb: 220,
  projectId: null,
  folderId: null,
  chatShowReasoning: false,
  reduceMotion: false,
  theme: 'light',
  lastChatModel: null,
};

function load(): Prefs {
  try {
    const raw = localStorage.getItem(KEY);
    if (raw) {
      const v = { ...defaults, ...JSON.parse(raw) } as Prefs;
      if (!['workspace', 'system', 'library', 'models', 'settings'].includes(v.view)) v.view = 'workspace';
      if (!['light', 'dark', 'system'].includes(v.theme)) v.theme = 'light';
      return v;
    }
  } catch {
    /* ignore */
  }
  return { ...defaults };
}

export const prefs = $state<Prefs>(load());

let timer: ReturnType<typeof setTimeout> | null = null;
export function persistPrefs() {
  if (timer) clearTimeout(timer);
  timer = setTimeout(() => {
    try {
      localStorage.setItem(KEY, JSON.stringify($state.snapshot(prefs)));
    } catch {
      /* storage full or unavailable */
    }
  }, 150);
}

/** Generic persisted state for feature-specific drafts (e.g. generation settings). */
export function persisted<T extends object>(key: string, initial: T): T {
  let value: T = initial;
  try {
    const raw = localStorage.getItem(`sarness.${key}`);
    if (raw) value = { ...initial, ...JSON.parse(raw) };
  } catch {
    /* ignore */
  }
  const s = $state<T>(value);
  return s;
}

export function savePersisted<T>(key: string, value: T) {
  try {
    localStorage.setItem(`sarness.${key}`, JSON.stringify(value));
  } catch {
    /* ignore */
  }
}
